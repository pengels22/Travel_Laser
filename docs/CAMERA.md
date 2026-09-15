# Camera

Camera streaming is WebRTC for deployment.

- The web portal embeds the configured WebRTC stream URL in a simple viewer.
- The backend does not transcode camera video.
- The camera service should request the highest stable resolution/FPS the camera and Orange Pi can support.
- Camera failure never stops the laser and must not affect K1/K2.

The exact WebRTC streamer command and camera USB identity remain hardware-dependent.
