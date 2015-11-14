# -*- coding: utf-8 -*-
import re

from amplify.agent.util import subp
from amplify.agent.containers.nginx.collectors.meta.common import NginxCommonMetaCollector

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"

class NginxDebianMetaCollector(NginxCommonMetaCollector):
    """
    Redefines package search method
    """

    dpkg_s_re = re.compile('([\w\-\.]+)\s*:\s*(.+)')
    dpkg_l_re = re.compile('([\d\w]+)\s+([\d\w\.\-]+)\s+([\d\w\.\-\+~]+)\s')

    def installed_nginx_packages(self):
        """ trying to find some installed packages """
        result = {}
        dpkg_grep_nginx_out, _ = subp.call("dpkg -l | grep nginx")
        for line in dpkg_grep_nginx_out:
            gwe = re.match(self.dpkg_l_re, line)
            if gwe:
                if gwe.group(2).startswith('nginx'):
                    result[gwe.group(2)] = gwe.group(3)
        return result

    def find_packages(self, meta):
        """
        Find a package with running binary
        """
        package_name = None

        # find which package contains our binary
        dpkg_s_nginx_out, dpkg_s_nginx_err = subp.call('dpkg -S %s' % self.object.bin_path, check=False)
        for line in dpkg_s_nginx_out:
            kv = re.match(self.dpkg_s_re, line)
            if kv:
                package_name = kv.group(1)
                break

        if dpkg_s_nginx_err:
            if 'no_path' in dpkg_s_nginx_err[0]:
                meta['warnings'].append('self-made binary, is not from any nginx package')

        if not package_name:
            return

        # get version
        all_installed_packages = self.installed_nginx_packages()

        if package_name in all_installed_packages:
            meta['packages'] = {package_name: all_installed_packages[package_name]}
