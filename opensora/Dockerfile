FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04

# Install necessary dependencies for micromamba
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    curl \
    git \
    ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*


# Download and install micromamba
RUN wget -qO- https://micro.mamba.pm/api/micromamba/linux-64/latest | tar xvj -C /usr/local bin/micromamba

# Add micromamba to PATH
ENV PATH="/usr/local/bin:$PATH"



COPY ./opensora /config/workspace/opensora/opensora
COPY ./pyproject.toml /config/workspace/opensora/pyproject.toml

# install dependencies
RUN micromamba install -y conda-forge::git && \
    micromamba install -y conda-forge::conda-pypi && \
    micromamba install -c conda-forge pyproject2conda && \
    # Create SORA env
    micromamba run git clone -b master https://github.com/Pypaiper/Generative-Content-Pipeline.git && \
    cd Generative-Content-Pipeline && \
    micromamba run pyproject2conda yaml -f opensora/pyproject.toml --python 3.10 -o environment.yaml -e dev --name opensora && \
    micromamba env create --file environment.yaml && \
    ## activate env    micromamba run -n opensora pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 && \
    micromamba run -n opensora pip3 install xformers==0.0.27 --index-url https://download.pytorch.org/whl/cu121 triton diffusers && \
    micromamba run -n opensora pip3 install flash_attn==2.7.4.post1 && \
    # # Install tensornvme
    micromamba run -n base git clone https://github.com/hpcaitech/TensorNVMe.git && \
    micromamba install -n opensora -y conda-forge::cmake conda-forge::make  conda-forge::git && \
    cd TensorNVMe && \
    micromamba run -n opensora pip install . && \
    cd /config/workspace/opensora && \
    micromamba run -n opensora pip3 install --upgrade pip && \
    micromamba run -n opensora pip3 install . 
