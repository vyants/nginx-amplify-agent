%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}

# distribution specific definitions
%define use_systemd (0%{?fedora} && 0%{?fedora} >= 18) || (0%{?rhel} && 0%{?rhel} >= 7) || (0%{?suse_version} == 1315)

%define nginx_home %{_localstatedir}/cache/nginx
%define nginx_user nginx
%define nginx_group nginx

Summary: NGINX Amplify Agent
Name: nginx-amplify-agent
Version: %{amplify_version}
Release: %{amplify_release}%{?dist}
Vendor: Nginx Software, Inc.
URL: https://amplify.nginx.com/
Packager: Nginx Software, Inc. <https://www.nginx.com>
License: 2-clause BSD-like license
Group: System Environment/Daemons


Source0:   nginx-amplify-agent-%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

BuildRequires:  python-devel
%if 0%{?fedora} && 0%{?fedora} <= 12
BuildRequires:  python-setuptools-devel
%else
BuildRequires:  python-setuptools
%endif

Requires: python >= 2.6
Requires: initscripts >= 8.36
Requires(post): chkconfig


%description
This package contains code used for collecting
and reporting a number of metrics, configs, logs and events
from NGINX and/or NGINX Plus instances to NGINX Amplify



%prep
%setup -q -n nginx-amplify-agent-%{version}
cp -p %{SOURCE0} .


%build
%{__python} -c 'import setuptools; execfile("setup.py")' build


%pre
# Add the "nginx" user
getent group %{nginx_group} >/dev/null || groupadd -r %{nginx_group}
getent passwd %{nginx_user} >/dev/null || \
    useradd -r -g %{nginx_group} -s /sbin/nologin \
    -d %{nginx_home} -c "nginx user"  %{nginx_user}
exit 0



%install
%define python_libexec /usr/bin/
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}
%{__python} -c 'import setuptools; execfile("setup.py")' install -O1 --skip-build --install-scripts %{python_libexec} --root %{buildroot}
mkdir -p %{buildroot}/var/
mkdir -p %{buildroot}/var/log/
mkdir -p %{buildroot}/var/log/amplify-agent/
mkdir -p %{buildroot}/var/
mkdir -p %{buildroot}/var/run/
mkdir -p %{buildroot}/var/run/amplify-agent/


%clean
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}


%files
%define config_files /etc/amplify-agent/
%defattr(-,root,root,-)
%{python_sitelib}/*
%{python_libexec}/*
%{config_files}/*
%attr(0755,nginx,nginx) %dir /var/log/amplify-agent
%attr(0755,nginx,nginx) %dir /var/run/amplify-agent
/etc/init.d/amplify-agent
/etc/logrotate.d/amplify-agent




%post
if [ $1 -eq 1 ] ; then
%if %{use_systemd}
    /usr/bin/systemctl preset amplify-agent.service >/dev/null 2>&1 ||:
%else
    /sbin/chkconfig --add amplify-agent
%endif
    mkdir -p /var/run/amplify-agent
    touch /var/log/amplify-agent/agent.log
    chown nginx /var/run/amplify-agent /var/log/amplify-agent/agent.log
elif [ $1 -eq 2 ] ; then
    # Check for an older version of the agent running
    if command -V pgrep > /dev/null 2>&1; then
        agent_pid=`pgrep amplify-agent`
    else
        agent_pid=`ps aux | grep -i '[a]mplify-agent' | awk '{print $2}'`
    fi

    # stop it
    if [ -n "$agent_pid" ]; then
        service amplify-agent stop > /dev/null 2>&1 < /dev/null
    fi

    # Change API URL from 1.0 to 1.1
    sh -c "sed -i.old 's/api_url.*$/api_url = https:\/\/receiver.amplify.nginx.com:443\/1.1/' \
        /etc/amplify-agent/agent.conf"

    # start it
    service amplify-agent start > /dev/null 2>&1 < /dev/null
fi

%preun
if [ $1 -eq 0 ]; then
%if %use_systemd
    /usr/bin/systemctl --no-reload disable amplify-agent.service >/dev/null 2>&1 ||:
    /usr/bin/systemctl stop amplify-agent.service >/dev/null 2>&1 ||:
%else
    /sbin/service amplify-agent stop > /dev/null 2>&1
    /sbin/chkconfig --del amplify-agent
%endif
fi



%changelog
* Thu Dec 17 2015 Mike Belov <dedm@nginx.com> 0.27-1
- 0.27-1
- Bug fixes

* Wed Dec 3 2015 Mike Belov <dedm@nginx.com> 0.25-1
- 0.25-1
- Bug fixes
- New metric: system.cpu.stolen
- Nginx config parsing improved

* Tue Nov 24 2015 Mike Belov <dedm@nginx.com> 0.24-2
- 0.24-2
- Bug fixes

* Tue Nov 24 2015 Mike Belov <dedm@nginx.com> 0.24-1
- 0.24-1
- Bug fixes

* Wed Nov 18 2015 Mike Belov <dedm@nginx.com> 0.23-1
- 0.23-1
- Bug fixes
- Ubuntu Wily support

* Sun Nov 15 2015 Mike Belov <dedm@nginx.com> 0.22-5
- 0.22-5
- Bug fixes

* Fri Nov 13 2015 Mike Belov <dedm@nginx.com> 0.22-4
- 0.22-4
- Bug fixes

* Thu Nov 12 2015 Mike Belov <dedm@nginx.com> 0.22-3
- 0.22-3
- Bug fixes

* Wed Nov 11 2015 Mike Belov <dedm@nginx.com> 0.22-2
- 0.22-2
- Bug fixes

* Mon Nov 09 2015 Mike Belov <dedm@nginx.com> 0.22-1
- 0.22-1
- Bug fixes

* Thu Nov 05 2015 Mike Belov <dedm@nginx.com> 0.21-3
- 0.21-3
- Additional events added

* Wed Nov 04 2015 Mike Belov <dedm@nginx.com> 0.21-2
- 0.21-2
- Bug fixes

* Mon Nov 02 2015 Mike Belov <dedm@nginx.com> 0.21-1
- 0.21-1
- Bug fixes

* Wed Oct 28 2015 Mike Belov <dedm@nginx.com> 0.20-1
- 0.20-1
- RPM support
