# -*- coding: utf-8 -*-
import time
import gc

from collections import defaultdict
from threading import current_thread

from amplify.agent.util import memusage
from amplify.agent.context import context
from amplify.agent import Singleton
from amplify.agent.util.http import HTTPClient

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class Bridge(Singleton):
    def __init__(self):
        self.client = HTTPClient()
        self.queue = defaultdict(list)
        self.first_run = True

    def look_around(self):
        """
        Checks everything around and make appropriate tree structure
        :return: dict of structure
        """
        # TODO check docker or OS around
        tree = {'system': ['nginx']}
        return tree

    def run(self):
        # TODO: stop after 3 fatal errors
        current_thread().name = 'bridge'
        context.setup_thread_id()

        try:
            while True:
                m_size_b, m_rss_b = memusage.report()
                self.wait()

                context.inc_action_id()
                self.flush_meta()

                if not self.first_run:
                    self.flush_metrics()
                    self.flush_events()
                    self.flush_configs()
                else:
                    self.first_run = False

                gc.collect()

                m_size_a, m_rss_a = memusage.report()
                context.log.debug('mem before: (%s %s), after (%s, %s)' % (m_size_b, m_rss_b, m_size_a, m_rss_a))
                if m_rss_a >= m_rss_b:
                    context.log.debug('RSS MEMORY same or increased, diff %s' % (m_rss_a-m_rss_b))
                elif m_size_a >= m_size_b:
                    context.log.debug('VSIZE MEMORY same or increased, diff %s' % (m_size_a-m_size_b))
        except:
            context.default_log.error('failed', exc_info=True)
            raise

    def flush_meta(self):
        self._flush(container=context.metad, location='meta/')

    def flush_metrics(self):
        self._flush(container=context.statsd, location='metrics/')

    def flush_events(self):
        self._flush(container=context.eventd, location='events/')

    def flush_configs(self):
        self._flush(container=context.configd, location='nginx/config/')

    def _flush(self, container=None, location=None):
        # get structure
        objects_structure = self.look_around()

        # get root object
        # there is only one root object!
        root_type = objects_structure.keys().pop()
        root = container.flush(type=root_type).values()

        if not len(root):
            root = {'object': context.top_object.definition}
            root_only_for_structure = True
        else:
            root = root[0]
            root_only_for_structure = False

        # go through children (one level)
        root['children'] = []
        child_data_found = False
        for child_type in objects_structure[root_type]:
            for child_data in container.flush(type=child_type).itervalues():
                if child_data:
                    child_data_found = True
                    root['children'].append(child_data)

        if child_data_found or not root_only_for_structure:
            self.queue[location].append(root)
            context.default_log.debug(root)
            try:
                self.client.post(location, data=self.queue[location])
                self.queue[location] = []
            except Exception, e:
                exception_name = e.__class__.__name__
                context.log.error('failed to push data due to %s' % exception_name)
                context.log.debug('additional info:', exc_info=True)

    @staticmethod
    def wait():
        time.sleep(context.app_config['cloud']['push_interval'])
