############################################################
# Dockerfile to build Nginx Amplify Agent container
# Based on Centos7
############################################################

# Set the base image to Centos
FROM centos:7

# File Author / Maintainer
MAINTAINER Mike Belov

# Install basic applications
RUN yum -y install tar curl wget net-tools redhat-lsb initscripts
RUN yum -y groupinstall 'Development Tools'

# Install Python and Basic Python Tools
RUN yum -y install python python-devel python-distribute
RUN wget --no-check-certificate https://bootstrap.pypa.io/ez_setup.py -O - | python
RUN easy_install pip

# Install nginx
ADD nginx.repo /etc/yum.repos.d/nginx.repo
RUN yum -y install nginx

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

CMD /usr/sbin/nginx && python /amplify/nginx-amplify-agent.py start --config=/amplify/etc/agent.conf.development && tail -f /amplify/log/agent.log