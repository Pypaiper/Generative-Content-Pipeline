FROM hpcaitech/pytorch-cuda:2.5.1-12.4.1

# install dependencies
RUN conda install -y cmake

# install tensornvme
RUN git clone https://github.com/hpcaitech/TensorNVMe.git && \
    cd TensorNVMe && \
    pip3 install -r requirements.txt && \
    pip3 install -v --no-cache-dir .

RUN git clone https://github.com/hpcaitech/Open-Sora.git && \
    cd Open-Sora && \
    pip3 install -r requirements.txt && \
    pip3 install -v .

#RUN ln -s  /usr/lib/x86_64-linux-gnu/libaio.so.1  /usr/lib/x86_64-linux-gnu/libaio.so.1t64
#ENV LD_LIBRARY_PATH $LD_LIBRARY_PATH:/usr/lib/x86_64-linux-gnu/

RUN pip3 install xformers triton diffusers
#RUN pip3 install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu126 
#RUN pip3 install flash-attn==2.7.4.post1 --no-build-isolation

RUN pip3 install flash_attn==2.7.4.post1 --no-build-isolation


# Install code-server using their install script
RUN apt update && apt install -y curl && sleep 2
RUN curl -fsSL https://code-server.dev/install.sh | sh

# Copy project files and customizations (optional)
RUN ["code-server", "--install-extension", "ms-python.python"]
RUN ["code-server", "--install-extension", "ms-toolsai.jupyter"]
RUN ["code-server", "--install-extension", "njpwerner.autodocstring"]

RUN  pip3 install opencv-python-headless ipykernel
RUN apt update && apt install -y libc6

RUN conda install -n base conda-forge::conda-pypi
RUN conda install -c conda-forge pyproject2conda

RUN git clone https://github.com/Pypaiper/Generative-Content-Pipeline.git && \
  cd Generative-Content-Pipeline && \
  pyproject2conda yaml -f training/pyproject.toml --python 3.12 -o environment.yaml --name training && \
  conda config --add channels defaults && \
  cat environment.yaml && sleep 7 && \
  conda env create --file environment.yaml

# Set the working directory (optional)
WORKDIR /app
# Set the entrypoint to run code-server
ENTRYPOINT ["code-server"]

