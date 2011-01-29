# -*- coding: utf-8 -*-

from uri import URI
from utils import random_string

# http://www.iana.org/assignments/sip-parameters
name_to_compact = {
        'accept-contact': 'a',
        'allow-events': 'u',
        'call-id':  'i',
        'contact':  'm',
        'content-encoding': 'e',
        'content-length':   'l',
        'content-type': 'c',
        'event':    'o',
        'from': 'f',
        'identity': 'y',
        'identify-info':    'n',
        'refer-to': 'r',
        'referred-by':  'b',
        'reject-contact':   'j',
        'request-disposition':  'd',
        'session-expires':  'x',
        'subject':  's',
        'supported':    'k',
        'to':   't',
        'via':  'v',
        }
compact_to_name = dict(zip(name_to_compact.values(), name_to_compact.keys()))

top_headers = (
        'via',
        'route',
        'record-route',
        'proxy-require',
        'max-forwards',
        'proxy-authorization',
        'to',
        'from',
        'contact'
        )

request_mandatory_headers = (
        'to',
        'from',
        'cseq',
        'call-id',
        'max-forwards',
        'via'
        )

address_headers = (
        'to',
        'from',
        'contact',
        'reply-to',
        'record-route',
        'route')

multi_headers = (
        'accept',
        'accept-encoding',
        'accept-language',
        'alert-info',
        'allow',
        'call-info',
        'contact',
        'content-encoding',
        'content-language',
        'error-info',
        'in-reply-to',
        'proxy-require',
        'record-route',
        'require',
        'route',
        'supported',
        'unsupported',
        'via',
        'warning'
        )

exceptions_normal_form = {
        'www-authenticate': 'WWW-Authenticate',
        'cseq': 'CSeq',
        'call-id': 'Call-ID',
        'mime-version': 'MIME-Version',
        'sip-etag': 'SIP-ETag'
        }


def name2intern(name):
    return compact_to_name.get(name.lower(), name.lower())

def name2norm(name):
    n = name2intern(name)
    if n in exceptions_normal_form:
        return exceptions_normal_form[n]
    return '-'.join(x.capitalize() for x in n.split('-'))

def name2compact(name):
    n = name2intern(name)
    if n in name_to_compact:
        return name_to_compact[n]
    return name2norm(name)

def generate_tag():
    return random_string(7)


class Header(object):
    def __init__(self, value, params=None):
        self.value = value
        self.params = params or {}

    def __str__(self):
        r = []
        r.append(self.value)
        p = self._renderParams()
        if p:
            r.append(';' + p)
        return ' '.join(r)

    def _renderParams(self):
        r = []
        for k, v in self.params.items():
            if v is None:
                r.append(k)
            else:
                r.append(k + '=' + v)
        return ';'.join(r)

    @staticmethod
    def _parse_params(s):
        params = {}
        for p in s.split(';'):
            if '=' in p:
                k, v = p.split('=')
                v = v.strip()
            else:
                k = p
                v = None
            k = k.strip().lower()
            params[k] = v
        return params


class AddressHeader(Header):
    def __init__(self, display_name=None, uri=None, params=None):
        self.display_name = display_name
        self.uri = uri
        self.params = params or {}

    def __str__(self):
        # XXX: check '?', ';' and ',' in uri
        if self.display_name is None:
            return self._renderAddrSpec()
        else:
            return self._renderNameAddr()

    def __repr__(self):
        return "<AddressHeader display_name=%r, uri=%r, params=%r>" % \
                (self.display_name, self.uri, self.params)

    def _renderAddrSpec(self):
        r = []
        r.append(str(self.uri))
        params = self._renderParams()
        if params:
            r.append(';' + params)
        return ' '.join(r)

    def _renderNameAddr(self):
        r = []
        if self.display_name:
            r.append(self.display_name)
        r.append('<' + str(self.uri) + '>')
        params = self._renderParams()
        if params:
            r.append(';' + params)
        return ' '.join(r)

    @classmethod
    def parse(cls, s):
        display_name, uri, rest = cls._parse_nameaddr(s)
        if rest:
            params = cls._parse_params(rest)
        else:
            params = None
        uri = URI.parse(uri)
        return cls(display_name, uri, params)

    @staticmethod
    def _parse_nameaddr(s):
        # XXX: handle quoted chars
        if '<' not in s:
            dn = None
            if ';' in s:
                uri, rest = s.split(';', 1)
            else:
                uri = s
                rest = None
        else:
            dn, rest = s.split('<')
            dn = dn.strip()
            uri, rest = rest.split('>')
            if ';' in rest:
                _, rest = rest.split(';')
                rest = rest.strip()
        uri = uri.strip()
        return dn, uri, rest


class CSeqHeader(Header):
    def __init__(self, number, method):
        self.number = number
        self.method = method

    def __str__(self):
        return ' '.join([str(self.number), self.method])

    @classmethod
    def parse(cls, s):
        r = s.split()
        if len(r) != 2:
            raise ValueError("Bad CSeq header: " + s)
        number = int(r[0])
        method = r[1]
        return cls(number, method)


class ViaHeader(Header):
    version = 'SIP/2.0'

    def __init__(self, transport=None, host=None, port=None, params=None, version='SIP/2.0'):
        self.transport = transport
        self.host = host
        self.port = port
        self.params = params or {}

    def __repr__(self):
        return "<Via transport=%r, host=%r, port=%r, params=%r>" % \
                (self.transport, self.host, self.port, self.params)

    def __str__(self):
        r = []
        r.append(self.version + '/' + self.transport)
        addr = self.host
        if self.port:
            addr += ':' + str(self.port)
        r.append(addr)
        p = self._renderParams()
        if p:
            r.append(';' + p)
        return ' '.join(r)

    @classmethod
    def parse(cls, s):
        version, transport, rest = cls._parse_proto(s)
        host, port, rest = cls._parse_hostport(rest)
        if rest:
            params = cls._parse_params(rest)
        return cls(version=version, transport=transport, host=host, port=port, params=params)

    @property
    def sent_by(self):
        r = self.host
        if self.port:
            r += ':' + self.port
        return r

    @staticmethod
    def _parse_proto(s):
        sent_by, rest = s.split(None, 1)
        version, transport = sent_by.rsplit('/', 1)
        return version, transport, rest

    @staticmethod
    def _parse_hostport(s):
        if ';' in s:
            s, rest = s.split(';', 1)
        else:
            rest = None
        s = s.strip()
        if ':' in s:
            host, port = s.split(':')
            port = port.strip()
        else:
            host = s
            port = None
        host = host.strip()
        return host, port, rest


class Headers(dict):
    compact = False

    def __init__(self, *arg, **kw):
        dict.__init__(self)
        self.update(*arg, **kw)

    def __setitem__(self, key, value):
        k = name2intern(key)
        dict.__setitem__(self, k, value)

    def __getitem__(self, key):
        k = name2intern(key)
        return dict.__getitem__(self, k)

    def __delitem__(self, key):
        k = name2intern(key)
        dict.__delitem__(self, k)

    def __contains__(self, key):
        k = name2intern(key)
        return dict.__contains__(self, k)

    def __str__(self):
        if self.compact:
            f = name2compact
        else:
            f = name2norm
        r = []
        for k, v in self.items():
            k = f(k)
            if isinstance(v, list) or isinstance(v, tuple):
                for item in v:
                    r.append('%s: %s' % (k, item))
            else:
                r.append('%s: %s' % (k, v))
        return '\r\n'.join(r)

    def get(self, key, d=None):
        k = name2intern(key)
        return dict.get(self, k, d)

    def update(self, *arg, **kw):
        for k, v in dict(*arg, **kw).iteritems():
            self[k] = v

    def has_key(self, key):
        k = name2intern(key)
        return dict.has_key(self, k)

    def pop(self, key, d=None):
        k = name2intern(key)
        return dict.pop(self, k)

    @classmethod
    def parse(cls, s):
        # XXX: this function bad and does not scale :)
        headers = cls()
        if not s:
            return headers
        for h in cls._iter_headers(s):
            name, hdr = h.split(':', 1)
            name = name2intern(name.strip())
            if name in multi_headers:
                hdrs = hdr.split(',')
            else:
                hdrs = [hdr]
            for hdr in hdrs:
                hdr = hdr.strip()
                if name == 'contact':
                    if hdr != '*':
                        hdr = AddressHeader.parse(hdr)
                    else:
                        headers[name] = '*'
                        continue
                elif name == 'cseq':
                    hdr = CSeqHeader.parse(hdr)
                elif name in address_headers:
                    hdr = AddressHeader.parse(hdr)
                elif name == 'via':
                    hdr = ViaHeader.parse(hdr)
                if name in multi_headers:
                    if name not in headers:
                        headers[name] = []
                    headers[name].append(hdr)
                else:
                    headers[name] = hdr
        return headers

    @staticmethod
    def _iter_headers(s):
        r = ''
        for hdr in s.split('\r\n'):
            if hdr[0].isspace():
                r += hdr
            else:
                if r:
                    yield r
                r = hdr
        if r:
            yield r

