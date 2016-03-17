# -*- coding: utf-8 -*-
import time

from hamcrest import *

from test.base import RealNginxTestCase, nginx_plus_test
from amplify.agent.containers.nginx.container import NginxContainer

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) Nginx, Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev", "Grant Hulegaard"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class NginxMetricsTestCase(RealNginxTestCase):

    def test_stub_status(self):
        container = NginxContainer()
        container.discover_objects()
        assert_that(container.objects, has_length(1))

        # get nginx object
        nginx_obj = container.objects.values().pop(0)

        # get metrics collector - the second from the list
        collectors = nginx_obj.collectors
        metrics_collector = collectors[1]

        # run plus status - twice, because counters will appear only on the second run
        metrics_collector.stub_status()
        time.sleep(1)
        metrics_collector.stub_status()

        # check counters
        metrics = nginx_obj.statsd.current
        assert_that(metrics, has_item('counter'))
        counters = metrics['counter']
        assert_that(counters, has_item('nginx.http.conn.accepted'))
        assert_that(counters, has_item('nginx.http.request.count'))
        assert_that(counters, has_item('nginx.http.conn.dropped'))

        # check gauges
        assert_that(metrics, has_item('gauge'))
        gauges = metrics['gauge']
        assert_that(gauges, has_item('nginx.http.conn.active'))
        assert_that(gauges, has_item('nginx.http.conn.current'))
        assert_that(gauges, has_item('nginx.http.conn.idle'))
        assert_that(gauges, has_item('nginx.http.request.current'))
        assert_that(gauges, has_item('nginx.http.request.writing'))
        assert_that(gauges, has_item('nginx.http.request.reading'))

    @nginx_plus_test
    def test_plus_status(self):
        time.sleep(1)  # Give N+ some time to start
        container = NginxContainer()
        container.discover_objects()
        assert_that(container.objects, has_length(1))

        # get nginx object
        nginx_obj = container.objects.values().pop(0)

        # get metrics collector - the second from the list
        collectors = nginx_obj.collectors
        metrics_collector = collectors[1]

        # run plus status - twice, because counters will appear only on the second run
        metrics_collector.plus_status()
        time.sleep(1)
        metrics_collector.plus_status()

        # check counters
        metrics = nginx_obj.statsd.current
        assert_that(metrics, has_item('counter'))
        counters = metrics['counter']
        assert_that(counters, has_item('nginx.http.conn.accepted'))
        assert_that(counters, has_item('nginx.http.request.count'))
        assert_that(counters, has_item('nginx.http.conn.dropped'))

        # check gauges
        assert_that(metrics, has_item('gauge'))
        gauges = metrics['gauge']
        assert_that(gauges, has_item('nginx.http.conn.active'))
        assert_that(gauges, has_item('nginx.http.conn.current'))
        assert_that(gauges, has_item('nginx.http.conn.idle'))
        assert_that(gauges, has_item('nginx.http.request.current'))

    @nginx_plus_test
    def test_plus_status_priority(self):
        """
        Checks that if we can reach plus status then we don't use stub_status
        """
        time.sleep(1)  # Give N+ some time to start
        container = NginxContainer()
        container.discover_objects()
        assert_that(container.objects, has_length(1))

        # get nginx object
        nginx_obj = container.objects.values().pop(0)

        # check that it has n+ status and stub_status enabled
        assert_that(nginx_obj.plus_status_enabled, equal_to(True))
        assert_that(nginx_obj.stub_status_enabled, equal_to(True))

        # get metrics collector - the second from the list
        collectors = nginx_obj.collectors
        metrics_collector = collectors[1]

        # run status twice
        metrics_collector.status()
        time.sleep(1)
        metrics_collector.status()

        # check gauges - we should't see request.writing/reading here, because n+ status doesn't have those
        metrics = nginx_obj.statsd.current
        assert_that(metrics, has_item('gauge'))
        gauges = metrics['gauge']
        assert_that(gauges, not_(has_item('nginx.http.request.writing')))
        assert_that(gauges, not_(has_item('nginx.http.request.reading')))

