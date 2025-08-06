FROM hpcaitech/pytorch-cuda:1.11.0-11.3.0

COPY ./opensora /config/workspace/opensora/opensora
COPY ./pyproject.toml /config/workspace/opensora/pyproject.toml

# install dependencies
RUN conda install -y cmake && \
    conda install -n base conda-forge::conda-pypi && \
    conda install -c conda-forge pyproject2conda && \
    conda update conda && conda update --all && \
    # Create SORA env
    git clone -b master https://github.com/Pypaiper/Generative-Content-Pipeline.git && \
    cd Generative-Content-Pipeline && \
    pyproject2conda yaml -f opensora/pyproject.toml --python 3.10 -o environment.yaml -e dev --name opensora && \
    conda config --add channels pytorch && \
    conda config --add channels defaults && \
    conda config --add channels  conda-forge && \
    conda env create --file environment.yaml && \
    # install tensornvme
    cd .. && \
    git clone https://github.com/hpcaitech/TensorNVMe.git && \
    cd TensorNVMe && \
    pip install -r requirements.txt && \
    pip install -v --no-cache-dir . && \
    cd /config/workspace/opensora && \
    pip3 install -e . --no-deps
