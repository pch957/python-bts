#!/usr/bin/env python3
###############################################################################
#
# The MIT License (MIT)
#
# Copyright (c) Tavendo GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

# from pprint import pprint
from bts.ws.base_protocol import BaseProtocol

try:
    import asyncio
except ImportError:
    import trollius as asyncio


def id_to_int(id):
    return int(id.split('.')[-1])


class StatisticsProtocol(BaseProtocol):
    account = {"name": "btsbots", "id": "", "statistics": ""}
    last_trx = ""
    last_op = "2.9.1"
    node_api = None

    def init_statistics(node_api, account_name):
        StatisticsProtocol.node_api = node_api
        StatisticsProtocol.account["name"] = account_name

    def process_operations(self, op_id):
        op_info = self.node_api.get_objects([op_id])
        print(op_info)

    def onStatistics(self, notify):
        # TODO: if network is ont sync, return
        trx_last = self.last_trx
        trx_current = notify["most_recent_op"]
        if id_to_int(trx_current) > id_to_int(trx_last):
            self.last_trx = trx_current
        else:
            return
        while True:
            if id_to_int(trx_current) <= id_to_int(trx_last):
                return
            trx_info = self.node_api.get_objects([trx_current])[0]
            if id_to_int(trx_info["operation_id"]) <= id_to_int(self.last_op):
                return
            self.process_operations(trx_info["operation_id"])
            trx_current = trx_info["next"]

    @asyncio.coroutine
    def onOpen(self):
        yield from super().onOpen()
        response = yield from self.rpc(
            [self.database_api, "get_account_by_name", [self.account["name"]]])
        self.account["statistics"] = response["statistics"]
        self.account["id"] = response["id"]
        statistics_info = self.node_api.get_objects(
            [self.account["statistics"]])[0]
        if self.last_trx == "":
            self.last_trx = statistics_info["most_recent_op"]
        print("monitor account %s, begin from trx: %s" % (
            self.account["name"], self.last_trx))
        self.onStatistics(statistics_info)
        self.subscribe(self.account["statistics"], self.onStatistics)


if __name__ == '__main__':

    from autobahn.asyncio.websocket import WebSocketClientFactory
    from bts.http_rpc import HTTPRPC
    factory = WebSocketClientFactory("ws://localhost:4090")
    factory.protocol = StatisticsProtocol
    node_api = HTTPRPC("127.0.0.1", "4090", "", "")
    factory.protocol.init_statistics(
        node_api, "nathan")
    # factory.protocol.last_trx = "2.9.176573"

    loop = asyncio.get_event_loop()
    coro = loop.create_connection(factory, '127.0.0.1', 4090)
    loop.run_until_complete(coro)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
