# -*- coding: utf-8 -*-
import os

from hamcrest import *

from test.base import BaseTestCase
from amplify.agent.context import context
from amplify.agent.containers.nginx.config.config import NginxConfig

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


simple_config = os.getcwd() + '/test/fixtures/nginx/simple/nginx.conf'
complex_config = os.getcwd() + '/test/fixtures/nginx/complex/nginx.conf'
huge_config = os.getcwd() + '/test/fixtures/nginx/huge/nginx.conf'
broken_config = os.getcwd() + '/test/fixtures/nginx/broken/nginx.conf'


class ConfigTestCase(BaseTestCase):

    def test_parse_simple(self):
        config = NginxConfig(simple_config)

        # error logs
        assert_that(config.error_logs, has_length(1))
        assert_that(config.error_logs[0], equal_to('/var/log/nginx/error.log'))

        # access logs
        assert_that(config.access_logs, has_length(2))
        assert_that(config.access_logs, has_item('/var/log/nginx/access.log'))
        assert_that(config.access_logs, has_item('/var/log/nginx/superaccess.log'))
        assert_that(config.access_logs['/var/log/nginx/access.log'], equal_to('super_log_format'))

        # log formats
        assert_that(config.log_formats, has_length(1))
        assert_that(config.log_formats, has_item('super_log_format'))
        assert_that(
            config.log_formats['super_log_format'],
            equal_to(
                '$remote_addr - $remote_user [$time_local] "$request" $status ' +
                '$body_bytes_sent "$http_referer" "$http_user_agent" "$http_x_forwarded_for" ' +
                'rt="$request_time" ua="$upstream_addr" us="$upstream_status" ' +
                'ut="$upstream_response_time" "$gzip_ratio"'
            )
        )

        # stub status url
        assert_that(config.stub_status, has_length(1))
        assert_that(config.stub_status[0], equal_to('127.0.0.1:81/basic_status'))

        # status url
        assert_that(config.plus_status, has_length(1))
        assert_that(config.plus_status[0], equal_to('127.0.0.1:81/plus_status'))

    def test_parse_huge(self):
        config = NginxConfig(huge_config)

        # error logs
        assert_that(config.error_logs, has_length(1))
        assert_that(config.error_logs[0], equal_to('/var/log/nginx-error.log'))

        # access logs
        assert_that(config.access_logs, has_length(2))
        assert_that(config.access_logs, has_item('/var/log/default.log'))
        assert_that(config.access_logs, has_item('/var/log/pp.log'))
        assert_that(config.access_logs['/var/log/pp.log'], equal_to('main'))

        # log formats
        assert_that(config.log_formats, has_length(1))
        assert_that(config.log_formats, has_item('main'))
        assert_that(
            config.log_formats['main'],
            equal_to(
                '$remote_addr - $remote_user [$time_local] "$request" ' +
                '$status $body_bytes_sent "$http_referer" "$http_user_agent" "$http_x_forwarded_for"'
            )
        )

        # stub status url
        assert_that(config.stub_status, has_length(2))
        assert_that(config.stub_status[0], equal_to('127.0.0.1:80/nginx_status'))

    def test_parse_complex(self):
        config = NginxConfig(complex_config)

        context.log.info(config.index)
        context.log.info(config.tree)
        context.log.info(config.files)
        context.log.info(config.checksum())

        # error logs
        assert_that(config.error_logs, has_length(0))

        # access logs
        assert_that(config.access_logs, has_length(0))

        # log formats
        assert_that(config.log_formats, has_length(0))

        # stub status url
        assert_that(config.stub_status, has_length(0))

    def test_broken(self):
        config = NginxConfig(broken_config)

        assert_that(config.tree, equal_to({}))
        assert_that(config.parser_errors, has_length(1))

    def test_broken_includes(self):
        config = NginxConfig(huge_config)

        assert_that(config.tree, not_(equal_to({})))
        assert_that(config.parser_errors, has_length(5))  # 5 missing includes
