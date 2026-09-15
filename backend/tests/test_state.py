from backend.state import ControllerState, LaserMode


async def test_state_updates_are_snapshot_based():
    state = ControllerState()

    def mutate(snapshot):
        snapshot.physical.k1 = True
        snapshot.mode.laser_mode = LaserMode.VIRTUALHERE

    await state.update(mutate)
    data = await state.to_dict()
    assert data["physical"]["k1"] is True
    assert data["mode"]["laser_mode"] == "virtualhere"
