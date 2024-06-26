# FROM dustynv/l4t-pytorch:r36.2.0
FROM dustynv/opencv:4.8.1-r36.2.0

RUN apt-get update &&\
    apt-get install -y \
    git zsh curl git vim net-tools wget htop x11-apps neofetch sudo \
    # For pytorch
    libopenblas-dev

RUN apt-get install ca-certificates --reinstall -y

ARG USERNAME=recorder
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd -g ${USER_GID} ${USERNAME} && \
    useradd ${USERNAME}  -u ${USER_UID} -g ${USER_GID} -m -p "$(openssl passwd -1 ${USERNAME})"
RUN usermod -aG sudo ${USERNAME}
# Give ownership of the user's home directory to the new user
RUN chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}

USER ${USERNAME}
ARG HOME=/home/${USERNAME}
WORKDIR ${HOME}

RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"

RUN git clone https://github.com/marlonrichert/zsh-autocomplete.git \
    ${ZSH_CUSTOM:-/home/${USERNAME}/.oh-my-zsh/custom}/plugins/zsh-autocomplete && \
    git clone https://github.com/zsh-users/zsh-autosuggestions \
    ${ZSH_CUSTOM:-/home/${USERNAME}/.oh-my-zsh/custom}/plugins/zsh-autosuggestions && \
    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git \
    ${ZSH_CUSTOM:-/home/${USERNAME}/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting && \
    git clone --depth=1 https://github.com/romkatv/powerlevel10k.git \
    ${ZSH_CUSTOM:-/home/${USERNAME}/.oh-my-zsh/custom}/themes/powerlevel10k

RUN mv ${HOME}/.zshrc ${HOME}/.zshrc.bak && \
    echo 'export ZSH="$HOME/.oh-my-zsh"\nplugins=(\n  git\n  zsh-autosuggestions\n  zsh-autocomplete\n  zsh-syntax-highlighting\n  themes\n)\n' >> ${HOME}/.zshrc && \
    echo 'ZSH_THEME="eastwood"\nsource $ZSH/oh-my-zsh.sh' >> ${HOME}/.zshrc && \
    echo 'bindkey -M menuselect "\\r" .accept-line' >> ${HOME}/.zshrc && \
    echo 'bindkey -M menuselect -s "^R" "^_^_^R" "^S" "^_^_^S"' >> ${HOME}/.zshrc && \
    echo 'bindkey -M menuselect "\\e[D" .backward-char "\\eOD" .backward-char "\\e[C" .forward-char "\\eOC" .forward-char' >> ${HOME}/.zshrc && \
    echo 'bindkey '^H' backward-kill-word' >> ${HOME}/.zshrc


RUN ARCH=$(uname -m) && SYS=$(uname -s) && \
    wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-${SYS}-${ARCH}.sh && \
    bash Miniforge3-${SYS}-${ARCH}.sh -b -p ${HOME}/miniforge3 && \
    rm Miniforge3-${SYS}-${ARCH}.sh && \
    ${HOME}/miniforge3/bin/conda init zsh && \
    ${HOME}/miniforge3/bin/conda init bash && \
    ${HOME}/miniforge3/bin/mamba init zsh && \
    ${HOME}/miniforge3/bin/mamba init bash


# pre-install vscode server and helpful plugins
RUN git clone https://gist.github.com/0a16b6645ab7921b0910603dfb85e4fb.git /home/${USERNAME}/vscode-install && \
    chmod +x /home/${USERNAME}/vscode-install/download-vs-code-server.sh && \
    /home/${USERNAME}/vscode-install/download-vs-code-server.sh linux
ENV PATH=/home/${USERNAME}/.vscode-server/bin/default_version/bin:$PATH
RUN code-server --install-extension ms-python.python && \
    code-server --install-extension mhutchie.git-graph && \
    code-server --install-extension eamodio.gitlens && \
    code-server --install-extension github.copilot && \
    code-server --install-extension kevinrose.vsc-python-indent && \
    code-server --install-extension streetsidesoftware.code-spell-checker && \
    code-server --install-extension ms-python.black-formatter

# Enable using `code` command in terminal to open file or attach new window to a folder
RUN echo "export PATH=/home/${USERNAME}/.vscode-server/bin/default_version/bin/remote-cli:\$PATH" >> /home/${USERNAME}/.zshrc


# Install pytorch
RUN wget https://nvidia.box.com/shared/static/0h6tk4msrl9xz3evft9t0mpwwwkw7a32.whl -O torch-2.1.0-cp310-cp310-linux_aarch64.whl && \
    /home/${USERNAME}/miniforge3/bin/pip install torch-2.1.0-cp310-cp310-linux_aarch64.whl && \
    rm torch-2.1.0-cp310-cp310-linux_aarch64.whl && \
    /home/${USERNAME}/miniforge3/bin/pip install numpy

# RUN /home/${USERNAME}/miniforge3/bin/mamba install -y opencv

USER root

# For opencv
RUN apt-get update && apt-get install -y \
    sudo ffmpeg libsm6 libxext6 libcairo2-dev \
    libgirepository1.0-dev 
# RUN apt-get update && apt-get install -y \
#     libgstreamer1.0-dev \
#     libgstreamer-plugins-base1.0-dev \
#     libgstreamer-plugins-good1.0-dev \
#     libgstreamer-plugins-bad1.0-dev
# RUN cp /usr/lib/aarch64-linux-gnu/gstreamer-1.0/* /home/${USERNAME}/miniforge3/lib/gstreamer-1.0

RUN usermod -aG video ${USERNAME}
RUN usermod -aG audio ${USERNAME}

USER ${USERNAME}

RUN /home/${USERNAME}/miniforge3/bin/pip install \
    opencv-python opencv-stubs quart zmq pytz \
    PyGObject
RUN /home/${USERNAME}/miniforge3/bin/mamba install -y \
    av python-sounddevice gst-plugins-base
# For audio recording
RUN /home/${USERNAME}/miniforge3/bin/pip install scipy moviepy \
    # For code formatting
    isort black


SHELL ["/bin/zsh", "-ec"]
CMD ["zsh"]