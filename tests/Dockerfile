FROM ubuntu:bionic

ARG cache_bust
RUN apt update &&\
    apt -y install locales

RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8
ENV TZ Etc/UTC
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get -y install\
    software-properties-common\
    curl\
    sudo\
    lsof

RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update
RUN apt-get -y install\
    python3.8\
    python3.9\
    python3.10\
    python3.11

RUN apt-get -y install\
    python3.8-distutils\
    python3.9-distutils\
    && curl https://bootstrap.pypa.io/get-pip.py | python3.9 -

ARG uid=1000
RUN groupadd -g $uid shtest\
    && useradd -m -u $uid -g $uid shtest\
    && gpasswd -a shtest sudo\
    && echo "shtest:shtest" | chpasswd


ENV TOX_PARALLEL_NO_SPINNER=1
USER shtest
WORKDIR /home/shtest/

ENV PATH="/home/shtest/.local/bin:$PATH"
RUN pip install tox flake8 black rstcheck mypy

COPY README.rst sh.py .flake8 tox.ini tests/test.py /home/shtest/
