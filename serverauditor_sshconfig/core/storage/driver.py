# -*- coding: utf-8 -*-
"""Module for low level of application storage.

Driver means "dict converter to stream".
"""
import abc
import os
from collections import OrderedDict

import pickle
import json
import csv
import shutil
import six


@six.add_metaclass(abc.ABCMeta)
class Driver(object):
    """Base class for any storage driver."""

    @abc.abstractmethod
    def dump(self, stream, obj_data):
        """Dump obj_data to stream."""

    @abc.abstractmethod
    def load(self, stream):
        """Load obj_data from stream."""
        stream.seek(0)


class PickleDriver(Driver):
    """Pickle driver for dict."""

    def dump(self, stream, obj_data):
        """Dump obj_data to stream."""
        pickle.dump(dict(obj_data), stream, 2)

    def load(self, stream):
        """Load obj_data from pickle stream."""
        super(PickleDriver, self).load(stream)
        return pickle.load(stream)


class JSONDriver(Driver):
    """JSON driver for dict."""

    def dump(self, stream, obj_data):
        """Dump obj_data to stream."""
        json.dump(obj_data, stream, separators=(',', ':'))

    def load(self, stream):
        """Load obj_data from json stream."""
        super(JSONDriver, self).load(stream)
        return json.load(stream)


class CSVDriver(Driver):
    """CSV driver for dict."""

    def dump(self, stream, obj_data):
        """Dump obj_data to stream."""
        csv.writer(stream).writerows(obj_data.items())

    def load(self, stream):
        """Load obj_data from csv stream."""
        super(CSVDriver, self).load(stream)
        return csv.reader(stream)


DRIVERS = OrderedDict((
    ('pickle', PickleDriver()),
    ('json', JSONDriver()),
    ('csv', CSVDriver()),
))


class PersistentDict(OrderedDict):
    """Persistent dictionary with an API compatible with shelve and anydbm.

    The dict is kept in memory, so the dictionary operations run as fast as
    a regular dictionary.

    Write to disk is delayed until close or sync (similar to gdbm's fast mode).

    Input file format is automatically discovered.
    Output file format is selectable between pickle, json, and csv.
    All three serialization formats are backed by fast C implementations.
    """

    def __init__(self, filename, flag='c', mode=None, _format='json',
                 *args, **kwds):
        """Construct new dict.

        :param str flag: one of ('readonly', 'create', 'new')
        :param mode: file mode for result file,
            None or an octal triple like 0644
        :oaram _format: one of ('csv', 'json', 'pickle')
        """
        self.flag = flag
        self.mode = mode
        self._format = _format
        self.filename = filename
        super(PersistentDict, self).__init__(*args, **kwds)
        if flag != 'n' and os.access(filename, os.R_OK):
            with open(filename, self._read_mode()) as fileobj:
                self.load(fileobj)

    def _write_mode(self):
        return 'wb' if self._format == 'pickle' else 'w'

    def _read_mode(self):
        return 'rb' if self._format == 'pickle' else 'r'

    def sync(self):
        """Write dict to disk."""
        def write_temp_file(filename):
            tempname = filename + '.tmp'
            try:
                with open(tempname, self._write_mode()) as fileobj:
                    self.dump(fileobj)
            except Exception:
                os.remove(tempname)
                raise
            return tempname

        def move_file_and_set_mode(src, dst, dst_mode):
            shutil.move(src, dst)    # atomic commit
            if dst_mode is not None:
                os.chmod(dst, dst_mode)

        if self.flag != 'r':
            tempname = write_temp_file(self.filename)
            move_file_and_set_mode(tempname, self.filename, self.mode)

    def close(self):
        """Close storage."""
        self.sync()

    def __enter__(self):
        """Process entering transaction."""
        return self

    def __exit__(self, *exc_info):
        """Process exiting transaction."""
        self.close()

    def dump(self, fileobj):
        """Write self to fileobj."""
        try:
            DRIVERS[self._format].dump(fileobj, self)
        except KeyError:
            raise NotImplementedError('Unknown format: ' + repr(self._format))

    def load(self, fileobj):
        """Populate self with fileobj content."""
        for loader in DRIVERS.values():
            try:
                return self.update(loader.load(fileobj))
            except Exception:  # pylint: disable=broad-except
                continue
        raise ValueError('File not in a supported format')
