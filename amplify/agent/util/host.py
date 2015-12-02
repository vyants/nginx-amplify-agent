# -*- coding: utf-8 -*-
import platform
import sys
import socket
import re
import os
import psutil
import uuid as python_uuid
import netifaces

from amplify.agent.util import subp
from amplify.agent.context import context
from amplify.agent.util.ec2 import AmazonEC2
from amplify.agent.errors import AmplifyCriticalException

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


VALID_HOSTNAME_RFC_1123_PATTERN = re.compile(
    r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$")

MAX_HOSTNAME_LEN = 255


def is_valid_hostname(name):
    """
    Validates hostname
    """
    if name.lower() in (
        'localhost',
        'localhost.localdomain',
        'localhost6.localdomain6',
        'ip6-localhost',
    ):
        context.default_log.warning(
            "Hostname: %s is local" % name
        )
        return False
    if len(name) > MAX_HOSTNAME_LEN:
        context.default_log.warning(
            "Hostname: %s is too long (max length is  %s characters)" %
            (name, MAX_HOSTNAME_LEN)
        )
        return False
    if VALID_HOSTNAME_RFC_1123_PATTERN.match(name) is None:
        context.default_log.warning(
            "Hostname: %s is not complying with RFC 1123" % name
        )
        return False
    return True


def hostname():
    """
    Get the hostname from
    - config
    - unix internals
    - ec2
    """
    result = None

    config = context.app_config
    hostname_from_config = config['credentials']['hostname']
    if hostname_from_config and is_valid_hostname(hostname_from_config):
        result = hostname_from_config

    # then move on to os-specific detection
    if result is None:
        def _get_hostname_unix():
            try:
                # fqdn
                out, err = subp.call('/bin/hostname -f')
                return out[0]
            except Exception:
                return None

        if os_name() in ['mac', 'freebsd', 'linux', 'solaris']:
            unix_hostname = _get_hostname_unix()
            if unix_hostname and is_valid_hostname(unix_hostname):
                result = unix_hostname

    # if its ec2 default hostname, try to get instance_id
    if result is not None and True in [result.lower().startswith(p) for p in [u'ip-', u'domu']]:
        instance_id = AmazonEC2.instance_id()
        if instance_id:
            result = instance_id

    # fall back on socket.gethostname()
    if result is None:
        try:
            socket_hostname = socket.gethostname()
        except socket.error:
            socket_hostname = None
        if socket_hostname and is_valid_hostname(socket_hostname):
            result = socket_hostname

    if result is None:
        raise AmplifyCriticalException(
            message='Unable to determine host name. Define it in the config file'
        )
    else:
        return result


def os_name():
    if sys.platform == 'darwin':
        return 'mac'
    elif sys.platform.find('linux') != -1:
        return 'linux'
    elif sys.platform.find('freebsd') != -1:
        return 'freebsd'
    elif sys.platform.find('sunos') != -1:
        return 'solaris'
    else:
        return sys.platform


def linux_name():
    lsb_out, _ = subp.call("lsb_release -i | awk '{print $3}'", check=False)
    if len(lsb_out):
        return lsb_out.pop(0).lower()


def is_deb():
    return os.path.isfile('/etc/debian_version')


def is_rpm():
    return os.path.isfile('/etc/redhat-release')


def uuid():
    config_uuid = context.app_config['credentials']['uuid']
    result = python_uuid.uuid5(python_uuid.NAMESPACE_DNS, platform.node() + str(python_uuid.getnode())).hex

    if config_uuid and config_uuid != result:
        context.log.warn('Real UUID != UUID from %s, maybe you changed hosts?' % context.app_config.filename)
        return config_uuid
    elif not config_uuid:
        context.app_config.save(section='credentials', key='uuid', value=result)
        context.log.debug('saved uuid %s' % result)
        return result

    return config_uuid


def block_devices():
    """
    Returns a list of all non-virtual block devices for a host
    :return: [] of str
    """
    result = []
    if os.path.exists('/sys/block/'):
        for device in os.listdir('/sys/block/'):
            pointed_at = os.readlink('/sys/block/%s' % device)
            if '/virtual/' not in pointed_at:
                result.append(device)
    return result


def alive_interfaces():
    """
    Returns a list of all network interfaces which have UP state
    see ip link show dev eth0
    will always return lo in a list if lo exists
    :return: [] of str
    """
    alive_interfaces = set()
    try:
        for interface_name, interface in psutil.net_if_stats().iteritems():
            if interface.isup:
                alive_interfaces.add(interface_name)
    except:
        context.log.debug('failed to use psutil.net_if_stats', exc_info=True)

        # fallback for centos6
        for interface_name in netifaces.interfaces():
            ip_link_out, _ = subp.call("ip link show dev %s" % interface_name, check=False)
            if ip_link_out:
                first_line = ip_link_out[0]
                r = re.match('.+state\s+(\w+)\s+.*', first_line)
                if r:
                    state = r.group(1)
                    if interface_name == 'lo' or state == 'UP':
                        alive_interfaces.add(interface_name)

    return alive_interfaces
