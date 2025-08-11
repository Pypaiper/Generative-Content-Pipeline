FROM nvidia/cuda:12.1.0-devel-ubuntu20.04

# ARGS for sagemaker 
ARG NB_USER="sagemaker-user"
ARG NB_UID="1000"
ARG NB_GID="100"

# Add micromamba to PATH
ENV PATH="/usr/local/bin:$PATH"
# Specify Cuda
ENV CUDA_HOME=/usr/local/cuda
# Nice to have for easier command writing (less -y's)
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget  \
    curl \
    libc6 libaio1 libaio-dev \
    build-essential \
    git \
    vim \
    # python3-pip \
    # python3-dev \
    # nvidia-cuda-toolkit \
    ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Create SageMaker user
RUN useradd -m -s /bin/bash -N -u $NB_UID $NB_USER && \
    chmod g+w /etc/passwd && \
    echo "${NB_USER} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Download and install micromamba
RUN wget -qO- https://micro.mamba.pm/api/micromamba/linux-64/latest | tar xvj -C /usr/local bin/micromamba

# install environment and difficult dependency tensornvme
COPY ./pyproject.toml /config/workspace/opensora/pyproject.toml

# Create SORA env
RUN  micromamba install -c conda-forge pyproject2conda && \
    micromamba run pyproject2conda yaml -f /config/workspace/opensora/pyproject.toml --python 3.10 -o environment.yaml -e dev --name opensora && \
    micromamba env create --file environment.yaml && \
    micromamba run -n opensora pip3 install --upgrade pip && \
    micromamba install -n opensora -y conda-forge::cmake conda-forge::make  conda-forge::git

# liburing
RUN micromamba run -n opensora git clone https://github.com/axboe/liburing.git && \
  cd liburing && \
  ./configure && \
  micromamba run -n opensora make && \
  micromamba run -n opensora make install

# Tensornvme, used for more efficient computation
RUN micromamba run -n opensora git clone https://github.com/hpcaitech/TensorNVMe.git && \
    cd TensorNVMe && \
    micromamba run -n opensora pip install -r requirements.txt && \
    micromamba run -n opensora pip install -v --no-cache-dir .


RUN micromamba run -n opensora pip install --upgrade pip && \
    micromamba run -n opensora pip3 install --no-cache-dir \
    torch \
    torchvision \
    torchaudio \
    --index-url https://download.pytorch.org/whl/cu121 # Ensure CUDA-enabled PyTorch
RUN micromamba run -n opensora pip3 install --no-cache-dir \
    jupyterlab \
    notebook \
    sagemaker \
    boto3 \
    pandas \
    numpy \
    matplotlib \
    scikit-learn 

# # Commands ran each merge
# # Copy local content and reinstall opensora package
COPY ./opensora /config/workspace/opensora/opensora
RUN cd /config/workspace/opensora && \
    micromamba run -n opensora pip3 install . 

# Set default command for JupyterLab
CMD ["micromamba", "run", "-n", "opensora", "jupyter-lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]