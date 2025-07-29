FROM hpcaitech/pytorch-cuda:2.5.1-12.4.1

# install dependencies
RUN conda install -y cmake


#RUN ln -s  /usr/lib/x86_64-linux-gnu/libaio.so.1  /usr/lib/x86_64-linux-gnu/libaio.so.1t64
#ENV LD_LIBRARY_PATH $LD_LIBRARY_PATH:/usr/lib/x86_64-linux-gnu/


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

RUN git clone -b ml-utilities https://github.com/Pypaiper/Generative-Content-Pipeline.git && \
  cd Generative-Content-Pipeline && \
  pyproject2conda yaml -f opensora/pyproject.toml --python 3.10 -o environment.yaml --name opensora && \
  conda config --add channels pytorch && \
  conda config --add channels defaults && \
  conda config --add channels  conda-forge && \
  cat environment.yaml && sleep 7 && \
  conda env create --file environment.yaml


# install tensornvme
RUN git clone https://github.com/hpcaitech/TensorNVMe.git && \
    cd TensorNVMe && \
    . /opt/conda/etc/profile.d/conda.sh && conda activate opensora && \
    pip3 install -r requirements.txt && \
    pip3 install -v --no-cache-dir .


RUN git clone https://github.com/hpcaitech/Open-Sora.git && \
    cd Open-Sora && \
     . /opt/conda/etc/profile.d/conda.sh && conda activate opensora && \
    pip3 install -r requirements.txt && \
    pip3 install -v .
RUN . /opt/conda/etc/profile.d/conda.sh && conda activate opensora && \
  pip3 install xformers==0.0.27.post2 --index-url https://download.pytorch.org/whl/cu121 triton diffusers && \
  pip3 install flash_attn==2.7.4.post1 --no-build-isolation



# Set the working directory (optional)
WORKDIR /app
# Set the entrypoint to run code-server
ENTRYPOINT ["code-server", "--bind-addr", "0.0.0.0:28080"]

