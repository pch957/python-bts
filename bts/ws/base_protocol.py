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
from autobahn.asyncio.websocket import WebSocketClientProtocol

try:
    import asyncio
except ImportError:
    import trollius as asyncio


class RPCError(Exception):
    pass


class BaseProtocol(WebSocketClientProtocol):
    def __init__(self):
        self.request_id = 0
        self.history_api = 0
        self.network_api = 0
        self.database_api = 0
        self.result = {}
        self.callbacks = {}

    @asyncio.coroutine
    def rpc(self, params):
        request_id = self.request_id
        self.request_id += 1
        request = {"id": request_id, "method": "call", "params": params}
        future = self.result[request_id] = asyncio.Future()
        self.sendMessage(json.dumps(request).encode('utf8'))
        yield from asyncio.wait_for(future, None)
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

    def onConnect(self, response):
        print("Server connected: {0}".format(response.peer))

    @asyncio.coroutine
    def onOpen(self):
        print("WebSocket connection open.")
        yield from self.rpc([1, "login", ["", ""]])
        self.database_api = yield from self.rpc([1, "database", []])
        self.history_api = yield from self.rpc([1, "history", []])
        self.network_api = yield from self.rpc([1, "network_broadcast", []])
        yield from self.rpc(
            [self.database_api, "set_subscribe_callback", [200, False]])

    def onMessage(self, payload, isBinary):
        res = json.loads(payload.decode('utf8'))
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

    def onClose(self, wasClean, code, reason):
        print("WebSocket connection closed: {0}".format(reason))


if __name__ == '__main__':

    from autobahn.asyncio.websocket import WebSocketClientFactory
    factory = WebSocketClientFactory("ws://localhost:4090")
    factory.protocol = BaseProtocol

    loop = asyncio.get_event_loop()
    coro = loop.create_connection(factory, '127.0.0.1', 4090)
    loop.run_until_complete(coro)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
