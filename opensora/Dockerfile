FROM nvidia/cuda:12.1.1-devel-ubuntu20.04
USER root
# Install necessary dependencies for micromamba
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget  \
    curl \
    # nvidia-cuda-toolkit \
    ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install nvcc
# ENV NVIDIA_CONTAINER_TOOLKIT_VERSION=1.17.8-1
# RUN curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
#   && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
#     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
#     tee /etc/apt/sources.list.d/nvidia-container-toolkit.list && \
#     apt-get update && \
#     apt-get install -y \
#       nvidia-container-toolkit=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
#       nvidia-container-toolkit-base=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
#       libnvidia-container-tools=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
#       libnvidia-container1=${NVIDIA_CONTAINER_TOOLKIT_VERSION}

# Download and install micromamba
RUN wget -qO- https://micro.mamba.pm/api/micromamba/linux-64/latest | tar xvj -C /usr/local bin/micromamba

# Add micromamba to PATH
ENV PATH="/usr/local/bin:$PATH"

RUN apt purge -y wget curl && apt -y autoremove



# USER mambauser
# install environment and difficult dependency tensornvme
COPY ./pyproject.toml /config/workspace/opensora/pyproject.toml
RUN micromamba install -y conda-forge::git && \
    micromamba run -n base git clone https://github.com/hpcaitech/TensorNVMe.git && \
    micromamba install -y conda-forge::conda-pypi && \
    micromamba install -c conda-forge pyproject2conda && \
    # Create SORA env
    cd Generative-Content-Pipeline && \
    micromamba run pyproject2conda yaml -f /config/workspace/opensora/pyproject.toml --python 3.10 -o environment.yaml -e dev --name opensora && \
    micromamba env create --file environment.yaml && \
    micromamba run -n opensora pip3 cache purge && \
    micromamba run -n opensora pip3 install xformers --index-url https://download.pytorch.org/whl/cu121 triton diffusers && \
    cd .. && \
    rm -rf Generative-Content-Pipeline && \
    micromamba install -n opensora -y conda-forge::cmake conda-forge::make  conda-forge::git && \
    micromamba run -n opensora pip3 install flash_attn==2.7.4.post1 && \
    cd TensorNVMe && \
    micromamba run -n opensora pip install .
# Commands ran each merge
# Copy local content and reinstall opensora package
COPY ./opensora /config/workspace/opensora/opensora
RUN cd /config/workspace/opensora && \
    micromamba run -n opensora pip3 install --upgrade pip && \
    micromamba run -n opensora pip3 install . 