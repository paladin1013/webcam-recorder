#!/bin/zsh
SCRIPT_DIR=$(realpath $(dirname $0))
WORKSPACE_DIR=$(realpath $SCRIPT_DIR/..)
DOCKER_DIR=$(realpath $SCRIPT_DIR/../docker)
REMOTE_USER=recorder

docker build \
  --build-arg USER_UID=$(id -u) \
  --build-arg USER_GID=$(id -g) \
  -t camera-recorder:latest $DOCKER_DIR

docker run \
  -v /tmp/.X11-unix/:/tmp/.X11-unix/ \
  -v $WORKSPACE_DIR:/home/$REMOTE_USER/webcam-recorder \
  -v ~/.zsh_history:/home/$REMOTE_USER/.zsh_history \
  -p 5000:5000 \
  -p 8800:8800 \
  -e DISPLAY=:0 \
  --device /dev/video0:/dev/video0 \
  --device /dev/snd:/dev/snd \
  --workdir /home/$REMOTE_USER/webcam-recorder \
  -it \
  camera-recorder
