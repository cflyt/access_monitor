#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Dictionary with auto-expiring values for caching purposes.

Expiration happens on any access, object is locked during cleanup from expired
values. Can not store more than max_len elements - the oldest will be deleted.

>>> ExpiringDict(max_len=100)

The values stored in the following way:
{
    key1: (value1, created_time1),
    key2: (value2, created_time2)
}

NOTE: iteration over dict and also keys() do not remove expired values!
'''

import time
from threading import RLock
import sys

try:
    from collections import OrderedDict
except ImportError:
    # Python < 2.7
    from ordereddict import OrderedDict


class ExpiringDict(OrderedDict):
    def __init__(self, max_len):
        assert max_len >= 1

        OrderedDict.__init__(self)
        self.max_len = max_len
        self.lock = RLock()

        if sys.version_info >= (3, 5):
            self._safe_keys = lambda: list(self.keys())
        else:
            self._safe_keys = self.keys

    def __contains__(self, key):
        """ Return True if the dict has a key, else return False. """
        try:
            with self.lock:
                item = OrderedDict.__getitem__(self, key)
                if time.time() - item[1] < 0:
                    return True
                else:
                    del self[key]
        except KeyError:
            pass
        return False

    def __getitem__(self, key, with_age=False, raw_value=False):
        """ Return the item of the dict.

        Raises a KeyError if key is not in the map.
        """
        with self.lock:
            item = OrderedDict.__getitem__(self, key)
            item_age = item[1] - time.time()
            if item_age > 0:
                if with_age:
                    return item[0], item_age
                elif raw_value:
                    return item
                else:
                    return item[0]
            else:
                del self[key]
                raise KeyError(key)

    def setex(self, key, value, expire_seconds=60):
        """ Set d[key] to value. """
        with self.lock:
            if len(self) == self.max_len:
                try:
                    self.popitem(last=False)
                except KeyError:
                    pass
            try:
                expire = int(expire_seconds)
            except ValueError:
                expire = 60

            OrderedDict.__setitem__(self, key, [value, time.time()+expire])

    def incr(self, key, value):
        with self.lock:
            try:
                item = self.__getitem__(key, raw_value=True)
            except KeyError as e:
                print 'key error', e
                return None

            try:
                item[0] = item[0] + value
            except ValueError as e:
                return None
            return item[0]

    def pop(self, key, default=None):
        """ Get item from the dict and remove it.

        Return default if expired or does not exist. Never raise KeyError.
        """
        with self.lock:
            try:
                item = OrderedDict.__getitem__(self, key)
                del self[key]
                return item[0]
            except KeyError:
                return default

    def ttl(self, key):
        """ Return TTL of the `key` (in seconds).

        Returns None for non-existent or expired keys.
        """
        key_value, key_age = self.get(key, with_age=True)
        if key_age:
            return key_age
        return None

    def get(self, key, default=None, with_age=False):
        " Return the value for key if key is in the dictionary, else default. "
        try:
            return self.__getitem__(key, with_age)
        except KeyError:
            if with_age:
                return default, None
            else:
                return default

    def items(self):
        """ Return a copy of the dictionary's list of (key, value) pairs. """
        r = []
        for key in self._safe_keys():
            try:
                r.append((key, self[key]))
            except KeyError:
                pass
        return r

    def values(self):
        """ Return a copy of the dictionary's list of values.
        See the note for dict.items(). """
        r = []
        for key in self._safe_keys():
            try:
                r.append(self[key])
            except KeyError:
                pass
        return r


