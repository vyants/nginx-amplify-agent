# -*- coding: utf-8 -*-
from amplify.agent.containers.nginx.log.access import NginxAccessLogParser
from amplify.agent.util.tail import FileTail
from amplify.agent.context import context
from amplify.agent.containers.abstract import AbstractCollector

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev", "Grant Hulegaard"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class NginxAccessLogsCollector(AbstractCollector):

    short_name = 'nginx_alog'

    counters = (
        'http.status.1xx',
        'http.status.2xx',
        'http.status.3xx',
        'http.status.4xx',
        'http.status.5xx',
        'http.status.discarded'
    )

    def __init__(self, filename=None, log_format=None, tail=None, **kwargs):
        super(NginxAccessLogsCollector, self).__init__(**kwargs)
        self.filename = filename
        self.parser = NginxAccessLogParser(log_format)
        self.tail = tail if tail is not None else FileTail(filename)

    def collect(self):
        self.init_counters()  # set all counters to 0

        count = 0
        for line in self.tail:
            count += 1
            try:
                parsed = self.parser.parse(line)
            except:
                context.log.debug('could parse line %s' % line, exc_info=True)
                parsed = None

            if not parsed:
                continue

            if parsed['malformed']:
                self.request_malformed()
            else:
                for method in (
                    self.http_method,
                    self.http_status,
                    self.http_version,
                    self.bytes_sent_rcvd,
                    self.gzip_ration,
                    self.request_time,
                    self.upstreams
                ):
                    try:
                        method(parsed)
                    except Exception as e:
                        exception_name = e.__class__.__name__
                        context.log.error(
                            'failed to collect log metrics %s due to %s' % (method.__name__, exception_name))
                        context.log.debug('additional info:', exc_info=True)

        context.log.debug('%s processed %s lines from %s' % (self.object.id, count, self.filename))

    def request_malformed(self):
        """
        nginx.http.request.malformed
        """
        self.statsd.incr('http.request.malformed')

    def http_method(self, data):
        """
        nginx.http.method.head
        nginx.http.method.get
        nginx.http.method.post
        nginx.http.method.inc
        nginx.http.method.put
        nginx.http.method.del
        nginx.http.method.other
        """
        if 'http_method' in data:
            method = data['http_method']
            metric_name = 'http.method.%s' % method.lower()
            self.statsd.incr(metric_name)

    def http_status(self, data):
        """
        nginx.http.status.1xx
        nginx.http.status.2xx
        nginx.http.status.3xx
        nginx.http.status.4xx
        nginx.http.status.5xx
        nginx.http.status.discarded
        """
        if 'status' in data:
            status = data['status']
            suffix = 'discarded' if status in ('499', '444', '408') else '%sxx' % status[0]
            metric_name = 'http.status.%s' % suffix
            self.statsd.incr(metric_name)

    def http_version(self, data):
        """
        nginx.http.v0_9
        nginx.http.v1_0
        nginx.http.v1_1
        nginx.http.v2
        """
        if 'http_version' in data:
            version = data['http_version']
            if version.startswith('0.9'):
                suffix = '0_9'
            elif version.startswith('1.0'):
                suffix = '1_0'
            elif version.startswith('1.1'):
                suffix = '1_1'
            elif version.startswith('2.0'):
                suffix = '2'
            else:
                suffix = version.replace('.', '_')

            metric_name = 'http.v%s' % suffix
            self.statsd.incr(metric_name)

    def bytes_sent_rcvd(self, data):
        """
        nginx.http.request.body_bytes_sent
        nginx.http.request.bytes_sent
        nginx.http.request.length
        """
        if 'request_length' in data:
            self.statsd.incr('http.request.length', data['request_length'])

        if 'body_bytes_sent' in data:
            self.statsd.incr('http.request.body_bytes_sent', data['body_bytes_sent'])

        if 'bytes_sent' in data:
            self.statsd.incr('http.request.bytes_sent', data['bytes_sent'])

    def gzip_ration(self, data):
        """
        nginx.http.gzip.ratio
        """
        if 'gzip_ratio' in data:
            self.statsd.average('http.gzip.ratio', data['gzip_ratio'])

    def request_time(self, data):
        """
        nginx.http.request.time
        nginx.http.request.time.median
        nginx.http.request.time.max
        nginx.http.request.time.pctl95
        nginx.http.request.time.count
        """
        # TODO: upstream matching
        if 'request_time' in data:
            self.statsd.timer('http.request.time', sum(data['request_time']))

    def upstreams(self, data):
        """
        nginx.cache.bypass
        nginx.cache.expired
        nginx.cache.hit
        nginx.cache.miss
        nginx.cache.revalidated
        nginx.cache.stale
        nginx.cache.updating
        nginx.upstream.request.count
        nginx.upstream.next.count
        nginx.upstream.connect.time
        nginx.upstream.connect.time.median
        nginx.upstream.connect.time.max
        nginx.upstream.connect.time.pctl95
        nginx.upstream.connect.time.count
        nginx.upstream.header.time
        nginx.upstream.header.time.median
        nginx.upstream.header.time.max
        nginx.upstream.header.time.pctl95
        nginx.upstream.header.time.count
        nginx.upstream.response.time
        nginx.upstream.response.time.median
        nginx.upstream.response.time.max
        nginx.upstream.response.time.pctl95
        nginx.upstream.response.time.count
        nginx.upstream.http.status.1xx
        nginx.upstream.http.status.2xx
        nginx.upstream.http.status.3xx
        nginx.upstream.http.status.4xx
        nginx.upstream.http.status.5xx
        nginx.upstream.http.status.discarded
        nginx.upstream.http.response.length
        """
        # TODO: upstream matching

        # find out if we have info about upstreams
        empty_values = ('-', '')
        upstream_data_found = False
        for key in data.iterkeys():
            if key.startswith('upstream') and data[key] not in empty_values:
                upstream_data_found = True
                break

        if not upstream_data_found:
            return

        # counters
        upstream_response = False
        if 'upstream_status' in data:
            status = data['upstream_status']
            suffix = 'discarded' if status in ('499', '444', '408') else '%sxx' % status[0]
            upstream_response = True if suffix in ('2xx', '3xx') else False  # Set flag for upstream length processing
            metric_name = 'upstream.http.status.%s' % suffix
            self.statsd.incr(metric_name)

        if upstream_response and 'upstream_response_length' in data:
            self.statsd.incr('upstream.http.response.length', data['upstream_response_length'])

        # gauges
        upstream_switches = None
        for metric_name, key_name in {
            'upstream.connect.time': 'upstream_connect_time',
            'upstream.response.time': 'upstream_response_time',
            'upstream.header.time': 'upstream_header_time'
        }.iteritems():
            if key_name in data:
                values = data[key_name]

                # set upstream switches one time
                if len(values) > 1 and upstream_switches is None:
                    upstream_switches = len(values) - 1

                # store all values
                self.statsd.timer(metric_name, sum(values))

        # log upstream switches
        self.statsd.incr('upstream.next.count', 0 if upstream_switches is None else upstream_switches)

        # cache
        if 'upstream_cache_status' in data:
            cache_status = data['upstream_cache_status']
            if cache_status != '-':
                metric_name = 'cache.%s' % cache_status.lower()
                self.statsd.incr(metric_name)

        # log total upstream requests
        self.statsd.incr('upstream.request.count')
