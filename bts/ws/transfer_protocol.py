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
    print("[warnning] need python-graphinelib to use transfer protocol")
import datetime

try:
    import asyncio
except ImportError:
    import trollius as asyncio


def id_to_int(id):
    return int(id.split('.')[-1])


class TransferProtocol(StatisticsProtocol):
    prefix = "BTS"
    memo_key = ""
    asset_info = {}

    def init_transfer_monitor(node_api, prefix, account_name, memo_key):
        StatisticsProtocol.init_statistics(node_api, account_name)
        TransferProtocol.prefix = prefix
        TransferProtocol.memo_key = memo_key

    def get_asset_info(self, asset_id):
        if asset_id not in self.asset_info:
            _asset_info = self.node_api.get_objects([asset_id])[0]
            self.asset_info[asset_id] = _asset_info
            self.asset_info[_asset_info["symbol"]] = _asset_info
        return self.asset_info[asset_id]

    def onSent(self, trx):
        print("sent %s" % trx)

    def onReceive(self, trx):
        print("receive %s" % trx)

    def process_operations(self, op_id):
        op_info = self.node_api.get_objects([op_id])
        for operation in op_info[::-1]:
            if operation["op"][0] != 0:
                return
            op = operation["op"][1]
            trx = {}

            # trx["timestamp"] = datetime.datetime.utcnow().strftime(
            #     "%Y%m%d %H:%M")
            trx["block_num"] = operation["block_num"]
            block_info = self.node_api.get_block(trx["block_num"])
            trx["timestamp"] = block_info["timestamp"]
            trx["trx_id"] = operation["id"]
            # Get amount
            asset_info = self.get_asset_info(op["amount"]["asset_id"])
            trx["asset"] = asset_info["symbol"]
            trx["amount"] = float(op["amount"]["amount"])/float(
                10**int(asset_info["precision"]))

            # Get accounts involved
            trx["from_id"] = op["from"]
            trx["to_id"] = op["to"]
            trx["from"] = self.node_api.get_objects([op["from"]])[0]["name"]
            trx["to"] = self.node_api.get_objects([op["to"]])[0]["name"]

            # Decode the memo
            if "memo" in op:
                memo = op["memo"]
                trx["nonce"] = memo["nonce"]
                try:
                    privkey = PrivateKey(self.memo_key)
                    if trx["to_id"] == self.account["id"]:
                        pubkey = PublicKey(memo["from"], prefix=self.prefix)
                    else:
                        pubkey = PublicKey(memo["to"], prefix=self.prefix)
                    trx["memo"] = Memo.decode_memo(
                        privkey, pubkey, memo["nonce"], memo["message"])
                except Exception:
                    trx["memo"] = None
            else:
                trx["nonce"] = None
                trx["memo"] = None

            if trx["from_id"] == self.account["id"]:
                self.onSent(trx)
            elif trx["to_id"] == self.account["id"]:
                self.onReceive(trx)


if __name__ == '__main__':

    from autobahn.asyncio.websocket import WebSocketClientFactory
    from bts.http_rpc import HTTPRPC

    factory = WebSocketClientFactory("ws://localhost:4090")
    factory.protocol = TransferProtocol
    node_api = HTTPRPC("127.0.0.1", "4090", "", "")
    factory.protocol.init_transfer_monitor(
        node_api, "BTS", "nathan",
        "5KQwrPbwdL6PhXujxW37FSSQZ1JiwsST4cqQzDeyXtP79zkvFD3")
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
