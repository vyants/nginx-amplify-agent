# -*- coding: utf-8 -*-
import netifaces
import re
import glob
import netaddr
import psutil

from amplify.agent.util import subp
from amplify.agent.util.ec2 import AmazonEC2
from amplify.agent.util.host import os_name, alive_interfaces
from amplify.agent.context import context
from amplify.agent.containers.abstract import AbstractCollector

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev", "Grant Hulegaard"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class SystemCommonMetaCollector(AbstractCollector):
    """
    OS meta collector
    Linux only right now
    """
    short_name = 'sys_meta'

    def __init__(self, **kwargs):
        super(SystemCommonMetaCollector, self).__init__(**kwargs)

        self.uuid = self.object.data['uuid']
        self.hostname = self.object.data['hostname']
        self.ec2_metadata = AmazonEC2.read_meta()

    def collect(self):
        meta = {
            'uuid': self.uuid,
            'uname': None,
            'boot': int(psutil.boot_time()) * 1000,
            'os-type': os_name(),
            'hostname': self.hostname,
            'network': {
                'interfaces': [],
                'default': None
            },
            'disk_partitions': [],
            'release': {
                'name': None,
                'version_id': None,
                'version': None
            },
            'processor': {
                'cache': {}
            },
            'warnings': []
        }

        for method in (
            self.uname,
            self.disk_partitions,
            self.etc_release,
            self.proc_cpuinfo,
            self.lscpu,
            self.network,
            self.ec2
        ):
            try:
                method(meta)
            except Exception as e:
                exception_name = e.__class__.__name__
                context.log.error('failed to collect meta %s due to %s' % (method.__name__, exception_name))
                context.log.debug('additional info:', exc_info=True)

        self.metad.meta(meta)

    @staticmethod
    def uname(meta):
        """ uname """
        uname_out, _ = subp.call('uname -a')
        meta['uname'] = uname_out.pop(0)

    @staticmethod
    def disk_partitions(meta):
        """ disk partitions """
        meta['disk_partitions'] = [
            {
                'mountpoint': x.mountpoint,
                'device': x.device,
                'fstype': x.fstype
            } for x in psutil.disk_partitions(all=False)
        ]

    @staticmethod
    def etc_release(meta):
        """ /etc/*-release """
        mapper = {
            'name': ('NAME', 'DISTRIB_ID'),
            'version_id': ('VERSION_ID', 'DISTRIB_RELEASE'),
            'version': ('VERSION', 'DISTRIB_DESCRIPTION')
        }

        for release_file in glob.glob("/etc/*-release"):
            etc_release_out, _ = subp.call('cat %s' % release_file)
            for line in etc_release_out:
                kv = re.match('(\w+)=(.+)', line)
                if kv:
                    key, value = kv.group(1), kv.group(2)
                    for var_name, release_vars in mapper.iteritems():
                        if key in release_vars:
                            if meta['release'][var_name] is None:
                                meta['release'][var_name] = value.replace('"', '')

        if meta['release']['name'] is None:
            meta['release']['name'] = 'unix'

    @staticmethod
    def proc_cpuinfo(meta):
        """ cat /proc/cpuinfo """
        proc_cpuinfo_out, _ = subp.call('cat /proc/cpuinfo')
        for line in proc_cpuinfo_out:
            kv = re.match('([\w|\s]+):\s*(.+)', line)
            if kv:
                key, value = kv.group(1), kv.group(2)
                if key.startswith('model name'):
                    meta['processor']['model'] = value
                elif key.startswith('cpu cores'):
                    meta['processor']['cores'] = value

    @staticmethod
    def lscpu(meta):
        """ lscpu """
        lscpu_out, _ = subp.call('lscpu')
        for line in lscpu_out:
            kv = re.match('([\w\d\s\(\)]+):\s+([\w|\d]+)', line)
            if kv:
                key, value = kv.group(1), kv.group(2)
                if key == 'Architecture':
                    meta['processor']['architecture'] = value
                elif key == 'CPU MHz':
                    meta['processor']['mhz'] = value
                elif key == 'Hypervisor vendor':
                    meta['processor']['hypervisor'] = value
                elif key == 'Virtualization type':
                    meta['processor']['virtualization'] = value
                elif key == 'CPU(s)':
                    meta['processor']['cpus'] = value
                elif 'cache' in key:
                    key = key.replace(' cache', '')
                    meta['processor']['cache'][key] = value

    @staticmethod
    def network(meta):
        """ network """

        # collect info for all hte alive interfaces
        for interface in alive_interfaces():
            addresses = netifaces.ifaddresses(interface)
            interface_info = {
                'name': interface
            }

            # collect ipv4 and ipv6 addresses
            for proto, key in {
                'ipv4': netifaces.AF_INET,
                'ipv6': netifaces.AF_INET6
            }.iteritems():
                # get the first address
                protocol_data = addresses.get(key, [{}])[0]
                if protocol_data:
                    addr = protocol_data.get('addr').split('%').pop(0)
                    netmask = protocol_data.get('netmask')

                    try:
                        prefixlen = netaddr.IPNetwork('%s/%s' % (addr, netmask)).prefixlen
                    except:
                        prefixlen = None

                    interface_info[proto] = {
                        'netmask': netmask,
                        'address': addr,
                        'prefixlen': prefixlen
                    }

            # collect mac address
            interface_info['mac'] = addresses.get(netifaces.AF_LINK, [{}])[0].get('addr')

            meta['network']['interfaces'].append(interface_info)

        # get default interface name
        netstat_out, _ = subp.call("netstat -nr | egrep -i '^0.0.0.0|default'", check=False)
        if len(netstat_out) and netstat_out[0]:
            first_matched_line = netstat_out[0]
            default_interface = first_matched_line.split(' ')[-1]
        elif len(meta['network']['interfaces']):
            default_interface = meta['network']['interfaces'][0]['name']
        else:
            default_interface = None

        meta['network']['default'] = default_interface

    def ec2(self, meta):
        """ ec2 """
        if self.ec2_metadata:
            meta['ec2'] = self.ec2_metadata
