FROM hpcaitech/pytorch-cuda:2.5.1-12.4.1

# install dependencies
RUN conda install -y cmake

# Install code-server using their install script
RUN apt update && apt install -y curl && sleep 2
RUN curl -fsSL https://code-server.dev/install.sh | sh

# Copy project files and customizations (optional)
RUN ["code-server", "--install-extension", "ms-python.python"]
RUN ["code-server", "--install-extension", "ms-toolsai.jupyter"]
RUN ["code-server", "--install-extension", "njpwerner.autodocstring"]

RUN  pip3 install ipykernel
RUN apt update && apt install -y libc6

RUN conda install -n base conda-forge::conda-pypi
RUN conda install -c conda-forge pyproject2conda
RUN conda update conda && conda update --all

# OPEN SORA env
RUN git clone -b ml-utilities https://github.com/Pypaiper/Generative-Content-Pipeline.git && \
  cd Generative-Content-Pipeline && \
  pyproject2conda yaml -f opensora/pyproject.toml --python 3.10 -o environment.yaml -e dev --name opensora && \
  conda config --add channels pytorch && \
  conda config --add channels defaults && \
  conda config --add channels  conda-forge && \
  conda env create --file environment.yaml

# scraping env
RUN cd Generative-Content-Pipeline && \
  pyproject2conda yaml -f scraping/pyproject.toml --python 3.10 -o environment.yaml -e dev --name scraping && \
  conda config --add channels defaults && \
  conda config --add channels  conda-forge && \
  conda env create --file environment.yaml

# install tensornvme
RUN git clone https://github.com/hpcaitech/TensorNVMe.git && \
    cd TensorNVMe && \
    . /opt/conda/etc/profile.d/conda.sh && conda activate opensora && \
    pip3 install -r requirements.txt && \
    pip3 install -v --no-cache-dir .

# Install opensora dependencies
RUN git clone https://github.com/hpcaitech/Open-Sora.git && \
    cd Open-Sora && \
     . /opt/conda/etc/profile.d/conda.sh && conda activate opensora && \
    pip3 install -r requirements.txt && \
    # Extra dependencies per opensora's readme
    pip3 install xformers==0.0.27.post2 --index-url https://download.pytorch.org/whl/cu121 triton diffusers && \
    pip3 install flash_attn==2.7.4.post1 --no-build-isolation


# Install projects editable into environments
COPY ./opensora/opensora /config/workspace/opensora/opensora
COPY ./opensora/pyproject.toml /config/workspace/opensora/pyproject.toml
COPY ./scraping/scraping /config/workspace/scraping/scraping
COPY ./scraping/pyproject.toml /config/workspace/scraping/pyproject.toml
## opensora requires scraping, install itself and dependencies
RUN . /opt/conda/etc/profile.d/conda.sh && conda activate opensora && \
   cd /config/workspace/opensora && \
   pip3 install -e . --no-deps && \
    cd ../scraping && \
   pip3 install -e . --no-deps

## install scraping and dependencies
RUN . /opt/conda/etc/profile.d/conda.sh && conda activate scraping && \
   cd /config/workspace/scraping && \
   pip3 install -e . && \
   sed -i -e 's/for idx, dir in enumerate(dirs):/for idx, dir in enumerate(dirs):\n            print(idx);\n            if idx in [9159,14419]: continue/g' /opt/conda/envs/scraping/lib/python3.10/site-packages/gutenbergpy/parse/rdfparser.py

# Set the working directory (optional)
WORKDIR /app

# Set the entrypoint to run code-server
ENTRYPOINT ["code-server", "--bind-addr", "0.0.0.0:8080"]

