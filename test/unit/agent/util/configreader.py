# -*- coding: utf-8 -*-
from hamcrest import *

from test.base import BaseTestCase
from amplify.agent.util import configreader

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class ConfigreaderTestCase(BaseTestCase):
    def test_read_app_config(self):
        conf = configreader.read('app')
        assert_that(conf, instance_of(object))
        assert_that(conf.config, has_key('daemon'))
        assert_that(conf.config, has_key('credentials'))

    def test_read_raise_error_if_not_exists(self):
        assert_that(calling(configreader.read).with_args('foo'), raises(Exception))
