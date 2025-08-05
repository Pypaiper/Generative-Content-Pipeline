FROM hpcaitech/pytorch-cuda:1.11.0-11.3.0

# install dependencies
RUN conda install -y cmake
RUN conda install -n base conda-forge::conda-pypi
RUN conda install -c conda-forge pyproject2conda
RUN conda update conda && conda update --all

# Create SORA env
RUN git clone -b master https://github.com/Pypaiper/Generative-Content-Pipeline.git && \
  cd Generative-Content-Pipeline && \
  pyproject2conda yaml -f opensora/pyproject.toml --python 3.10 -o environment.yaml -e dev --name opensora && \
  conda config --add channels pytorch && \
  conda config --add channels defaults && \
  conda config --add channels  conda-forge && \
  conda env create --file environment.yaml

# install tensornvme
RUN git clone https://github.com/hpcaitech/TensorNVMe.git && \
    cd TensorNVMe && \
    . /opt/conda/etc/profile.d/conda.sh && conda activate opensora && \
    pip install -r requirements.txt && \
    pip install -v --no-cache-dir .


COPY ./opensora /config/workspace/opensora/opensora
COPY ./pyproject.toml /config/workspace/opensora/pyproject.toml

## opensora requires scraping, install itself and dependencies
RUN . /opt/conda/etc/profile.d/conda.sh && conda activate opensora && \
   cd /config/workspace/opensora && \
   pip3 install -e . --no-deps
