# -*- coding: utf-8 -*-

from collections import defaultdict


class MemoryStorage(object):
    def __init__(self):
        self.htables = {}
        self.sets = defaultdict(set)

    def addCallbackOnConnected(self, *arg, **kw):
        pass

    async def hset(self, table, field, value):
        if table not in self.htables:
            self.htables[table] = {}
        self.htables[table][field] = value

    async def hsetn(self, table, items):
        if table not in self.htables:
            self.htables[table] = {}
        self.htables[table].update(items)

    async def hget(self, table, field):
        try:
            r = self.htables[table][field]
        except KeyError:
            raise KeyError("Table '%s' or field '%s' not found" %
                           (table, field))
        return r

    async def hgetall(self, table):
        try:
            r = self.htables[table].copy()
        except KeyError:
            raise KeyError("Table '%s' not found" % (table,))
        return r

    async def hdel(self, table, field):
        try:
            del self.htables[table][field]
        except KeyError:
            raise KeyError("Table '%s' or field '%s' not found" %
                           (table, field))

    async def hincr(self, table, field, value):
        try:
            self.htables[table][field] += value
        except KeyError:
            raise KeyError("Table '%s' or field '%s' not found" %
                           (table, field))
        return self.htables[table][field]

    async def hdrop(self, table):
        try:
            self.htables.pop(table)
        except KeyError:
            raise KeyError("Table '%s' not found" % table)

    async def sadd(self, s, item):
        self.sets[s].add(item)

    async def saddn(self, s, items):
        self.sets[s].update(items)

    async def srem(self, s, item):
        try:
            self.sets[s].remove(item)
        except KeyError:
            raise KeyError("Set '%s' or item '%s' not found" % (s, item))

    async def sgetall(self, s):
        try:
            r = self.sets[s].copy()
        except KeyError:
            raise KeyError("Set '%s' not found" % (s,))
        return r

    async def sdrop(self, s):
        try:
            self.sets.pop(s)
        except KeyError:
            raise KeyError("Set '%s' not found" % s)
