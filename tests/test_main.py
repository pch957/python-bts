# -*- coding: utf-8 -*-
# from pytest import raises

# The parametrize function is generated, so this doesn't work:
#
#     from pytest.mark import parametrize
#
import pytest
parametrize = pytest.mark.parametrize
from bts import HTTPRPC
from pprint import pprint


class TestMain(object):
    logfile = open("/tmp/test-python-bts.log", 'a')
    host = "localhost"
    node_port = "4090"
    cli_port = "4092"
    cli_rpc = HTTPRPC(host, cli_port, "", "")

    def test_cli_rpc(self):
        pprint("======= test_cli_rpc =========", self.logfile)
        result = self.cli_rpc.about()
        pprint(result, self.logfile)
        result = self.cli_rpc.get_dynamic_global_properties()
        pprint(result, self.logfile)
        assert result["head_block_number"] > 0
