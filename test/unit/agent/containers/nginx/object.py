# -*- coding: utf-8 -*-
from hamcrest import *

from test.base import RealNginxTestCase, nginx_plus_test
from amplify.agent.containers.nginx.container import NginxContainer

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
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
        assert_that(nginx_obj.plus_status_internal_url, equal_to('http://127.0.0.1:81/plus_status'))
        assert_that(nginx_obj.plus_status_external_url, equal_to('http://status.naas.nginx.com:81/plus_status'))
