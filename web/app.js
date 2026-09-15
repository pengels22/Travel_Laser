async function fetchStatus() {
  const response = await fetch("/api/status");
  if (!response.ok) return;
  const state = await response.json();
  renderStatus(state);
}

function renderStatus(state) {
  setText("machine-state", state.machine.state);
  setText("homed", String(state.machine.homed));
  setText("power-switch", state.physical.power_switch ? "on" : "off");
  setText("k1", state.physical.k1 ? "on" : "off");
  setText("lightburn", state.lightburn.connected ? "connected" : "disconnected");
  setText("mode", state.mode.laser_mode);

  const error = document.getElementById("error");
  if (state.machine.error) {
    error.textContent = state.machine.error;
    error.hidden = false;
  } else {
    error.hidden = true;
  }

  renderCamera(state.camera);
}

function renderCamera(camera) {
  const frame = document.getElementById("camera-frame");
  const streamUrl = camera.stream_url || `${window.location.protocol}//${window.location.hostname}:8889/cam`;

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

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

async function post(path) {
  await fetch(path, { method: "POST" });
  await fetchStatus();
}

document.getElementById("stop").addEventListener("click", () => post("/api/stop"));
document.getElementById("estop").addEventListener("click", () => post("/api/estop"));

fetchStatus();
setInterval(fetchStatus, 1000);
