# -*- coding: utf-8 -*-
import copy

from amplify.agent import CommonDataTank, CommonDataClient


__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev", "Grant Hulegaard"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class ConfigdContainer(CommonDataTank):
    pass


class ConfigdClient(CommonDataClient):
    def __init__(self, *args, **kwargs):
        # Import context as a class object to avoid circular import on statsd.  This could be refactored later.
        from amplify.agent.context import context
        self.context = context

        super(ConfigdClient, self).__init__(*args, **kwargs)

    def config(self, payload, checksum):
        self.current = {
            'data': payload,
            'checksum': checksum,
        }

    def flush(self):
        if not self.current:
            return

        delivery = copy.deepcopy(self.current)
        self.current = {}
        return {
            'object': self.object.definition,
            'config': delivery,
            'agent_version': self.context.version
        }
