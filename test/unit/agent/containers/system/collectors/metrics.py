# -*- coding: utf-8 -*-
import netifaces
import psutil

from hamcrest import *

from test.base import BaseTestCase
from amplify.agent.containers.system.container import SystemContainer
from amplify.agent.containers.system.collectors.metrics import SystemMetricsCollector


__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class MetricsParsersTestCase(BaseTestCase):

    def test_collect_only_alive_interfaces(self):
        container = SystemContainer()
        container.discover_objects()

        os_obj = container.objects.values().pop()
        collector = SystemMetricsCollector(object=os_obj)
        collector.collect()
        collector.collect()  # double collect is needed, because otherwise we do not collect metrics properly

        # get interfaces info
        all_interfaces = netifaces.interfaces()
        alive_interfaces = set()
        down_interfaces = set()
        for interface_name, interface in psutil.net_if_stats().iteritems():
            if interface.isup:
                alive_interfaces.add(interface_name)
            else:
                down_interfaces.add(interface_name)

        # check
        collected_metrics = os_obj.statsd.current
        net_metrics_found = False
        for metric in collected_metrics['counter'].keys():
            if metric.startswith('system.net.') and '|' in metric:
                net_metrics_found = True
                metric_name, label_name = metric.split('|')
                assert_that(all_interfaces, has_item(label_name))
                assert_that(alive_interfaces, has_item(label_name))
                assert_that(down_interfaces, not_(has_item(label_name)))
        assert_that(net_metrics_found, equal_to(True))

    # This test doesn't really belong here...but it was the only test file that had a usable statsd object.
    def test_flush_aggregation(self):
        container = SystemContainer()
        container.discover_objects()

        os_obj = container.objects.values().pop()
        collector = SystemMetricsCollector(object=os_obj)
        collector.collect()
        collector.collect()  # double collect is needed, because otherwise we do not collect metrics properly

        flush = collector.statsd.flush()

        for type in flush['metrics'].keys():  # e.g. 'timer', 'counter', 'gauge', 'average'
            for key in flush['metrics'][type].keys():
                # Make sure there is only one item per item in the flush.
                assert_that(len(flush['metrics'][type][key]), equal_to(1))
