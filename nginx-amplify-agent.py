#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import amplify

amplify_path = '/'.join(amplify.__file__.split('/')[:-1])
sys.path.insert(0, amplify_path)

from gevent import monkey
monkey.patch_all(socket=False, ssl=False, select=False)

from optparse import OptionParser, Option

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


usage = "usage: %prog [start|stop|configtest] [options]"

option_list = (
    Option(
        '--config',
        action='store',
        dest='config',
        type='string',
        help='path to config file',
        default=None,
    ),
    Option(
        '--pid',
        action='store',
        dest='pid',
        type='string',
        help='path to pid file',
        default=None,
    ),
    Option(
        '--foreground',
        action='store_true',
        dest='foreground',
        help='do not daemonize, run in foreground',
        default=False,
    ),
)

parser = OptionParser(usage, option_list=option_list)
(options, args) = parser.parse_args()


if __name__ == '__main__':
    try:
        from setproctitle import setproctitle
        setproctitle('amplify-agent')
    except ImportError:
        pass

    try:
        action = sys.argv[1]
        if action not in ('start', 'stop', 'configtest'):
            print "Invalid action: %s\n" % action
            raise KeyError
    except KeyError:
        parser.print_help()
        sys.exit(1)

    if action == 'configtest':
        from amplify.agent.util import configreader
        rc = configreader.test(options.config, options.pid)
        print ""
        sys.exit(rc)
    else:
        try:
            from amplify.agent.context import context
            context.setup(
                app='agent',
                config_file=options.config,
                pid_file=options.pid
            )
        except:
            import traceback
            print traceback.format_exc()

        try:
            from amplify.agent.supervisor import Supervisor
            supervisor = Supervisor(foreground=options.foreground)

            if not options.foreground:
                from amplify.agent.runner import Runner
                daemon_runner = Runner(supervisor)
                daemon_runner.do_action()
            else:
                supervisor.run()
        except:
            context.default_log.error('failed to run', exc_info=True)
