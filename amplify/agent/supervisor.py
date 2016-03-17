# -*- coding: utf-8 -*-
import time
import pprint
import gevent

from threading import current_thread

from amplify.agent import Singleton
from amplify.agent.context import context
from amplify.agent.util import loader
from amplify.agent.bridge import Bridge
from amplify.agent.util.threads import spawn
from amplify.agent.containers.abstract import definition_id
from amplify.agent.errors import AmplifyCriticalException

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) Nginx, Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev", "Grant Hulegaard"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class Supervisor(Singleton):
    """
    Agent supervisor

    Starts dedicated threads for each data source
    """

    CONTAINER_CLASS = '%sContainer'
    CONTAINER_MODULE = 'amplify.agent.containers.%s.%s'

    def __init__(self, foreground=False):
        # daemon specific
        self.stdin_path = '/dev/null'

        if foreground:
            self.stdout_path = '/dev/stdout'
            self.stderr_path = '/dev/stderr'
        else:
            self.stdout_path = '/dev/null'
            self.stderr_path = '/dev/null'

        self.pidfile_path = context.app_config['daemon']['pid']
        self.pidfile_timeout = 1

        # init
        self.containers = {}
        self.bridge = None

        self.start_time = int(time.time())
        self.last_cloud_talk_time = 0
        self.is_running = True

    def init_containers(self):
        """
        Tries to load and create all objects containers specified in config
        """
        containers = {}
        containers_from_local_config = context.app_config['containers']

        for container_name in containers_from_local_config.keys():
            try:
                container_classname = self.CONTAINER_CLASS % container_name.title()
                container_class = loader.import_class(self.CONTAINER_MODULE % (container_name, container_classname))
                containers[container_name] = container_class()
                context.log.debug('loaded container "%s" from %s' % (container_name, container_class))
            except:
                context.log.error('failed to load container %s' % container_name, exc_info=True)
        return containers

    def run(self):
        current_thread().name = 'supervisor'

        # get initial config from cloud
        self.talk_with_cloud()

        # run containers
        self.containers = self.init_containers()
        if not self.containers:
            context.log.error('no containers configured, stopping')
            return

        # run bridge thread
        self.bridge = spawn(Bridge().run)

        # main cycle
        while self.is_running:
            try:
                time.sleep(5.0)
                context.inc_action_id()

                for container in self.containers.itervalues():
                    container._discover_objects()
                    container.run_objects()
                    container.schedule_cloud_commands()

                try:
                    self.talk_with_cloud(top_object=context.top_object.definition)
                except AmplifyCriticalException:
                    pass

                self.check_bridge()
            except OSError as e:
                if e.errno == 12:  # OSError errno 12 is a memory error (unable to allocate, out of memory, etc.)
                    context.default_log.error('OSError: [Errno %s] %s' % (e.errno, e.message), exc_info=True)
                    continue
                else:
                    raise e

    def stop(self):
        self.is_running = False

        for container in self.containers.itervalues():
            container.stop_objects()

        bridge = Bridge()
        bridge.flush_metrics()
        bridge.flush_events()

    def talk_with_cloud(self, top_object=None):
        # TODO: receive commands from cloud

        now = int(time.time())
        if now <= self.last_cloud_talk_time + context.app_config['cloud']['talk_interval']:
            return

        # talk to cloud
        try:
            cloud_response = context.http_client.post('agent/', data=top_object)
            cloud_versions = cloud_response.pop('versions')
        except:
            context.log.error('could not connect to cloud', exc_info=True)
            raise AmplifyCriticalException()

        # check agent version status
        agent_version = float(context.version.split('-')[0])
        if agent_version <= float(cloud_versions['obsolete']):
            context.log.error(
                'agent is obsolete - cloud will refuse updates until it is updated (version: %s, current: %s)' %
                (agent_version, cloud_versions['current'])
            )
            self.stop()
        elif agent_version <= float(cloud_versions['old']):
            context.log.warn(
                'agent is old - update is recommended (version: %s, current: %s)' %
                (agent_version, cloud_versions['current'])
            )

        # update special object configs
        changed_containers = []
        for obj_config in cloud_response['objects']:

            obj = obj_config['object']
            obj_type = obj['type']
            container = self.containers[obj_type]
            obj_id = definition_id(obj)

            if container.object_configs.get(obj_id, {}) != obj_config['config']:
                container.object_configs[obj_id] = obj_config['config']
                changed_containers.append(obj_type)

        for obj_type in changed_containers:
            self.containers[obj_type].stop_objects()

        # TODO work with messages
        messages = cloud_response['messages']

        # global config changes
        config_changed = context.app_config.apply(cloud_response['config'])
        if config_changed:
            context.http_client.update_cloud_url()
            context.cloud_restart = True
            if self.containers:
                context.log.info('config has changed. now running with: %s' % pprint.pformat(context.app_config.config))
                for container in self.containers.itervalues():
                    container.stop_objects()
                self.init_containers()

        context.cloud_restart = False
        self.last_cloud_talk_time = int(time.time())

    def check_bridge(self):
        """
        Check containers threads, restart if some failed
        """
        if self.bridge.ready and self.bridge.exception:
            context.log.debug('bridge exception: %s' % self.bridge.exception)
            self.bridge = gevent.spawn(Bridge().run)
