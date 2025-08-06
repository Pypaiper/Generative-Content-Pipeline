FROM hpcaitech/pytorch-cuda:1.11.0-11.3.0

COPY ./opensora /config/workspace/opensora/opensora
COPY ./pyproject.toml /config/workspace/opensora/pyproject.toml

# install dependencies
RUN conda install mamba -n base -c conda-forge && \

    mamba install -y conda-forge::cmake && \
    mamba install -n base conda-forge::conda-pypi && \
    mamba install -c conda-forge pyproject2conda && \
    
    # Create SORA env
    git clone -b master https://github.com/Pypaiper/Generative-Content-Pipeline.git && \
    cd Generative-Content-Pipeline && \
    pyproject2conda yaml -f opensora/pyproject.toml --python 3.10 -o environment.yaml -e dev --name opensora && \
    mamba env create --file environment.yaml && \
    cd .. && \
    # install tensornvme
    git clone https://github.com/hpcaitech/TensorNVMe.git && \
    cd TensorNVMe && \
    pip install -r requirements.txt && \
    pip install -v --no-cache-dir . && \
    cd /config/workspace/opensora && \
    pip3 install -e . --no-deps
