# -*- coding: utf-8 -*-
import gevent

from amplify.agent.context import context

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"

def spawn(f, *args, **kwargs):
    thread = gevent.spawn(f, *args, **kwargs)
    context.log.debug('started "%s"' % f)
    return thread
