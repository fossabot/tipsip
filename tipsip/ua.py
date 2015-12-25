# -*- coding: utf-8 -*-

import asyncio
from message import Request, Response
from header import AddressHeader, ViaHeader
from uri import URI
from utils import random_string
from dialog import Dialog


def generate_branch():
    return "z9hG4bK" + random_string(7)


class SIPError(Exception):
    def __init__(self, code, reason):
        self.code = code
        self.reason = reason


class SIPUA(object):
    DEFAULT_UDP_PORT = 5060

    def __init__(self, dialog_store, transport, transaction_layer):
        self.dialog_store = dialog_store
        self.transport = transport
        transport.message_callback = self.messageReceived
        self.transaction_layer = transaction_layer
        transaction_layer.requestReceivedCallback = self.requestReceived
        self._pending_requests = {}
        self._pending_finally = {}

    def messageReceived(self, message):
        if type(message) == Request:
            self.transaction_layer.requestReceived(message)
        elif type(message) == Response:
            self.responseReceived(message)
        else:
            raise TypeError("Expected Request or Response")

    async def requestReceived(self, request):
        if not request.isValid():
            raise SIPError("400", "Bad Request")
        try:
            await self.handleRequest(request)
        except SIPError as e:
            self.sendResponse(request.createResponse(e.code, e.reason))
        except:
            self.sendResponse(request.createResponse(500, 'Server Internal Error'))
            raise

    def responseReceived(self, response):
        branch = response.headers['via'][0].params['branch']
        is_finally = response.code >= 200
        if branch in self._pending_requests:
            f = self._pending_requests[branch]
            wait_finally = self._pending_finally[branch]
            if is_finally or not wait_finally:
                f.set_result(response)
                del self._pending_requests[branch]
                del self._pending_finally[branch]

    async def handleRequest(self, request):
        await self._matchDialog(request)
        method = request.method
        print(method)
        handler = getattr(self, "handle_%s" % method, self.handle_DEFAULT)
        await handler(request)

    def handle_DEFAULT(self, request):
        raise SIPError(405, 'Method Not Allowed')

    def sendRequest(self, request, addr=None, wait_finally=True):
        self._createVia(request)
        route = request.headers.get('route')
        if route:
            route = route[0]
            host, port = route.uri.host, route.uri.port
        else:
            host, port = request.ruri.host, request.ruri.port
        if not port:
            port = self.DEFAULT_UDP_PORT
        if request.dialog:
            d = self.dialog_store.incr_lcseq(request.dialog.id)
        f = asyncio.Future()
        branch = request.headers['via'][0].params['branch']
        self._pending_requests[branch] = f
        self._pending_finally[branch] = wait_finally
        self.transport.send_message(request, host, port)
        return f

    def waitResponse(self, request, wait_finally=False):
        f = asyncio.Future()
        self._pending_requests[branch] = f
        self._pending_finally[branch] = wait_finally
        return f

    def sendResponse(self, response):
        via = response.headers['via'][0]
        # XXX: resolv domain name
        host = via.host
        if not via.port:
            port = self.DEFAULT_UDP_PORT
        else:
            port = int(via.port)
        if response.transaction:
            self.transaction_layer.sendResponse(response)
        else:
            self.transport.send_message(response, host, port)

    async def createDialog(self, request):
        d = Dialog()
        r = request
        d.local_tag = r.response_totag
        d.remote_tag = r.headers['from'].params['tag']
        d.callid = r.headers['call-id']
        d.local_cseq = 0
        d.remote_cseq = int(r.headers['cseq'].number)
        d.local_uri = str(r.headers['to'].uri)
        d.remote_uri = str(r.headers['from'].uri)
        ifc = r.from_interface
        d.local_target_uri = ''.join(['sip:', ifc.host, ':', str(ifc.port), ' ;transport=', ifc.transport])
        d.remote_target_uri = str(r.headers['contact'][0].uri)
        if 'record-route' in request.headers:
            rr = request.headers['record-route']
            d.route_set = [str(hdr) for hdr in rr]
        await self.dialog_store.put(d)
        r.dialog = d
        return d

    async def removeDialog(self, dialog=None, id=None):
        if not dialog and not id:
            raise TypeError("dialog or dialog.id required")
        if dialog:
            id = dialog.id
        await self.dialog_store.remove(id)

    def _createVia(self, req):
        h = req.headers
        if 'via' not in h:
            h['via'] = []
        if len(h['via']):
            via = h['via'][0]
        else:
            via = ViaHeader()
            h['via'].append(via)
        via.params['branch'] = generate_branch()

    async def _matchDialog(self, request):
        hdrs = request.headers
        if 'tag' in hdrs['t'].params:
            dialog_id = hdrs['call-id'], hdrs['to'].params['tag'], hdrs['from'].params['tag']
            dialog = await self.dialog_store.get(dialog_id)
            if dialog:
                if hdrs['cseq'].number != dialog.remote_cseq + 1:
                    print("WARNING! Request CSeq (%s) mismatch. Expected %s." % \
                            (hdrs['cseq'].number, dialog.remote_cseq))
                    # Fallback for broken implementations
                    await self.removeDialog(dialog)
                    await self.createDialog(request)
                else:
                    await self.dialog_store.incr_rcseq(dialog.id)
                    request.dialog = dialog

