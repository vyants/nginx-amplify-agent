# -*- coding: utf-8 -*-
import copy

from collections import defaultdict

from amplify.agent import CommonDataTank, CommonDataClient


__author__ = "Mike Belov"
__copyright__ = "Copyright (C) Nginx, Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev", "Grant Hulegaard"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class MetadContainer(CommonDataTank):
    pass

class MetadClient(CommonDataClient):
    def __init__(self, *args, **kwargs):
        # Import context as a class object to avoid circular import on statsd.  This could be refactored later.
        from amplify.agent.context import context
        self.context = context

        super(MetadClient, self).__init__(*args, **kwargs)

    def meta(self, data):
        self.current = data

    def flush(self):
        if self.current:
            delivery = copy.deepcopy(self.current)
            self.current = defaultdict(dict)
            return {
                'object': self.object.definition,
                'meta': delivery,
                'agent_version': self.context.version
            }
