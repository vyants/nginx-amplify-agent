############################################################
# Dockerfile to build Nginx Amplify Agent container
# Based on Debian 8
############################################################

# Set the base image to Debian
FROM debian:8

# File Author / Maintainer
MAINTAINER Mike Belov

# Update the sources list
RUN apt-get update

# Install basic applications
RUN apt-get install -y tar curl nano wget dialog net-tools build-essential
RUN apt-get install -y --fix-missing nginx

# Install Python and Basic Python Tools
RUN apt-get install -y python python-dev python-distribute
RUN wget --no-check-certificate https://bootstrap.pypa.io/ez_setup.py -O - | python
RUN easy_install pip

# Copy the application folder inside the container
ADD . /amplify

# Get pip to download and install requirements:
RUN pip install lockfile gevent netifaces pytest-xdist ujson psutil requests netaddr pyparsing setproctitle python-daemon

ENV AMPLIFY_ENVIRONMENT development
ENV PYTHONPATH /amplify/

# Set the default directory where CMD will execute
WORKDIR /amplify

# add stub status
ADD nginx.conf /etc/nginx/nginx.conf

CMD nginx && python /amplify/nginx-amplify-agent.py start --config=/amplify/etc/agent.conf.development && tail -f /amplify/log/agent.log