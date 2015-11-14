#!/usr/bin/python
# -*- coding: utf-8 -*-
from builders.util import shell_call

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"

if __name__ == '__main__':
    shell_call('find . -name "*.pyc" -type f -delete', terminal=True)
    shell_call('docker build -t amplify-agent-test docker/test', terminal=True)
    shell_call('docker-compose -f docker/test.yml run test bash', terminal=True)
