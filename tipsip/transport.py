# -*- coding: utf-8 -*-

from collections import namedtuple

from message import Message


Address = namedtuple('Address', ('host', 'port', 'transport'))


def debug(msg):
    return
    print(msg)


class UDPTransport:
    def __init__(self):
        self.message_callback = lambda x: None

    def connection_made(self, transport):
        self.transport = transport
        self.listen_interface = Address('127.0.0.1', '9090', transport)

    def datagram_received(self, data, addr):
        host, port = addr
        data = data.decode()
        if not data.strip():
            return
        debug("[UDP] received message from %s:%s:\n%s" % (host, port, data))
        msg = Message.parse(data)
        msg.received = Address(host, port, "UDP")
        msg.from_interface = self.listen_interface
        self.message_callback(msg)

    def send_message(self, message, host, port):
        # XXX: do it for requests only
        self._fillVia(message)
        data = str(message).encode()
        debug("[UDP] sent message to %s:%s:\n%s" % (host, port, data))
        self.transport.sendto(data, (host, port))

    def _fillVia(self, msg):
        via = msg.headers['via'][0]
        if via.transport:
            return
        via.transport = 'UDP'
        via.host = self.listen_interface.host
        via.port = self.listen_interface.port
