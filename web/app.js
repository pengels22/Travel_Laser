async function fetchCameraStatus() {
  const response = await fetch("/api/status");
  if (!response.ok) return;
  const state = await response.json();
  const laserOk = state.ready &&
    state.physical.power_sense &&
    !state.physical.estop_sense &&
    state.physical.k1 &&
    state.machine.laser_usb_connected &&
    state.machine.connected_to_grbl &&
    !state.safety.software_estop;
  const status = document.getElementById("laser-status");
  status.textContent = laserOk ? "LASER OK" : "LASER FAULT";
  status.className = laserOk ? "ok" : "fault";
  document.getElementById("mode-status").textContent = `Mode: ${state.mode.laser_mode}`;
  document.getElementById("camera-status").textContent = cameraText(state.camera);
  document.getElementById("network-status").textContent =
    `Tailscale: ${state.network.tailscale_status || "unknown"} ${state.network.tailscale_ip || ""}`.trim();
  renderCamera(state.camera);
}

function cameraText(camera) {
  const state = camera.connected ? "connected" : "not connected";
  return `Camera: ${state} (${camera.stream_type || "stream"})`;
}

function renderCamera(camera) {
  const frame = document.getElementById("camera-frame");
  const streamUrl = camera.stream_url || `${window.location.protocol}//${window.location.hostname}:8889/cam/`;
  if (camera.stream_type === "webrtc") {
    const existing = frame.querySelector("iframe");
    if (existing && existing.src === streamUrl) return;
    frame.innerHTML = "";
    const iframe = document.createElement("iframe");
    iframe.src = streamUrl;
    iframe.title = "WebRTC camera stream";
    iframe.allow = "autoplay; fullscreen; camera";
    iframe.referrerPolicy = "no-referrer";
    frame.appendChild(iframe);
  } else {
    const existing = frame.querySelector("img");
    if (existing && existing.src === streamUrl) return;
    frame.innerHTML = "";
    const img = document.createElement("img");
    img.src = streamUrl;
    img.alt = "Camera stream";
    frame.appendChild(img);
  }
}

async function post(path) {
  const response = await fetch(path, { method: "POST" });
  if (!response.ok) {
    let message = "Command unavailable.";
    try {
      const result = await response.json();
      message = result.message || message;
    } catch (_) {
      // Keep the generic message.
    }
    window.alert(message);
  }
}

document.getElementById("home").addEventListener("click", () => post("/api/home"));
document.getElementById("stop").addEventListener("click", () => post("/api/stop"));
document.getElementById("estop").addEventListener("click", () => post("/api/estop"));
document.getElementById("reset-fault").addEventListener("click", () => {
  if (window.confirm("Reset fault latch? Home before running.")) {
    post("/api/reset-fault");
  }
});

fetchCameraStatus();
setInterval(fetchCameraStatus, 1000);
