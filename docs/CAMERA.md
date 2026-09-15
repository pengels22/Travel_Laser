# Camera

Camera streaming is WebRTC for deployment.

- The web portal embeds the configured WebRTC stream URL in a simple viewer.
- If no `camera.stream_url` is configured, the web portal defaults to `http://<current-host>:8889/cam`.
- MediaMTX serves WebRTC on port `8889`.
- FFmpeg publishes the selected V4L2 camera mode to MediaMTX over RTSP on `127.0.0.1:8554/cam`.
- The backend does not transcode camera video.
- `scripts/select-camera-mode.sh` selects the largest advertised V4L2 resolution.
- The camera service starts at 30 FPS by default; confirm the highest stable resolution/FPS after the physical camera is present.
- Camera failure never stops the laser and must not affect K1/K2.

The exact camera USB identity remains hardware-dependent.
