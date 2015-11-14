# -*- coding: utf-8 -*-

from amplify.agent.supervisor import Supervisor
from test.base import BaseTestCase

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class SupervisorTestCase(BaseTestCase):
    def test_init_simple(self):
        supervisor = Supervisor()

    def test_init_with_config(self):
        pass
