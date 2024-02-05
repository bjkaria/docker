FROM python:latest

RUN pip install -U pip wheel setuptools && pip install zmq aiohttp
RUN apt update -y && apt install -y dnsutils

CMD ["/bin/bash"]