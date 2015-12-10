# -*- coding: utf-8 -*-
import requests

from amplify.agent.util import host
from amplify.agent.context import context
from amplify.agent.containers.abstract import AbstractObject
from amplify.agent.containers.nginx.collectors.accesslog import NginxAccessLogsCollector
from amplify.agent.containers.nginx.collectors.errorlog import NginxErrorLogsCollector
from amplify.agent.containers.nginx.collectors.meta.common import NginxCommonMetaCollector
from amplify.agent.containers.nginx.collectors.meta.deb import NginxDebianMetaCollector
from amplify.agent.containers.nginx.collectors.meta.centos import NginxCentosMetaCollector
from amplify.agent.containers.nginx.collectors.metrics import NginxMetricsCollector
from amplify.agent.containers.nginx.config.config import NginxConfig
from amplify.agent.containers.nginx.collectors.config import NginxConfigCollector
from amplify.agent.eventd import INFO

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev", "Grant Hulegaard"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class NginxObject(AbstractObject):
    type = 'nginx'

    def __init__(self, **kwargs):
        super(NginxObject, self).__init__(**kwargs)

        self.local_id = self.data['local_id']
        self.pid = self.data['pid']
        self.version = self.data['version']
        self.workers = self.data['workers']
        self.prefix = self.data['prefix']
        self.bin_path = self.data['bin_path']
        self.conf_path = self.data['conf_path']

        self.config = NginxConfig(self.conf_path, prefix=self.prefix)
        self.config.full_parse()

        self.plus_status_url = self.get_alive_plus_status_url()
        self.plus_status_enabled = True if self.plus_status_url else False
        self.stub_status_url = self.get_alive_stub_status_url()
        self.stub_status_enabled = True if self.stub_status_url else False
        self.status_module_enabled = False  # nginx+

        self.upload_config = self.data.get('upload_config') or \
                             context.app_config['containers'][self.type].get('upload_config', False)

        self.run_config_test = self.data.get('run_test') or \
                               context.app_config['containers'][self.type].get('run_test', False)

        self.processes = []

        meta_collector_class = NginxCommonMetaCollector
        if host.os_name() == 'linux':
            if host.linux_name() in ('ubuntu', 'debian'):
                meta_collector_class = NginxDebianMetaCollector
            elif host.linux_name() in ('centos',):
                meta_collector_class = NginxCentosMetaCollector

        self.collectors = [
            meta_collector_class(
                object=self, interval=self.intervals['meta']
            ),
            NginxMetricsCollector(
                object=self, interval=self.intervals['metrics']
            ),
            NginxConfigCollector(
                object=self, interval=self.intervals['configs'],
            )
        ]

        # access logs
        for log_filename, format_name in self.config.access_logs.iteritems():
            log_format = self.config.log_formats.get(format_name)
            try:
                self.collectors.append(
                    NginxAccessLogsCollector(
                        object=self,
                        interval=self.intervals['logs'],
                        filename=log_filename,
                        log_format=log_format
                    )
                )

                # Send access log discovery event.
                self.eventd.event(level=INFO, message='nginx access log %s found' % log_filename)
            except IOError as e:
                exception_name = e.__class__.__name__
                context.log.error(
                    'failed to start reading log %s due to %s (maybe has no rights?)' %
                    (log_filename, exception_name)
                )
                context.log.debug('additional info:', exc_info=True)

        # error logs
        for log_filename in self.config.error_logs:
            try:
                self.collectors.append(
                    NginxErrorLogsCollector(
                        object=self,
                        interval=self.intervals['logs'],
                        filename=log_filename
                    )
                )

                # Send error log discovery event.
                self.eventd.event(level=INFO, message='nginx error log %s found' % log_filename)
            except IOError as e:
                exception_name = e.__class__.__name__
                context.log.error(
                    'failed to start reading log %s due to %s (maybe has no rights?)' %
                    (log_filename, exception_name)
                )
                context.log.debug('additional info:', exc_info=True)

    def get_alive_stub_status_url(self):
        return self.__get_alive_status(self.config.stub_status, type='stub')

    def get_alive_plus_status_url(self):
        return self.__get_alive_status(self.config.plus_status, type='plus')

    def __get_alive_status(self, url_list, type='stub'):
        """
        Tries to find alive stub status url
        Returns first alive url or None if all founded urls are not responding

        :return: None or str
        """
        for stub_url in url_list:
            for proto in ('http://', 'https://'):
                try:
                    full_stub_url = '%s%s' % (proto, stub_url)
                    stub = requests.get(full_stub_url, timeout=1, headers={'Connection': 'close'})
                    stub.raise_for_status()

                    # Send stub detected event
                    self.eventd.event(
                        level=INFO,
                        message='nginx %s_status detected, %s' % (type, full_stub_url)
                    )

                    return full_stub_url
                except:
                    context.log.error('failed to check %s_status url %s%s' % (type, proto, stub_url))
                    context.log.debug('additional info', exc_info=True)

        # Send stub undetected event
        if type == 'stub':
            self.eventd.event(
                level=INFO,
                message='nginx %s_status not found in nginx config' % type
            )
        return None
