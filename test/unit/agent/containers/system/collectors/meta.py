# -*- coding: utf-8 -*-
import netifaces
import psutil

from hamcrest import *

from test.base import BaseTestCase
from amplify.agent.util import subp
from amplify.agent.containers.system.container import SystemContainer
from amplify.agent.containers.system.collectors.meta.common import SystemCommonMetaCollector


__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class MetaParsersTestCase(BaseTestCase):

    def test_parse_only_alive_interfaces(self):
        container = SystemContainer()
        container.discover_objects()

        os_obj = container.objects.values().pop()
        collector = SystemCommonMetaCollector(object=os_obj)
        collector.collect()

        # get interfaces info
        all_interfaces = netifaces.interfaces()
        alive_interfaces = set()
        down_interfaces = set()
        for interface_name, interface in psutil.net_if_stats().iteritems():
            if interface.isup:
                alive_interfaces.add(interface_name)
            else:
                down_interfaces.add(interface_name)

        # check intefaces
        collected_interfaces = os_obj.metad.current['network']['interfaces']
        for interface_info in collected_interfaces:
            name = interface_info['name']
            assert_that(all_interfaces, has_item(name))
            assert_that(alive_interfaces, has_item(name))
            assert_that(down_interfaces, not_(has_item(name)))

    def test_default_interface(self):
        container = SystemContainer()
        container.discover_objects()

        os_obj = container.objects.values().pop()
        collector = SystemCommonMetaCollector(object=os_obj)
        collector.collect()

        default_from_netstat, _ = subp.call(
            'netstat -nr | egrep -i "^0.0.0.0|default" | head -1 | sed "s/.*[ ]\([^ ][^ ]*\)$/\\1/"'
        )[0]

        default_interface = os_obj.metad.current['network']['default']

        assert_that(default_interface, equal_to(default_from_netstat))

