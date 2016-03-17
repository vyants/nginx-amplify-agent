# -*- coding: utf-8 -*-
import os

from amplify.agent.context import context

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) Nginx, Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"



scale = {'kB': 1024.0, 'mB': 1024.0*1024.0, 'KB': 1024.0, 'MB': 1024.0*1024.0}

def report():
    # get pseudo file  /proc/<pid>/status
    proc_status = '/proc/%d/status' % os.getpid()
    try:
        t = open(proc_status)
        v = t.read()
        t.close()
    except:
        context.log.error('mem', exc_info=True)
        return 0, 0

    # get VmKey line e.g. 'VmRSS:  9999  kB\n ...'
    results = []
    for vm_key in ['VmSize:', 'VmRSS:']:
        i = v.index(vm_key)
        _ = v[i:].split(None, 3)  # whitespace
        if len(_) < 3:
            results.append(0)  # invalid format?
        # convert Vm value to bytes
        results.append(int(float(_[1]) * scale[_[2]] / 1024))

    return results
