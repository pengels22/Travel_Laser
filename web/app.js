async function fetchStatus() {
  const response = await fetch("/api/status");
  if (!response.ok) return;
  const state = await response.json();
  renderStatus(state);
}

function renderStatus(state) {
  setText("machine-state", state.machine.state);
  setText("homed", String(state.machine.homed));
  setText("k1", state.physical.k1 ? "on" : "off");
  setText("k2", state.physical.k2 ? "on" : "off");
  setText("lightburn", state.lightburn.connected ? "connected" : "disconnected");
  setText("mode", state.mode.laser_mode);

  const error = document.getElementById("error");
  if (state.machine.error) {
    error.textContent = state.machine.error;
    error.hidden = false;
  } else {
    error.hidden = true;
  }

  const frame = document.getElementById("camera-frame");
  if (state.camera.stream_url && !frame.querySelector("img")) {
    frame.innerHTML = "";
    const img = document.createElement("img");
    img.src = state.camera.stream_url;
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

