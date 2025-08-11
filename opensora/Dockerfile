FROM nvidia/cuda:12.1.0-devel-ubuntu20.04
# USER root
# Install necessary dependencies for micromamba
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget  \
    curl \
    # nvidia-cuda-toolkit \
    ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Download and install micromamba
RUN wget -qO- https://micro.mamba.pm/api/micromamba/linux-64/latest | tar xvj -C /usr/local bin/micromamba

# Add micromamba to PATH
ENV PATH="/usr/local/bin:$PATH"

RUN apt purge -y wget curl && apt -y autoremove




# install environment and difficult dependency tensornvme
COPY ./pyproject.toml /config/workspace/opensora/pyproject.toml
# Create SORA env
ENV CUDA_HOME=/usr/local/cuda
RUN  micromamba install -c conda-forge pyproject2conda && \
    micromamba run pyproject2conda yaml -f /config/workspace/opensora/pyproject.toml --python 3.10 -o environment.yaml -e dev --name opensora && \
    micromamba env create --file environment.yaml && \
    micromamba run -n opensora pip3 install --upgrade pip && \
    micromamba install -n opensora -y conda-forge::cmake conda-forge::make  conda-forge::git

RUN apt update && apt install -y libc6 libaio1 libaio-dev

# libering
RUN micromamba run -n opensora git clone https://github.com/axboe/liburing.git && \
  cd liburing && \
  ./configure && \
  micromamba run -n opensora make && \
  micromamba run -n opensora make install
RUN apt update && apt install -y curl

# RUN curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey |  gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
#   && curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
#     sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
#     tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
# ENV NVIDIA_CONTAINER_TOOLKIT_VERSION=1.17.8-1
# RUN apt-get install -y \
#       nvidia-container-toolkit=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
#       nvidia-container-toolkit-base=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
#       libnvidia-container-tools=${NVIDIA_CONTAINER_TOOLKIT_VERSION} \
#       libnvidia-container1=${NVIDIA_CONTAINER_TOOLKIT_VERSION}

# RUN micromamba run -n opensora pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
# ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:/root/.local/share/mamba/envs/opensora/lib/:${LD_LIBRARY_PATH}"
RUN micromamba run -n opensora git clone https://github.com/hpcaitech/TensorNVMe.git && \
    cd TensorNVMe && \
    micromamba run -n opensora pip install -r requirements.txt && \
    micromamba run -n opensora pip install -v --no-cache-dir .
# # Commands ran each merge
# # Copy local content and reinstall opensora package
COPY ./opensora /config/workspace/opensora/opensora
RUN cd /config/workspace/opensora && \
    micromamba run -n opensora pip3 install . 