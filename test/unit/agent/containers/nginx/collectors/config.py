# -*- coding: utf-8 -*-
from hamcrest import *

from test.base import RealNginxTestCase
from amplify.agent.context import context
from amplify.agent.containers.nginx.container import NginxContainer

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) Nginx, Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class ConfigCollectorTestCase(RealNginxTestCase):

    def setup_method(self, method):
        super(ConfigCollectorTestCase, self).setup_method(method)
        self.max_test_time = context.app_config['containers']['nginx']['max_test_duration']

    def teardown_method(self, method):
        context.app_config['containers']['nginx']['max_test_duration'] = self.max_test_time
        super(ConfigCollectorTestCase, self).teardown_method(method)

    def test_collect(self):
        container = NginxContainer()
        container.discover_objects()

        nginx_obj = container.objects.values().pop(0)
        collectors = nginx_obj.collectors
        cfg_collector = collectors[2]

        # run collect
        cfg_collector.collect()
        assert_that(nginx_obj.configd.current, not_(equal_to({})))

    def test_test_run_time(self):
        container = NginxContainer()
        container.discover_objects()

        nginx_obj = container.objects.values().pop(0)
        collectors = nginx_obj.collectors
        cfg_collector = collectors[2]
        assert_that(nginx_obj.run_config_test, equal_to(True))

        # set maximum run time for test to 0.0
        context.app_config['containers']['nginx']['max_test_duration'] = 0.0

        # run collect
        cfg_collector.collect()
        assert_that(nginx_obj.run_config_test, equal_to(False))
        events = nginx_obj.eventd.current.values()
        messages = []
        for event in events:
            messages.append(event.message)

        assert_that(messages, has_item(starts_with('/usr/sbin/nginx -t -c /etc/nginx/nginx.conf took')))


class ConfigCollectorSSLTestCase(RealNginxTestCase):

    def setup_method(self, method):
        super(ConfigCollectorSSLTestCase, self).setup_method(method)
        self.original_upload_ssl = context.app_config['containers']['nginx']['upload_ssl']

    def teardown_method(self, method):
        context.app_config['containers']['nginx']['upload_ssl'] = self.original_upload_ssl
        super(ConfigCollectorSSLTestCase, self).teardown_method(method)

    def test_ssl_config_works_if_ssl_enabled(self):
        # set upload_ssl to True
        context.app_config['containers']['nginx']['upload_ssl'] = True

        container = NginxContainer()
        container.discover_objects()
        assert_that(container.objects, has_length(1))

        # get nginx object
        nginx_obj = container.objects.values().pop(0)
        collectors = nginx_obj.collectors
        cfg_collector = collectors[2]
        cfg_collector.collect()

        config = nginx_obj.configd.current
        assert_that(config['data']['ssl_certificates'], has_length(1))

    def test_ssl_config_doesnt_work_if_ssl_disabled(self):
        # set upload_ssl to True
        context.app_config['containers']['nginx']['upload_ssl'] = False

        container = NginxContainer()
        container.discover_objects()
        assert_that(container.objects, has_length(1))

        # get nginx object
        nginx_obj = container.objects.values().pop(0)
        collectors = nginx_obj.collectors
        cfg_collector = collectors[2]
        cfg_collector.collect()

        config = nginx_obj.configd.current
        assert_that(config['data']['ssl_certificates'], has_length(0))
