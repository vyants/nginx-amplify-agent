# -*- coding: utf-8 -*-
from hamcrest import *

from test.base import BaseTestCase
from amplify.agent.util import ssl


__author__ = "Grant Hulegaard"
__copyright__ = "Copyright (C) Nginx, Inc. All rights reserved."
__credits__ = ["Mike Belov", "Andrei Belov", "Ivan Poluyanov", "Oleg Mamontov", "Andrew Alexeev", "Grant Hulegaard"]
__license__ = ""
__maintainer__ = "Grant Hulegaard"
__email__ = "grant.hulegaard@nginx.com"


class SSLAnalysisTestCase(BaseTestCase):
    def test_issuer_with_apostrophe(self):
        result = {}
        line = "issuer= /C=US/O=Let's Encrypt/CN=Let's Encrypt Authority X1"

        for regex in ssl.ssl_regexs:
            match_obj = regex.match(line)
            if match_obj:
                result.update(match_obj.groupdict())

        assert_that(result, has_key('organization'))
        assert_that(result['organization'], equal_to("Let's Encrypt"))
        assert_that(result, has_key('common_name'))
        assert_that(result['common_name'], equal_to("Let's Encrypt Authority X1"))
