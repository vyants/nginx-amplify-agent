# -*- coding: utf-8 -*-
from hamcrest import *

from test.base import RealNginxTestCase, nginx_plus_test
from amplify.agent.context import context
from amplify.agent.containers.nginx.container import NginxContainer

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) Nginx, Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class ObjectTestCase(RealNginxTestCase):

    @nginx_plus_test
    def test_plus_status_url_discovery(self):
        """
        Checks that for plus nginx we collect two status urls:
        - one for web link (with server name)
        - one for agent purposes (local url)
        """
        container = NginxContainer()
        container.discover_objects()
        assert_that(container.objects, has_length(1))

        # get nginx object
        nginx_obj = container.objects.values().pop(0)

        # check all plus status urls
        assert_that(nginx_obj.plus_status_enabled, equal_to(True))
        assert_that(nginx_obj.plus_status_internal_url, equal_to('https://127.0.0.1:443/plus_status'))
        assert_that(nginx_obj.plus_status_external_url, equal_to('http://status.naas.nginx.com:443/plus_status_bad'))

    @nginx_plus_test
    def test_bad_plus_status_url_discovery(self):
        self.stop_first_nginx()
        self.start_second_nginx(conf='nginx_bad_status.conf')
        container = NginxContainer()
        container.discover_objects()

        assert_that(container.objects, has_length(1))

        # get nginx object
        nginx_obj = container.objects.values().pop(0)

        # check all plus status urls
        assert_that(nginx_obj.plus_status_enabled, equal_to(True))
        assert_that(nginx_obj.plus_status_internal_url, equal_to(None))
        assert_that(nginx_obj.plus_status_external_url, equal_to('http://bad.status.naas.nginx.com:82/plus_status'))

