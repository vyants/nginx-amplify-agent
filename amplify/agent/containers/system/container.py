# -*- coding: utf-8 -*-
from amplify.agent.context import context
from amplify.agent.containers.abstract import AbstractContainer, definition_id
from amplify.agent.containers.system.object import SystemObject


__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class SystemContainer(AbstractContainer):
    """
    Container for system objects
    Typically we have only one object since we run in a single OS
    """

    type = 'system'

    def discover_objects(self):
        if not self.objects:
            definition = dict(
                type=self.type,
                hostname=context.hostname,
                uuid=context.uuid
            )

            data = dict(
                hostname=context.hostname,
                uuid=context.uuid
            )

            object_id = definition_id(definition)
            sys_obj = SystemObject(definition=definition, data=data)
            self.objects = {object_id: sys_obj}
            context.top_object = sys_obj
