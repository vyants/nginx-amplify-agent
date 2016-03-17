#!/usr/bin/python
# -*- coding: utf-8 -*-
from optparse import OptionParser, Option

from builders.util import shell_call

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) Nginx, Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"

usage = "usage: %prog -h"

option_list = (
    Option(
        '--plus',
        action='store_true',
        dest='plus',
        help='Run with nginx+ (false by default)',
        default=False,
    ),
)

parser = OptionParser(usage, option_list=option_list)
(options, args) = parser.parse_args()

if __name__ == '__main__':
    if options.plus:
        yml, image, path = 'docker/test-plus.yml', 'amplify-agent-test-plus', 'docker/test-plus'
    else:
        yml, image, path = 'docker/test.yml', 'amplify-agent-test', 'docker/test'

    shell_call('find . -name "*.pyc" -type f -delete', terminal=True)
    shell_call('docker build -t %s %s' % (image, path), terminal=True)
    shell_call('docker-compose -f %s run test bash' % yml, terminal=True)
