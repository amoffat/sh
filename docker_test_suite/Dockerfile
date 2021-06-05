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
    python\
    lsof

RUN add-apt-repository ppa:deadsnakes/ppa
RUN apt-get update
RUN apt-get -y install\
    python2.6\
    python2.7\
    python3.1\
    python3.2\
    python3.3\
    python3.4\
    python3.5\
    python3.6\
    python3.7\
    python3.8\
    python3.9

RUN apt-get -y install python3-distutils\
    && curl https://bootstrap.pypa.io/get-pip.py | python -

ARG uid=1000
RUN groupadd -g $uid shtest\
    && useradd -m -u $uid -g $uid shtest\
    && gpasswd -a shtest sudo\
    && echo "shtest:shtest" | chpasswd

COPY requirements-dev.txt /tmp/
RUN pip install -r /tmp/requirements-dev.txt

USER shtest
WORKDIR /home/shtest/sh
ENTRYPOINT ["python", "sh.py", "test"]
