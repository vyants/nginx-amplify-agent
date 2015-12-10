# -*- coding: utf-8 -*-
import copy

from amplify.agent.context import context
from amplify.agent.containers.nginx.config.config import NginxConfig
from amplify.agent.containers.abstract import AbstractCollector
from amplify.agent.eventd import CRITICAL, WARNING, INFO

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev", "Grant Hulegaard"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class NginxConfigCollector(AbstractCollector):

    short_name = 'nginx_config'

    def __init__(self, upload_config=False, run_config_test=False, **kwargs):
        super(NginxConfigCollector, self).__init__(**kwargs)

        self.previous_files = {}
        self.previous_checksum = None

    def collect(self):
        try:
            config = NginxConfig(
                self.object.conf_path,
                binary=self.object.bin_path,
                prefix=self.object.prefix
            )

            # check if config is changed (changes are: new files, new mtimes)
            all_config_files = config.get_all_files()
            if all_config_files == self.previous_files:
                return

            # parse config tree
            config.full_parse()

            # Send event for parsing nginx config.
            # Use config.parser.filename to account for default value defined in NginxConfigParser.
            self.eventd.event(
                level=INFO,
                message='nginx config parsed, read from %s' % config.filename,
            )
            for error in config.parser_errors:
                self.eventd.event(level=WARNING, message=error)

            # run upload
            checksum = config.checksum()
            if self.object.upload_config:
                self.upload(config, checksum)

            # config changed, so we need to restart the object
            if self.previous_checksum:
                self.object.need_restart = True
            # otherwise run test
            else:
                # run test
                if self.object.run_config_test and config.total_size() < 10*1024*1024:  # 10 MB
                    run_time = config.run_test()

                    # Send event for testing nginx config.
                    if config.test_errors:
                        self.eventd.event(level=WARNING, message='nginx config test failed')
                    else:
                        self.eventd.event(level=INFO, message='nginx config tested ok')

                    for error in config.test_errors:
                        self.eventd.event(level=CRITICAL, message=error)

                    if run_time > context.app_config['containers']['nginx']['max_test_duration']:
                        context.app_config['containers']['nginx']['run_test'] = False
                        context.app_config.mark_unchangeable('run_test')
                        self.eventd.event(
                            level=WARNING,
                            message='%s -t -c %s took %s seconds, disabled until agent restart' % (
                                config.binary, config.filename, run_time
                            )
                        )
                        self.object.run_config_test = False

            self.previous_checksum = checksum
            self.previous_files = copy.copy(all_config_files)
        except Exception as e:
            exception_name = e.__class__.__name__
            context.log.error('failed to collect due to %s' % exception_name)
            context.log.debug('additional info:', exc_info=True)

            self.eventd.event(
                level=INFO,
                message='nginx config parser failed, path %s' % self.object.conf_path,
                onetime=True
            )

    def upload(self, config, checksum):
        payload = {
            'root': config.filename,
            'index': config.index,
            'tree': config.tree,
            'files': config.files,
            'errors': {'parser': len(config.parser_errors), 'test': len(config.test_errors)}
        }
        self.configd.config(payload=payload, checksum=checksum)
