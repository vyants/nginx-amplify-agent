# -*- coding: utf-8 -*-
import os

from hamcrest import *

from test.base import BaseTestCase
from amplify.agent.util.tail import FileTail

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) Nginx, Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class TailTestCase(BaseTestCase):
    test_log = 'log/something.log'
    test_log_rotated = 'log/something.log.rotated'

    def setup_method(self, method):
        # write something to create file
        self.write_log('start')

    def write_log(self, line):
        os.system('echo %s >> %s' % (line, self.test_log))
        """
        with open(self.test_log, 'a+') as f:
            print 'writing "%s" to %s' % (line, f.name)
            f.writelines([line])
        """

    def teardown_method(self, method):
        # remove test log
        for filename in (self.test_log, self.test_log_rotated):
            if os.path.exists(filename):
                os.remove(filename)

        super(TailTestCase, self).teardown_method(method)

    def test_read_new_lines(self):
        tail = FileTail(filename=self.test_log)

        # write messages and read them
        for i in xrange(10):
            line = "this is %s line" % i
            self.write_log(line)
            new_lines = tail.readlines()
            assert_that(new_lines, has_length(1))
            assert_that(new_lines.pop(), equal_to(line))

    def test_rotate(self):
        tail = FileTail(filename=self.test_log)

        # rotate it
        os.rename(self.test_log, self.test_log_rotated)

        # write something in a new one
        self.write_log("from a new file")

        # read tail and get two lines
        new_lines = tail.readlines()
        assert_that(new_lines, has_length(1))
        assert_that(new_lines, equal_to(['from a new file']))

    def test_lose_changes_while_rotate(self):
        tail = FileTail(filename=self.test_log)

        # write something
        self.write_log("from the old file")

        # rotate it
        os.rename(self.test_log, self.test_log_rotated)

        # write something in a new one
        self.write_log("from a new file")

        # read tail and get two lines
        new_lines = tail.readlines()
        assert_that(new_lines, has_length(1))
        assert_that(new_lines, equal_to(['from a new file']))

    def test_no_new_lines(self):
        # check one new line
        tail = FileTail(filename=self.test_log)
        self.write_log('something')
        new_lines = tail.readlines()
        assert_that(new_lines, has_length(1))

        # check no new lines
        new_lines = tail.readlines()
        assert_that(new_lines, has_length(0))

        # and check again one new line
        tail = FileTail(filename=self.test_log)
        self.write_log('something')
        new_lines = tail.readlines()
        assert_that(new_lines, has_length(1))
