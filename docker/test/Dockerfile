############################################################
# Dockerfile to build Nginx Amplify Agent autotests
# Based on Ubuntu
############################################################

# Set the base image to Ubuntu
FROM ubuntu:14.04

# File Author / Maintainer
MAINTAINER Mike Belov

# Add the application resources URL
RUN echo "deb http://archive.ubuntu.com/ubuntu/ $(lsb_release -sc) main universe" >> /etc/apt/sources.list

# Update the sources list
RUN apt-get update

# Install basic applications
RUN apt-get install -y tar curl nano wget dialog net-tools build-essential
RUN apt-get install -y --fix-missing nginx
RUN rm -rf  /run && mkdir /run

# Install Python and Basic Python Tools
RUN apt-get install -y python python-dev python-distribute python-daemon
RUN wget --no-check-certificate https://bootstrap.pypa.io/ez_setup.py -O - | python
RUN easy_install pip

# Copy the application folder inside the container
ADD . /amplify

# Get pip to download and install requirements:
RUN pip install gevent netifaces pytest pytest-xdist pyhamcrest ujson psutil==3.2.2 requests netaddr pyparsing setproctitle

ENV AMPLIFY_ENVIRONMENT testing
ENV PYTHONPATH /amplify

# Set the default directory where CMD will execute
WORKDIR /amplify

# add config
ADD nginx.conf /etc/nginx/nginx.conf
ADD nginx2.conf /etc/nginx/nginx2.conf

# add ssl
ADD amplify-agent-test.crt /etc/nginx/certs.d/amplify-agent-test.crt
ADD amplify-agent-test.key /etc/nginx/certs.d/amplify-agent-test.key

# cp nginx
RUN cp /usr/sbin/nginx /usr/sbin/nginx2

CMD bash