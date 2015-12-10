# -*- coding: utf-8 -*-
import ujson
import time
import requests
import logging
import zlib

from amplify.agent import Singleton
from amplify.agent.context import context

requests.packages.urllib3.disable_warnings()
"""

WHY DO YOU DISABLE THIS WARNING?

We don't want to show you redundant messages.


IS IT A REAL PROBLEM?

No. It is not a real problem.
It's just a notification that urllib3 uses standard Python SSL library.


GIVE ME MORE DETAILS!

By default, urllib3 uses the standard library’s ssl module.
Unfortunately, there are several limitations which are addressed by PyOpenSSL.

In order to work with Python OpenSSL bindings urllib3 needs
requests[security] to be installed, which contains cryptography,
pyopenssl and other modules.

The problem is we CAN'T ship Amplify with built-in OpenSSL & cryptography.
You can install those libs manually and enable warnings back.

More details: https://urllib3.readthedocs.org/en/latest/security.html#pyopenssl

"""


__author__ = "Mike Belov"
__copyright__ = "Copyright (C) 2015, Nginx Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev", "Grant Hulegaard"]
__license__ = ""
__maintainer__ = "Mike Belov"
__email__ = "dedm@nginx.com"


class HTTPClient(Singleton):

    def __init__(self):
        config = context.app_config
        self.timeout = float(config['cloud']['api_timeout'])
        self.verify_ssl = config['cloud']['verify_ssl']
        self.gzip = config['cloud']['gzip']
        self.session = None
        self.url = None

        self.proxies = config.get('proxies')  # Support old configs which don't have 'proxies' section
        if self.proxies is not None and self.proxies['https'] == '':
            self.proxies = None  # Pass None to trigger requests default scraping of environment variables

        self.update_cloud_url()

        logging.getLogger("requests").setLevel(logging.WARNING)

    def update_cloud_url(self):
        config = context.app_config
        self.url = '%s/%s' % (config['cloud']['api_url'], config['credentials']['api_key'])
        content_type = 'binary/octet-stream' if self.gzip else 'application/json'
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': content_type,
            'User-Agent': 'nginx-amplify-agent/%s' % context.version
        })

    def make_request(self, location, method, data=None, timeout=None, json=True, log=True):
        url = location if location.startswith('http') else '%s/%s' % (self.url, location)
        timeout = timeout if timeout is not None else self.timeout
        payload = ujson.encode(data) if data else '{}'
        payload = zlib.compress(payload, self.gzip) if self.gzip else payload

        start_time = time.time()
        result, http_code = None, 200
        try:
            if method == 'get':
                r = self.session.get(
                    url,
                    timeout=timeout,
                    verify=self.verify_ssl,
                    proxies=self.proxies
                )
            else:
                r = self.session.post(
                    url,
                    data=payload,
                    timeout=timeout,
                    verify=self.verify_ssl,
                    proxies=self.proxies
                )
            http_code = r.status_code
            r.raise_for_status()
            result = r.json() if json else r.text
            return result
        except Exception as e:
            if log:
                context.default_log.error('failed to %s "%s", exception: "%s"' % (method, url, e.message))
                context.default_log.debug('', exc_info=True)
                result = {}
                raise e
        finally:
            if log:
                end_time = time.time()
                context.default_log.debug(result)
                context.default_log.info(
                    "%s %s %s %s %s %.3f" % (method, url, http_code, len(payload), len(result), end_time - start_time)
                )

    def post(self, url, data=None, timeout=None, json=True):
        return self.make_request(url, 'post', data=data, timeout=timeout, json=json)

    def get(self, url, timeout=None, json=True, log=True):
        return self.make_request(url, 'get', timeout=timeout, json=json, log=log)
