docker build -t camera-recorder:latest .

docker run \
  -v /tmp/.X11-unix/:/tmp/.X11-unix/ \
  -v $(pwd)/..:/home/recorder/webcam-recorder \
  -v ~/.zsh_history:/home/recorder/.zsh_history \
  -p 5000:5000 \
  -p 8800:8800 \
  -e DISPLAY=:0 \
  --device /dev/video0:/dev/video0 \
  --device /dev/snd:/dev/snd \
  --workdir /home/recorder/webcam-recorder \
  -it \
  camera-recorder
