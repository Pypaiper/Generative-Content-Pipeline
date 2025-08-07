FROM mambaorg/micromamba:latest

COPY ./opensora /config/workspace/opensora/opensora
COPY ./pyproject.toml /config/workspace/opensora/pyproject.toml


# install dependencies
RUN micromamba install -y conda-forge::git && \
    micromamba install -y conda-forge::cmake && \
    micromamba install -y conda-forge::conda-pypi && \
    micromamba install -c conda-forge pyproject2conda && \
    # Create SORA env
    micromamba run git clone -b master https://github.com/Pypaiper/Generative-Content-Pipeline.git && \
    cd Generative-Content-Pipeline && \
    micromamba run pyproject2conda yaml -f opensora/pyproject.toml --python 3.10 -o environment.yaml -e dev --name opensora && \
    micromamba env create --file environment.yaml && \
    ## activate env
    eval "$(micromamba shell hook --shell bash)" && \
    micromamba activate opensora  && \
    micromamba install -c "nvidia/label/cuda-12.1.0" cuda-nvcc&& \
    pip3 install xformers==0.0.27.post2 --index-url https://download.pytorch.org/whl/cu121 triton diffusers && \
    pip3 install flash_attn==2.7.4.post1 --no-build-isolation 
    # cd .. && \
    # # install tensornvme
    # micromamba run git clone https://github.com/hpcaitech/TensorNVMe.git && \
    # cd TensorNVMe && \
    # pip install -r requirements.txt && \
    # pip install -v --no-cache-dir . && \
    # cd /config/workspace/opensora && \
    # pip3 install -e . --no-deps
