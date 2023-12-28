FROM ubuntu:22.04

RUN apt-get update &&\
    apt-get install git -y



ARG USERNAME=recorder
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Add the new user with sudo access
# TODO: this should be removed when published
RUN useradd -m ${USERNAME} -p "$(openssl passwd -1 123)"
RUN usermod -aG sudo ${USERNAME}
# Give ownership of the user's home directory to the new user


# Personal ubuntu configurations
RUN apt-get install -y x11-apps
RUN git clone https://github.com/paladin1013/ubuntu-config.git /home/${USERNAME}/ubuntu-config && \
    cd /home/${USERNAME}/ubuntu-config && \
    git checkout d6270f472f4b788a46d6d6c123fbdff80dfb1599 && \
    ./setup_ubuntu.sh

RUN chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}


USER ${USERNAME}
# Set the user's home directory as the working directory
WORKDIR /home/${USERNAME}
# Continue setting up the user's environment
RUN cd ubuntu-config && \
    ./install_oh_my_zsh.sh && \
    ./config_oh_my_zsh.sh && \
    ./install_conda.sh

# pre-install vscode server and helpful plugins
RUN git clone https://gist.github.com/0a16b6645ab7921b0910603dfb85e4fb.git /home/${USERNAME}/vscode-install && \
    chmod +x /home/${USERNAME}/vscode-install/download-vs-code-server.sh && \
    /home/${USERNAME}/vscode-install/download-vs-code-server.sh
ENV PATH=/home/${USERNAME}/.vscode-server/bin/default_version/bin:$PATH
RUN code-server --install-extension ms-python.python && \
    code-server --install-extension mhutchie.git-graph && \
    code-server --install-extension eamodio.gitlens && \
    code-server --install-extension github.copilot && \
    code-server --install-extension kevinrose.vsc-python-indent && \
    code-server --install-extension streetsidesoftware.code-spell-checker
# Enable using `code` command in terminal to open file or attach new window to a folder
RUN echo "export PATH=/home/${USERNAME}/.vscode-server/bin/default_version/bin/remote-cli:\$PATH" >> /home/${USERNAME}/.zshrc

RUN /home/${USERNAME}/miniforge3/bin/mamba install -y opencv

USER root

# For opencv
RUN apt-get install -y sudo ffmpeg libsm6 libxext6
RUN usermod -aG video ${USERNAME}

USER ${USERNAME}

RUN code-server --install-extension ms-python.black-formatter
RUN /home/${USERNAME}/miniforge3/bin/pip install opencv-stubs
RUN /home/${USERNAME}/miniforge3/bin/mamba install -y av
RUN /home/${USERNAME}/miniforge3/bin/pip install quart zmq

SHELL ["/bin/zsh", "-ec"]
CMD ["zsh"]