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
import json
import websockets

try:
    import asyncio
except ImportError:
    import trollius as asyncio


class RPCError(Exception):
    pass


class BaseProtocol(object):
    def __init__(self, uri=""):
        if not uri:
            uri = "wss://bitshares.openledger.info/ws"
        self.uri = uri
        self.request_id = 0
        self.history_api = 0
        self.network_api = 0
        self.database_api = 0
        self.result = {}
        self.callbacks = {}

    async def rpc(self, params):
        request_id = self.request_id
        self.request_id += 1
        request = {"id": request_id, "method": "call", "params": params}
        future = self.result[request_id] = asyncio.Future()
        await self.websocket.send(json.dumps(request).encode('utf8'))
        await asyncio.wait_for(future, None)
        self.result.pop(request_id)
        ret = future.result()
        if 'error' in ret:
            if 'detail' in ret['error']:
                raise RPCError(ret['error']['detail'])
            else:
                raise RPCError(ret['error']['message'])
        return ret["result"]

    def subscribe(self, object_id, callback):
        if object_id not in self.callbacks:
            self.callbacks[object_id] = [callback]
        else:
            self.callbacks[object_id].append(callback)

    async def handler_message(self):
        while True:
            payload = await self.websocket.recv()
            self.onMessage(payload)

    async def onOpen(self):
        await self.rpc([1, "login", ["", ""]])
        self.database_api = await self.rpc([1, "database", []])
        self.history_api = await self.rpc([1, "history", []])
        self.network_api = await self.rpc([1, "network_broadcast", []])
        await self.rpc(
            [self.database_api, "set_subscribe_callback", [200, False]])

    async def handler(self):
        # can handle message less than 8M
        async with websockets.connect(
                self.uri, max_size=2**20*8, max_queue=2**5*2) as websocket:
            print("WebSocket connection open.")
            self.websocket = websocket
            task1 = asyncio.ensure_future(self.handler_message())
            task2 = asyncio.ensure_future(self.onOpen())
            await asyncio.wait([task1, task2])

    def onMessage(self, payload):
        res = json.loads(payload)
        if "id" in res and res["id"] in self.result:
            self.result[res["id"]].set_result(res)
        elif "method" in res:
            for notice in res["params"][1][0]:
                if "id" not in notice:
                    # means the object have removed from chain
                    if "removed" in self.callbacks:
                        for _cb in self.callbacks["removed"]:
                            _cb(notice)
                    continue
                for _id in self.callbacks:
                    if _id == notice["id"][:len(_id)]:
                        for _cb in self.callbacks[_id]:
                            _cb(notice)


if __name__ == '__main__':
    import sys
    uri = ""
    if len(sys.argv) >= 2:
        uri = sys.argv[1]

    ws = BaseProtocol(uri)
    asyncio.get_event_loop().run_until_complete(ws.handler())
