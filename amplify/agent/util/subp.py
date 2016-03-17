# -*- coding: utf-8 -*-
import subprocess

from amplify.agent.errors import AmplifySubprocessError

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) Nginx, Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


def call(command, check=True):
    """
    Calls subprocess.Popen with the command

    :param command: full shell command
    :param check: check the return code or not
    :return: subprocess stdout [], stderr [] - both as lists
    """
    subprocess_params = dict(
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    process = subprocess.Popen(command, **subprocess_params)
    try:
        process.wait()
        if process.returncode != 0 and check:
            raise AmplifySubprocessError(message=command, payload=dict(returncode=process.returncode))
        else:
            raw_out, raw_err = process.communicate()
            out = raw_out.split('\n')
            err = raw_err.split('\n')
            return out, err
    except:
        raise
    finally:
        process.stdout.close()
        process.stderr.close()
