# -*- coding: utf-8 -*-
import os
import traceback

from util import shell_call, get_version_and_build, change_first_line, install_pip, install_pip_deps

__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev", "Grant Hulegaard"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


def build():
    full_package_name = "nginx-amplify-agent"
    pkg_root = os.path.expanduser('~') + '/agent-pkg-root'
    pkg_final = os.path.expanduser('~') + '/agent-package'

    # get version and build
    version, bld = get_version_and_build()

    # get architecture
    arch = shell_call("dpkg-architecture -c 'echo ${DEB_BUILD_ARCH}'").split('\n')[0]

    # get codename
    shell_call("lsb_release -c")  # checks that lsb_release is installed
    codename = shell_call("lsb_release -c | awk '{print $2}'").split('\n')[0]

    # install pip
    install_pip()

    try:
        # delete previous build
        shell_call('rm -rf %s' % pkg_root)
        shell_call('rm -rf %s && mkdir %s' % (pkg_final, pkg_final))

        # install all dependencies
        install_pip_deps()

        # sed build to control
        shell_call("sed -i 's/^Version: .*$/Version: %s-%s~%s/' packages/deb/DEBIAN/control" % (version, bld, codename))
        shell_call("sed -i 's/^Architecture: .*$/Architecture: %s/' packages/deb/DEBIAN/control" % arch)

        # sed first line of changelog
        changelog_first_line = '%s (%s-%s~%s) unstable; urgency=low' % (full_package_name, version, bld, codename)
        change_first_line('packages/deb/DEBIAN/changelog', changelog_first_line)

        # create python package
        shell_call('python setup.py install --install-layout=deb --prefix=/usr --root=%s' % pkg_root)

        # copy debian files to pkg-root
        shell_call('cp -r packages/deb/DEBIAN %s/' % pkg_root)

        # create deb package
        package_file = '%s_%s-%s~%s_%s.deb' % (full_package_name, version, bld, codename, arch)
        shell_call('fakeroot dpkg --build %s %s/%s' % (pkg_root, pkg_final, package_file))

        # clean
        shell_call('rm -r build', important=False)
        shell_call('rm -r *.egg-*', important=False)
    except:
        print(traceback.format_exc())
