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
from bts.ws.statistics_protocol import StatisticsProtocol
try:
    from graphenebase import Memo, PrivateKey, PublicKey
except ImportError:
    print("[warnning] need python-graphinelib to use trade protocol")
import datetime

try:
    import asyncio
except ImportError:
    import trollius as asyncio


def id_to_int(id):
    return int(id.split('.')[-1])


class TradeProtocol(StatisticsProtocol):
    prefix = "BTS"
    asset_info = {}

    def init_trade_monitor(node_api, prefix, account_name):
        StatisticsProtocol.init_statistics(node_api, account_name)
        TradeProtocol.prefix = prefix

    def get_asset_info(self, asset_id):
        if asset_id not in self.asset_info:
            _asset_info = self.node_api.get_objects([asset_id])[0]
            self.asset_info[asset_id] = _asset_info
            self.asset_info[_asset_info["symbol"]] = _asset_info
        return self.asset_info[asset_id]

    def onTrade(self, trx):
        print("sent %s" % trx)

    def process_operations(self, op_id):
        op_info = self.node_api.get_objects([op_id])
        for operation in op_info[::-1]:
            if operation["op"][0] != 4:
                return
            op = operation["op"][1]
            trx = {}

            trx["block_num"] = operation["block_num"]
            block_info = self.node_api.get_block(trx["block_num"])
            trx["timestamp"] = block_info["timestamp"]
            trx["trx_id"] = operation["id"]
            # Get trade info
            for _type in ["pays", "receives", "fee"]:
                trx[_type] = [0, ""]
                asset_info = self.get_asset_info(op[_type]["asset_id"])
                trx[_type][1] = asset_info["symbol"]
                trx[_type][0] = float(op[_type]["amount"])/float(
                        10**int(asset_info["precision"]))

            self.onTrade(trx)


if __name__ == '__main__':

    from autobahn.asyncio.websocket import WebSocketClientFactory
    from bts.http_rpc import HTTPRPC

    factory = WebSocketClientFactory("ws://localhost:4090")
    factory.protocol = TradeProtocol
    node_api = HTTPRPC("127.0.0.1", "4090", "", "")
    factory.protocol.init_trade_monitor(node_api, "BTS", "nathan")
    # factory.protocol.last_trx = "2.9.1"

    loop = asyncio.get_event_loop()
    coro = loop.create_connection(factory, '127.0.0.1', 4090)
    loop.run_until_complete(coro)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
