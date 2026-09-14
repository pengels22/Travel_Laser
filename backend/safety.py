from __future__ import annotations

from enum import Enum

from .events import ControllerEvent, EventCode, Severity
from .gpio import GPIOBackend
from .state import ControllerState, MachineState


class EstopSource(str, Enum):
    PHYSICAL = "physical"
    TS1 = "ts1"
    WEB = "web"
    SOFTWARE = "software"
    FIRE = "fire"
    LIGHTBURN = "lightburn"
    USB = "usb"


class SafetyController:
    def __init__(self, state: ControllerState, gpio: GPIOBackend, event_sink: object | None = None) -> None:
        self.state = state
        self.gpio = gpio
        self.event_sink = event_sink
        self.events: list[ControllerEvent] = []

    async def initialize_safe(self) -> None:
        await self.gpio.initialize_safe()

        def mutate(snapshot):
            snapshot.physical.k1 = False
            snapshot.physical.k2 = False

        await self.state.update(mutate)

    async def refresh_physical_inputs(self) -> None:
        power = await self.gpio.read_power_switch()
        estop = await self.gpio.read_estop_switch()

        def mutate(snapshot):
            snapshot.physical.power_switch = power
            snapshot.physical.estop_switch = estop

        await self.state.update(mutate)
        await self.evaluate_outputs()

    async def evaluate_outputs(self) -> None:
        snapshot = await self.state.snapshot()
        k1_should_on = snapshot.physical.power_switch
        k2_should_on = not self._any_estop(snapshot)
        await self.set_k1(k1_should_on)
        await self.set_k2(k2_should_on)

    async def request_estop(self, source: EstopSource, reason: str | None = None) -> None:
        event_code = {
            EstopSource.PHYSICAL: EventCode.PHYSICAL_ESTOP_ON,
            EstopSource.TS1: EventCode.TS1_ESTOP,
            EstopSource.WEB: EventCode.WEB_ESTOP,
            EstopSource.SOFTWARE: EventCode.SOFTWARE_ESTOP,
            EstopSource.LIGHTBURN: EventCode.LIGHTBURN_STREAM_LOST,
            EstopSource.USB: EventCode.LASER_USB_DISCONNECTED,
            EstopSource.FIRE: EventCode.SOFTWARE_ESTOP,
        }[source]

        def mutate(snapshot):
            if source == EstopSource.PHYSICAL:
                snapshot.physical.estop_switch = True
            elif source == EstopSource.TS1:
                snapshot.safety.remote_estop = True
            elif source in {EstopSource.WEB, EstopSource.SOFTWARE, EstopSource.LIGHTBURN, EstopSource.USB}:
                snapshot.safety.software_estop = True
            elif source == EstopSource.FIRE:
                snapshot.safety.fire_active = True
            snapshot.machine.homed = False
            snapshot.machine.state = MachineState.FAULT

        await self.state.update(mutate)
        await self.set_k2(False)
        self.record(event_code, Severity.CRITICAL, source.value, {"reason": reason})

    async def clear_software_estop(self) -> None:
        def mutate(snapshot):
            snapshot.safety.remote_estop = False
            snapshot.safety.software_estop = False
            snapshot.safety.fire_active = False
            if not snapshot.physical.estop_switch:
                snapshot.machine.state = MachineState.RECOVERING

        await self.state.update(mutate)
        await self.evaluate_outputs()

    async def set_k1(self, energized: bool) -> None:
        snapshot = await self.state.snapshot()
        if snapshot.physical.k1 == energized:
            return
        await self.gpio.set_k1(energized)

        def mutate(state):
            state.physical.k1 = energized

        await self.state.update(mutate)
        self.record(EventCode.K1_ON if energized else EventCode.K1_OFF)

    async def set_k2(self, energized: bool) -> None:
        snapshot = await self.state.snapshot()
        if snapshot.physical.k2 == energized:
            return
        await self.gpio.set_k2(energized)

        def mutate(state):
            state.physical.k2 = energized
            if not energized:
                state.machine.homed = False

        await self.state.update(mutate)
        self.record(EventCode.K2_ON if energized else EventCode.K2_OFF)

    async def handle_lightburn_disconnect(self) -> None:
        snapshot = await self.state.snapshot()

        def mutate(state):
            state.lightburn.connected = False

        await self.state.update(mutate)
        if snapshot.lightburn.stream_active:
            await self.request_estop(EstopSource.LIGHTBURN, "active LightBurn TCP stream lost")
        else:
            self.record(EventCode.LIGHTBURN_DISCONNECTED, Severity.INFO, "grbl_proxy")

    async def handle_laser_usb_disconnected(self) -> None:
        snapshot = await self.state.snapshot()

        def mutate(state):
            state.machine.laser_usb_connected = False
            state.machine.connected_to_grbl = False

        await self.state.update(mutate)
        if snapshot.physical.k2:
            await self.request_estop(EstopSource.USB, "laser USB lost while K2 expected on")
        else:
            self.record(EventCode.LASER_USB_DISCONNECTED, Severity.INFO, "usb", {"expected": True})

    async def handle_camera_disconnected(self) -> None:
        def mutate(state):
            state.camera.connected = False

        await self.state.update(mutate)
        self.record(EventCode.CAMERA_USB_DISCONNECTED, Severity.WARNING, "camera")

    async def handle_ts1_disconnected(self) -> None:
        def mutate(state):
            state.ts1.connected = False

        await self.state.update(mutate)
        self.record(EventCode.TS1_DISCONNECTED, Severity.WARNING, "websocket")

    def record(
        self,
        code: EventCode,
        severity: Severity = Severity.INFO,
        source: str = "safety",
        details: dict | None = None,
    ) -> None:
        self.events.append(ControllerEvent(code=code, severity=severity, source=source, details=details or {}))

    def _any_estop(self, snapshot) -> bool:
        fire_estop = snapshot.safety.fire_enabled and snapshot.safety.fire_active
        return (
            snapshot.physical.estop_switch
            or snapshot.safety.remote_estop
            or snapshot.safety.software_estop
            or fire_estop
        )

