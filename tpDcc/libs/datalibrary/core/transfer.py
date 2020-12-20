#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base transfer data item  implementation
"""

from __future__ import print_function, division, absolute_import

import os
import time
import json
import locale
import getpass
import logging

from tpDcc import dcc
from tpDcc.libs.python import python, decorators, fileio
from tpDcc.libs.qt.core import decorators as qt_decorators

from tpDcc.libs.datalibrary.core import utils

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class _MetaBaseTransferObject(type):
    def __call__(self, *args, **kwargs):
        as_class = kwargs.get('as_class', True)
        if dcc.client().is_maya():
            from tpDcc.libs.datalibrary.dccs.maya.core import transfer
            if as_class:
                return transfer.MayaTransferObject
            else:
                return type.__call__(transfer.MayaTransferObject, *args, **kwargs)
        else:
            if as_class:
                return BaseTransferObject
            else:
                return type.__call__(BaseTransferObject, *args, **kwargs)


class BaseTransferObject(object):

    DEFAULT_DATA = {'metadata': dict(), 'objects': dict()}

    def __init__(self):
        self._path = None
        self._data = self.DEFAULT_DATA

    # ============================================================================================================
    # ABSTRACT FUNCTIONS
    # ============================================================================================================

    def load(self, *args, **kwargs):
        """
        Loads transfer object data
        Must be implemented in custom transfer objects
        :param args:
        :param kwargs:
        """

        self.read()

    # ============================================================================================================
    # CLASS METHODS
    # ============================================================================================================

    @classmethod
    def from_path(cls, path, force_creation=False):
        """
        Returns a new transfer instance for the given path
        :param path: str
        :param force_creation: bool
        :return: TransferObject
        """

        t = cls()
        t.set_path(path)

        if not os.path.isfile(path) or force_creation:
            filename = os.path.basename(path)
            filedir = os.path.dirname(path)
            if os.path.isfile(filedir):
                # This happens when we open files not created with library tools
                return t
            else:
                if not os.path.isdir(filedir):
                    os.makedirs(filedir)
            fileio.create_file(filename, filedir)
            utils.save_json(path, cls.DEFAULT_DATA)

        t.read()

        return t

    @classmethod
    def from_objects(cls, objects, **kwargs):
        """
        Returns a new transfer instance for the given objects
        :param objects: list(str)
        :param kwargs: dict
        :return: TransferObject
        """

        t = cls(**kwargs)
        for obj in objects:
            t.add(obj)

        return t

    # ============================================================================================================
    # STATIC FUNCTIONS
    # ============================================================================================================

    @staticmethod
    def read_json(path):
        """
        Reads the given JSON path
        :param path: str
        :return: dict
        """

        with open(path, 'r') as f:
            data = f.read() or '{}'

        data = json.loads(data)

        return data

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def path(self):
        """
        Returns the disk location for the transfer object
        :return: str
        """

        return self._path

    def set_path(self, path):
        """
        Set the disk location for loading and saving the transfer object
        :param path: str
        """

        self._path = path

    def mtime(self):
        """
        Returns the modification datetime of file path
        :return: str
        """

        return os.path.getmtime(self.path())

    def ctime(self):
        """
        Returns the creation datetime of file path
        :return: str
        """

        return os.path.getctime(self.path())

    def data(self):
        """
        Returns all the data for the transfer object
        :return: dict
        """

        return self._data

    def set_data(self, data):
        """
        Sets the data for the transfer object
        :param data: dict
        """

        self._data = data

    def metadata(self):
        """
        Returns the current metadata for the transfer object
         {
            "User": "",
            "Scene": "",
            "Reference": {"filename": "", "namespace": ""},
            "Description": "",
        }
        :return: dict
        """

        return self.data().get('metadata', dict())

    def set_metadata(self, key, value):
        """
        Sets the given key and value in the metadata
        :param key: str
        :param value: int or str or float or dict
        """

        self.data()['metadata'][key] = value

    def update_metadata(self, metadata):
        """
        Updates the given key and value in the metadata
        :param metadata:dict
        """

        self.data()['metadata'].update(metadata)

    def owner(self):
        """
        Returns the user who created this item
        :return: str
        """

        return self.metadata().get('user', '')

    def description(self):
        """
        Returns the description of this item
        :return: str
        """

        return self.metadata().get('description', '')

    def objects(self):
        """
        Returns all the object data
        :return: dict
        """

        return self.data().get('objects', {})

    def object(self, name):
        """
        Returns the data for the given object name
        :param name: str
        :return: dict
        """

        return self.objects().get(name, {})

    def create_object_data(self, name):
        """
        Creates the object data for the given object name
        :param name: str
        :return: dict
        """

        return dict()

    def object_count(self):
        """
        Returns the number of objects in the transfer object
        :return: int
        """

        return len(self.objects() or list())

    def add(self, objects):
        """
        Adds the given objects to the transfer object
        :param objects: str or list(str)
        """

        objects = python.force_list(objects)

        for name in objects:
            self.objects()[name] = self.create_object_data(name)

    def remove(self, objects):
        """
        Removes the given objecst from the transfer object
        :param objects: str or list(str)
        """

        objects = python.force_list(objects)

        for name in objects:
            del self.objects()[name]

    def read(self, path=''):
        """
        Returns the data from the path set on the Transfer Object
        :param path: str
        :return: dict
        """

        data = dict()
        try:
            path = path or self.path()
            data = self.read_json(path)
        except Exception as exc:
            LOGGER.warning('Impossible to read data for transfer object in path: "{}" | {}'.format(path, exc))

        self.set_data(data)

    def data_to_save(self):
        """
        Returns data to save
        Can be override to store custom data
        :return: dict
        """

        encoding = locale.getpreferredencoding()
        user = getpass.getuser()
        if user:
            try:
                user = user.decode(encoding)
            except AttributeError:
                user = str(user)

        ctime = str(time.time()).split('.')[0]

        self.set_metadata('user', user)
        self.set_metadata('ctime', ctime)

        metadata = {'metadata': self.metadata()}
        data = self.dump(metadata)[:-1] + ','

        objects = {'objects': self.objects()}
        data += self.dump(objects)[1:]

        return data

    @qt_decorators.show_wait_cursor
    def save(self, path):
        """
        Saves the current metadata and object data to the given path
        :param path: str
        :return: None
        """

        LOGGER.debug('Saving object: {}'.format(path))

        data = self.data_to_save()

        # Create directory if it does not exists
        dir_name = os.path.dirname(path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        with open(path, 'w') as f:
            f.write(str(data))

        LOGGER.debug('Saved object: {}'.format(path))

    def dump(self, data=None):
        """
        Dumps JSON info
        :param data: str or dict
        """

        if data is None:
            data = self.data()

        return json.dumps(data, indent=2)

    def validate(self, **kwargs):
        """
        Validates the given keyword arguments for the current IO object
        :param kwargs: dict
        """

        return True


@decorators.add_metaclass(_MetaBaseTransferObject)
class TransferObject(object):
    pass
