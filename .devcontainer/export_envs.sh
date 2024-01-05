# !/bin/zsh

echo "UID=$(id -u)" > .devcontainer/devcontainer.env
echo "GID=$(id -g)" >> .devcontainer/devcontainer.env
echo "ARCH=$(uname -m)" >> .devcontainer/devcontainer.env
