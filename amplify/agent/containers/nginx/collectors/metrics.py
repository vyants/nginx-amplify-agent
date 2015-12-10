# -*- coding: utf-8 -*-
import re
import time
import psutil

from amplify.agent.util.ps import Process
from amplify.agent.errors import AmplifyParseException
from amplify.agent.context import context
from amplify.agent.containers.abstract import AbstractCollector
from amplify.agent.eventd import WARNING

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev", "Grant Hulegaard"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"

STUB_RE = re.compile(r'^Active connections: (?P<connections>\d+)\s+[\w ]+\n'
                     r'\s+(?P<accepts>\d+)'
                     r'\s+(?P<handled>\d+)'
                     r'\s+(?P<requests>\d+)'
                     r'\s+Reading:\s+(?P<reading>\d+)'
                     r'\s+Writing:\s+(?P<writing>\d+)'
                     r'\s+Waiting:\s+(?P<waiting>\d+)')


class NginxMetricsCollector(AbstractCollector):

    short_name = 'nginx_metrics'

    def __init__(self, **kwargs):
        super(NginxMetricsCollector, self).__init__(**kwargs)

        self.processes = [Process(pid) for pid in self.object.workers]
        self.zombies = set()

    def collect(self):
        for method in (
            self.workers_count,
            self.memory_info,
            self.workers_fds_count,
            self.workers_rlimit_nofile,
            self.workers_io,
            self.workers_cpu,
            self.stub_status
        ):
            try:
                method()
            except psutil.NoSuchProcess as e:
                exception_name = e.__class__.__name__

                # Log exception
                context.log.warning(
                    'failed to collect metrics %s due to %s, object restart needed' %
                    (method.__name__, exception_name)
                )
                self.object.need_restart = True
            except Exception as e:
                exception_name = e.__class__.__name__

                # Fire event warning.
                self.eventd.event(
                    level=WARNING,
                    message="can't obtain worker process metrics (maybe permissions?)",
                    onetime=True
                )

                # Log exception
                context.log.error('failed to collect metrics %s due to %s' % (method.__name__, exception_name))
                context.log.debug('additional info:', exc_info=True)

    def workers_count(self):
        """nginx.workers.count"""
        self.statsd.gauge('workers.count', len(self.object.workers))

    def handle_zombie(self, pid):
        """
        removes pid from workers list
        :param pid: zombie pid
        """
        context.log.warning('zombie process %s found' % pid)
        self.zombies.add(pid)

    def memory_info(self):
        """
        memory info

        nginx.workers.mem.rss
        nginx.workers.mem.vms
        nginx.workers.mem.rss_pct
        """
        rss, vms, pct = 0, 0, 0.0
        for p in self.processes:
            if p.pid in self.zombies:
                continue
            try:
                mem_info = p.memory_info()
                rss += mem_info.rss
                vms += mem_info.vms
                pct += p.memory_percent()
            except psutil.ZombieProcess:
                self.handle_zombie(p.pid)

        self.statsd.gauge('workers.mem.rss', rss)
        self.statsd.gauge('workers.mem.vms', vms)
        self.statsd.gauge('workers.mem.rss_pct', pct)

    def workers_fds_count(self):
        """nginx.workers.fds_count"""
        fds = 0
        for p in self.processes:
            if p.pid in self.zombies:
                continue
            try:
                fds += p.num_fds()
            except psutil.ZombieProcess:
                self.handle_zombie(p.pid)
        self.statsd.incr('workers.fds_count', fds)

    def workers_rlimit_nofile(self):
        """
        nginx.workers.rlimit_nofile

        sum for all hard limits (second value of rlimit)
        """
        rlimit = 0
        for p in self.processes:
            if p.pid in self.zombies:
                continue
            try:
                rlimit += p.rlimit_nofile()
            except psutil.ZombieProcess:
                self.handle_zombie(p.pid)
        self.statsd.gauge('workers.rlimit_nofile', rlimit)

    def workers_io(self):
        """
        io

        nginx.workers.io.kbs_r
        nginx.workers.io.kbs_w
        """
        # collect raw data
        read, write = 0, 0
        for p in self.processes:
            if p.pid in self.zombies:
                continue
            try:
                io = p.io_counters()
                read += io.read_bytes
                write += io.write_bytes
            except psutil.ZombieProcess:
                self.handle_zombie(p.pid)
        current_stamp = int(time.time())

        # kilobytes!
        read /= 1024
        write /= 1024

        # get deltas and store metrics
        for metric_name, value in {'workers.io.kbs_r': read, 'workers.io.kbs_w': write}.iteritems():
            prev_stamp, prev_value = self.previous_values.get(metric_name, [None, None])
            if prev_stamp:
                value_delta = value - prev_value
                self.statsd.incr(metric_name, value_delta)
            self.previous_values[metric_name] = [current_stamp, value]

    def workers_cpu(self):
        """
        cpu

        nginx.workers.cpu.system
        nginx.workers.cpu.user
        """
        worker_user, worker_sys = 0.0, 0.0
        for p in self.processes:
            if p.pid in self.zombies:
                continue
            try:
                u, s = p.cpu_percent()
                worker_user += u
                worker_sys += s
            except psutil.ZombieProcess:
                self.handle_zombie(p.pid)
        self.statsd.gauge('workers.cpu.total', worker_user + worker_sys)
        self.statsd.gauge('workers.cpu.user', worker_user)
        self.statsd.gauge('workers.cpu.system', worker_sys)

    def stub_status(self):
        """
        stub status metrics

        nginx.http.conn.current = ss.active
        nginx.http.conn.active = ss.active - ss.waiting
        nginx.http.conn.idle = ss.waiting
        nginx.http.request.reading = ss.reading
        nginx.http.request.writing = ss.writing
        nginx.http.conn.dropped = ss.accepts - ss.handled
        nginx.http.conn.dropped_s = (current nginx.conn.dropped - previous nginx.conn.dropped) /
                                    (current measurement timestamp - previous timestamp)
        nginx.http.conn.accepted = ss.accepts
        nginx.http.conn.accepted_s = (current nginx.conn.accepted - previous nginx.conn.accepted) /
                                    (current measurement timestamp - previous timestamp)
        """
        if not self.object.stub_status_enabled:
            return

        stub_body = ''
        stub = {}
        stub_time = int(time.time())

        # get stub status body

        try:
            stub_body = context.http_client.get(self.object.stub_status_url, timeout=1, json=False)
        except:
            context.log.error('failed to check stub_status url %s' % self.object.stub_status_url)
            context.log.debug('additional info', exc_info=True)

        # parse body
        try:
            gre = STUB_RE.match(stub_body)
            if not gre:
                raise AmplifyParseException(message='stub status %s' % stub_body)
            for field in ('connections', 'accepts', 'handled', 'requests', 'reading', 'writing', 'waiting'):
                stub[field] = int(gre.group(field))
        except:
            context.log.error('failed to parse stub_status body')
            raise

        # store some variables for further use
        stub['dropped'] = stub['accepts'] - stub['handled']

        # gauges
        self.statsd.gauge('http.conn.current', stub['connections'])
        self.statsd.gauge('http.conn.active', stub['connections'] - stub['waiting'])
        self.statsd.gauge('http.conn.idle', stub['waiting'])
        self.statsd.gauge('http.request.writing', stub['writing'])
        self.statsd.gauge('http.request.reading', stub['reading'])
        self.statsd.gauge('http.request.current', stub['reading'] + stub['writing'])

        # counters
        counted_vars = {
            'http.request.count': 'requests',
            'http.conn.accepted': 'accepts',
            'http.conn.dropped': 'dropped'
        }
        for metric_name, stub_name in counted_vars.iteritems():
            value, stamp = stub[stub_name], stub_time
            prev_stamp, prev_value = self.previous_values.get(metric_name, [None, None])

            if prev_stamp:
                value_delta = value - prev_value
                self.statsd.incr(metric_name, value_delta)

            self.previous_values[metric_name] = [stamp, value]
