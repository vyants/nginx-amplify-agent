# -*- coding: utf-8 -*-
from amplify.agent.containers.nginx.log.error import NginxErrorLogParser
from amplify.agent.util.tail import FileTail
from amplify.agent.context import context
from amplify.agent.containers.abstract import AbstractCollector

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"



class NginxErrorLogsCollector(AbstractCollector):

    short_name = 'nginx_elog'

    def __init__(self, filename=None, log_format=None, tail=None, **kwargs):
        super(NginxErrorLogsCollector, self).__init__(**kwargs)
        self.filename = filename
        self.parser = NginxErrorLogParser()
        self.tail = tail if tail is not None else FileTail(filename)

    def collect(self):
        count = 0
        for line in self.tail:
            count += 1
            try:
                error = self.parser.parse(line)
            except:
                context.log.debug('could not parse line %s' % line, exc_info=True)
                error = None

            if error:
                try:
                    self.statsd.incr(error)
                except Exception, e:
                    exception_name = e.__class__.__name__
                    context.log.error('failed to collect error log metrics due to %s' % exception_name)
                    context.log.debug('additional info:', exc_info=True)

        context.log.debug('%s processed %s lines from %s' % (self.object.id, count, self.filename))
