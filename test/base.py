# -*- coding: utf-8 -*-
from gevent import monkey
monkey.patch_all(socket=False, subprocess=True)

import os
import imp
import pytest
import random
import shutil

from unittest import TestCase

import test.config.app

from amplify.agent.util import subp
from amplify.agent.util import configreader
from amplify.agent.context import context
from amplify.agent.containers.abstract import AbstractObject

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"



class BaseTestCase(TestCase):
    def setup_method(self, method):
        imp.reload(configreader)
        imp.reload(test.config.app)

        context.setup(
            app='test',
            app_config=test.config.app.TestingConfig()
        )
        context.setup_thread_id()

        context.default_log.info(
            '%s %s::%s %s' % ('=' * 20, self.__class__.__name__, self._testMethodName, '=' * 20)
        )

    def teardown_method(self, method):
        pass


class WithConfigTestCase(BaseTestCase):

    def setup_method(self, method):
        super(WithConfigTestCase, self).setup_method(method)
        self.original_file = test.config.app.TestingConfig.filename
        self.fake_config_file = '%s.%s' % (self.original_file, self._testMethodName)
        test.config.app.TestingConfig.filename = self.fake_config_file

    def teardown_method(self, method):
        if os.path.exists(self.fake_config_file):
            os.remove(self.fake_config_file)
        test.config.app.TestingConfig.filename = self.original_file

    def mk_test_config(self, config=None):
        if os.path.exists(self.original_file):
            shutil.copyfile(self.original_file, self.fake_config_file)
        imp.reload(test.config.app)
        context.app_config = test.config.app.TestingConfig()

class NginxCollectorTestCase(BaseTestCase):
    """
    Special class for collector tests
    Creates statsd stubd and object stub for collector envrionment
    """
    def setup_method(self, method):
        super(NginxCollectorTestCase, self).setup_method(method)

        class FakeNginxObject(AbstractObject):
            type = 'nginx'

        local_id = random.randint(1, 10000000)

        self.fake_object = FakeNginxObject(
            definition={
                'local_id': local_id,
            },
            data={
                'bin_path': '/usr/sbin/nginx',
                'conf_path': '/etc/nginx/nginx.conf',
                'pid': '123',
                'local_id': local_id,
                'workers': []
            }
        )


class RealNginxTestCase(BaseTestCase):
    """
    Special class for tests on real nginx
    Launches nginx on setup and stops it on teardown
    """
    def setup_method(self, method):
        super(RealNginxTestCase, self).setup_method(method)
        self.second_started = False
        subp.call('service nginx start')

    def teardown_method(self, method):
        subp.call('pgrep nginx |sudo xargs kill -SIGKILL')
        super(RealNginxTestCase, self).teardown_method(method)

    def reload_nginx(self):
        subp.call('service nginx reload')

    def start_second_nginx(self):
        subp.call('/usr/sbin/nginx2 -c /etc/nginx/nginx2.conf')
        self.second_started = True

    def restart_nginx(self):
        subp.call('service nginx restart')


future_test = pytest.mark.skipif(1 > 0, reason='This test will be written in future')
