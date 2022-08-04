FROM ubuntu:bionic

ARG cache_bust
RUN apt-get update
RUN apt-get -y install locales

RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

RUN apt-get -y install\
    software-properties-common\
    curl\
    sudo\
    lsof

RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update
RUN apt-get -y install \
    python2.7-dev \
    python3.5-dev \
    python3.6-dev python3.6-distutils \
    python3.7-dev python3.7-distutils \
    python3.8-dev python3.8-distutils \
    python3.9-dev python3.9-distutils

ARG uid=1000
RUN groupadd -g $uid shtest\
    && useradd -m -u $uid -g $uid shtest\
    && gpasswd -a shtest sudo\
    && echo "shtest:shtest" | chpasswd

COPY requirements-dev.txt /tmp/
RUN curl https://bootstrap.pypa.io/pip/2.7/get-pip.py | python2.7 - && python2.7 -m pip install -r /tmp/requirements-dev.txt
RUN curl https://bootstrap.pypa.io/pip/3.5/get-pip.py | python3.5 - && python3.5 -m pip install -r /tmp/requirements-dev.txt
RUN curl https://bootstrap.pypa.io/pip/3.6/get-pip.py | python3.6 - && python3.6 -m pip install -r /tmp/requirements-dev.txt
RUN curl https://bootstrap.pypa.io/get-pip.py | python3.7 - && python3.7 -m pip install -r /tmp/requirements-dev.txt
RUN curl https://bootstrap.pypa.io/get-pip.py | python3.8 - && python3.8 -m pip install -r /tmp/requirements-dev.txt
RUN curl https://bootstrap.pypa.io/get-pip.py | python3.9 - && python3.9 -m pip install -r /tmp/requirements-dev.txt

USER shtest
WORKDIR /home/shtest/sh
CMD python2.7 -m unittest discover -v && \
    python3.5 -m unittest -v && \
    python3.6 -m unittest -v && \
    python3.7 -m unittest -v && \
    python3.8 -m unittest -v && \
    python3.9 -m unittest -v
