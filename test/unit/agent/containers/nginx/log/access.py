# -*- coding: utf-8 -*-
from hamcrest import *

from test.base import BaseTestCase
from amplify.agent.containers.nginx.log.access import NginxAccessLogParser

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class LogParserTestCase(BaseTestCase):
    def test_prepare_combined(self):
        """
        Check that we can prepare standart format:
        '$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"'
        """
        parser = NginxAccessLogParser()

        expected_keys = ['remote_addr', 'remote_user', 'time_local',
                         'request', 'status', 'body_bytes_sent',
                         'http_referer', 'http_user_agent']

        for key in expected_keys:
            assert_that(parser.keys, has_item(key))

        assert_that(parser.regex_string, equal_to(
            r'(?P<remote_addr>.+)\ \-\ (?P<remote_user>.+)\ \[(?P<time_local>.+)\]\ \"(?P<request>.+)\"\ (?P<status>\d+)\ (?P<body_bytes_sent>\d+)\ \"(?P<http_referer>.+)\"\ \"(?P<http_user_agent>.+)\"'))

    def test_parse_combined(self):
        """
        Checks that we can parse standart format

        log example:
        127.0.0.1 - - [02/Jul/2015:14:49:48 +0000] "GET /basic_status HTTP/1.1" 200 110 "-" "python-requests/2.2.1 CPython/2.7.6 Linux/3.13.0-48-generic"
        """
        parser = NginxAccessLogParser()

        line = '127.0.0.1 - - [02/Jul/2015:14:49:48 +0000] "GET /basic_status HTTP/1.1" 200 110 "-" "python-requests/2.2.1 CPython/2.7.6 Linux/3.13.0-48-generic"'
        parsed = parser.parse(line)

        # basic keys
        common_expected_keys = ['remote_addr', 'remote_user', 'time_local',
                                'request', 'status', 'body_bytes_sent',
                                'http_referer', 'http_user_agent']

        for key in common_expected_keys:
            assert_that(parsed, has_item(key))

        assert_that(parsed['status'], equal_to('200'))
        assert_that(parsed['body_bytes_sent'], equal_to(110))
        assert_that(parsed['remote_user'], equal_to('-'))
        assert_that(parsed['http_user_agent'], equal_to('python-requests/2.2.1 CPython/2.7.6 Linux/3.13.0-48-generic'))

        # request keys
        request_expected_keys = NginxAccessLogParser.request_variables
        for key in request_expected_keys:
            assert_that(parsed, has_item(key))

        assert_that(parsed['http_method'], equal_to('GET'))
        assert_that(parsed['request_uri'], equal_to('/basic_status'))
        assert_that(parsed['http_version'], equal_to('1.1'))

    def test_mailformed_request(self):
        line = '10.0.0.1 - - [03/Jul/2015:04:46:18 -0400] "/xxx?q=1 GET POST" 400 173 "-" "-" "-"'

        parser = NginxAccessLogParser()
        parsed = parser.parse(line)

        assert_that(parsed['malformed'], equal_to(True))
        assert_that(parsed['status'], equal_to('400'))

    def test_simple_user_format(self):
        """
        Check some user format
        """
        user_format = '$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" "$http_x_forwarded_for" "$host" "$request_time" $gzip_ratio'

        expected_keys = ['remote_addr', 'remote_user', 'time_local', 'request_time',
                         'request', 'status', 'body_bytes_sent', 'http_x_forwarded_for',
                         'http_referer', 'http_user_agent', 'host', 'gzip_ratio']

        parser = NginxAccessLogParser(user_format)

        for key in expected_keys:
            assert_that(parser.keys, has_item(key))

        lines = [
            '141.101.234.201 - - [03/Jul/2015:10:52:33 +0300] "POST /wp-login.php HTTP/1.1" 200 3809 "http://estevmeste.ru/wp-login.php" "Mozilla/5.0 (Windows NT 6.0; rv:34.0) Gecko/20100101 Firefox/34.0" "-" "estevmeste.ru" "0.001" -',
            '95.211.80.227 - - [03/Jul/2015:10:52:57 +0300] "PUT /stub_status HTTP/1.1" 200 109 "-" "cloudwatch-nginx-agent/1.0" "-" "defan.pp.ru" "0.001" -',
            '95.211.80.227 - - [03/Jul/2015:10:54:00 +0300] "GET /stub_status HTTP/2.1" 200 109 "-" "cloudwatch-nginx-agent/1.0" "-" "defan.pp.ru" "0.134" -'
        ]

        for line in lines:
            parsed = parser.parse(line)
            for key in expected_keys:
                assert_that(parsed, has_item(key))
            assert_that(parsed['host'], is_in(['defan.pp.ru', 'estevmeste.ru']))
            assert_that(parsed['gzip_ratio'], equal_to(0))
            assert_that(parsed['malformed'], equal_to(False))
            assert_that(parsed['request_time'], is_(instance_of(list)))
            assert_that(parsed['request_time'][0], is_(instance_of(float)))

        # check first line
        parsed = parser.parse(lines[0])
        assert_that(parsed['request_uri'], equal_to('/wp-login.php'))

        # check second line
        parsed = parser.parse(lines[1])
        assert_that(parsed['http_method'], equal_to('PUT'))

        # check second line
        parsed = parser.parse(lines[2])
        assert_that(parsed['http_version'], equal_to('2.1'))
        assert_that(parsed['request_time'], equal_to([0.134]))

    def test_complex_user_format(self):
        """
        Check some super complex user format with cache
        """
        user_format = '$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" "$http_x_forwarded_for" "$upstream_addr" "$upstream_cache_status" $connection/$connection_requests'
        line = '217.15.195.202 - - [03/Jul/2015:11:12:53 +0300] "GET /gsat/9854/5231/14 HTTP/1.1" 200 11901 "-" "tile-fetcher/0.1" "-" "173.194.32.133:80" "MISS" 62277/22'

        expected_keys = [
            'remote_addr', 'remote_user', 'time_local', 'connection',
            'request', 'status', 'body_bytes_sent', 'http_x_forwarded_for',
            'http_referer', 'http_user_agent', 'upstream_addr', 'upstream_cache_status', 'connection_requests'
        ]
        parser = NginxAccessLogParser(user_format)
        for key in expected_keys:
            assert_that(parser.keys, has_item(key))

        parsed = parser.parse(line)
        for key in expected_keys:
            assert_that(parsed, has_item(key))

        assert_that(parsed['upstream_addr'], equal_to('173.194.32.133:80'))
        assert_that(parsed['connection'], equal_to('62277'))
        assert_that(parsed['malformed'], equal_to(False))
        assert_that(parsed['upstream_cache_status'], equal_to('MISS'))

    def test_mailformed_request_time(self):
        user_format = '$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" "$http_x_forwarded_for" "$host" "$request_time" $gzip_ratio'
        line = '141.101.234.201 - - [03/Jul/2015:10:52:33 +0300] "POST /wp-login.php HTTP/1.1" 200 3809 "http://estevmeste.ru/wp-login.php" "Mozilla/5.0 (Windows NT 6.0; rv:34.0) Gecko/20100101 Firefox/34.0" "-" "estevmeste.ru" "1299760000.321" -'

        parser = NginxAccessLogParser(user_format)
        parsed = parser.parse(line)

        assert_that(parsed, is_not(has_item('request_time')))

    def test_our_config(self):
        user_format = '$remote_addr - $remote_user [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" "$http_x_forwarded_for" rt="$request_time" ua="$upstream_addr" us="$upstream_status" ut="$upstream_response_time" "$gzip_ratio"'
        line = '127.0.0.1 - - [03/Jul/2015:14:09:38 +0000] "GET /basic_status HTTP/1.1" 200 100 "-" "curl/7.35.0" "-" rt="0.000" ua="-" us="-" ut="-" "-"'

        parser = NginxAccessLogParser(user_format)
        parsed = parser.parse(line)

        assert_that(parsed, has_item('request_time'))

    def test_lonerr_config(self):
        user_format = '$remote_addr - $remote_user [$time_local] ' + \
                     '"$request" $status $body_bytes_sent "$http_referer" "$http_user_agent" ' + \
                     'rt=$request_time ut="$upstream_response_time" cs=$upstream_cache_status'

        line = \
            '1.2.3.4 - - [22/Jan/2010:19:34:21 +0300] "GET /foo/ HTTP/1.1" 200 11078 ' + \
            '"http://www.rambler.ru/" "Mozilla/5.0 (Windows; U; Windows NT 5.1" rt=0.010 ut="2.001, 0.345" cs=MISS'

        parser = NginxAccessLogParser(user_format)
        parsed = parser.parse(line)

        assert_that(parsed, has_item('upstream_response_time'))
