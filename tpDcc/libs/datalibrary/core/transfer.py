#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base class to define data transfer objects
"""

import os
import json
import time
import locale
import logging
import getpass

from tpDcc import dcc
from tpDcc.libs.python import python, decorators

from tpDcc.libs.datalibrary.core import consts

logger = logging.getLogger(consts.LIB_ID)


class _MetaDataTransferObject(type):
    def __call__(self, *args, **kwargs):
        as_class = kwargs.get('as_class', True)
        if dcc.is_maya():
            from tpDcc.libs.datalibrary.dccs.maya.core import transfer
            if as_class:
                return transfer.MayaDataTransferObject
            else:
                return type.__call__(transfer.MayaDataTransferObject, *args, **kwargs)
        else:
            if as_class:
                return BaseDataTransferObject
            else:
                return type.__call__(BaseDataTransferObject, *args, **kwargs)


class BaseDataTransferObject(object):

    VERSION = '1.0.0'

    def __init__(self):
        self._path = None
        self._namespaces = None
        self._data = {'metadata': dict(), 'objects': dict()}

    # =================================================================================================================
    # PROPERTIES
    # =================================================================================================================

    @property
    def path(self):
        """
        Returns the disk location for the data transfer object
        :return: str
        """

        return self._path

    @path.setter
    def path(self, value):
        """
        Sets teh disk location for the data transfer object
        :param value: str
        """

        self._path = str(value)

    @property
    def data(self):
        """
        Returns data transfer object data
        :return: dict
        """

        return self._data

    @data.setter
    def data(self, data_dict):
        """
        Sets the data transfer object data
        :param data_dict: dict
        """

        self._data = data_dict

    # =================================================================================================================
    # ABSTRACT FUNCTIONS
    # =================================================================================================================

    @decorators.abstractmethod
    def load(self, *args, **kwargs):
        """
        Loads transfer data object
        :param args:
        :param kwargs:
        :return:
        """

        raise NotImplementedError('Load function for "{}" not implemented'.format(self.__class__.__name__))

    # =================================================================================================================
    # CLASS FUNCTIONS
    # =================================================================================================================

    @classmethod
    def from_path(cls, path):
        """
        Returns a new transfer data object for the given path
        :param path: str
        :return: DataTransferObject
        """

        new_data = cls()
        new_data.path = path
        new_data.parse()

        return new_data

    @classmethod
    def from_objects(cls, objects, **kwargs):
        """
        Returns a new transfer data object from the given objects
        :param objects: list(str)
        :param kwargs:
        :return: DataTransferObject
        """

        new_data = cls(**kwargs)
        new_data.add_objects(objects)

        return new_data

    # =================================================================================================================
    # BASE
    # =================================================================================================================

    def validate(self, **kwargs):
        """
        Validates the given keyword arguments for the current data transfer object
        :param kwargs: dict
        :return: bool
        """

        return True

    def mtime(self):
        """
        Returns the modification datetime of the current data transfer object path
        :return: float
        """

        return os.path.getmtime(self.path)

    def ctime(self):
        """
        Returns the creation datetime of the current data transfer object path
        :return: float
        """

        return os.path.getctime(self.path)

    def metadata(self):
        """
        Returns current data transfer object metadata
        :return: dict
        """

        return self.data.get('metadata', dict())

    def set_metadata(self, key, value):
        """
        Sets current metadata with given metadata key and value
        :param key: str
        :param value: object
        """

        self.data['metadata'][key] = value

    def update_metadata(self, metadata):
        """
        Updates current metadata with given metadata
        :param metadata: dict
        """

        self.data['metadata'].update(metadata)

    def owner(self):
        """
        Returns the user who created this data transfer object path
        :return: str
        """

        return self.metadata().get('user', '')

    def description(self):
        """
        Returns the user description of this transfer object
        :return: str
        """

        return self.metadata().get('description', '')

    def objects(self):
        """
        Returns all the objects data
        :return: dict
        """

        return self.data.get('objects', dict())

    def object_count(self):
        """
        Returns the number of objects in the data transfer object
        :return: int
        """

        return len(self.objects() or list())

    def object(self, name):
        """
        Returns the data for the given object name
        :param name: str
        :return: dict
        """

        return self.objects().get(name, dict())

    def add_objects(self, objects):
        """
        Adds the given objects to the current data transfer object
        :param objects: str or list(str), list of object to add
        """

        objects = python.force_list(objects)
        for name in objects:
            self.objects()[name] = self.parse_object(name)

    def remove_objects(self, objects):
        """
        Removes the given objects from the current data transfer object
        :param objects: str or list(str), list of objects to remove
        """

        objects = python.force_list(objects)
        for name in objects:
            del self.objects()[name]

    def parse_object(self, name):
        """
        Returns the object data for the given object name
        :param name: str
        :return: dict
        """

        return dict()

    def parse(self, path=''):
        """
        Returns the data from data transfer object path
        :param path: str, if given, this path will be used
        :return: dict
        """

        path = path or self.path
        with open(path, 'r') as f:
            data = f.read() or '{}'
        data = json.loads(data)
        self.data = data

        return self.data

    def dump(self, data=None, file_object=None, **kwargs):
        """
        Dumps data into file
        :param data: dict
        :param file_object: Stream or None
        """

        data = data if data is not None else self.data

        indent = kwargs.pop('indent', 2)
        if file_object is None:
            return json.dumps(data, indent=indent, **kwargs)
        else:
            return json.dump(data, file_object, indent=indent, **kwargs)

    def save(self, path=''):
        """
        Saves current data transfer object in given path
        :param path: str
        """

        path = path or self.path

        logger.info('Saving data: {}'.format(path))

        self._set_metadata()
        data = {
            'metadata': self.metadata(),
            'objects': self.objects()
        }

        with open(path, 'w') as json_file:
            self.dump(data, file_object=json_file)

        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        logger.info('Saved data: {}'.format(path))

        return True

    # =================================================================================================================
    # INTERNAL
    # =================================================================================================================

    def _set_metadata(self):
        """
        Internal function that sets the metadata of the data transfer object
        Called before saving the data
        """

        encoding = locale.getpreferredencoding()
        user = getpass.getuser()
        if user:
            user = user.decode(encoding)
        ctime = str(time.time()).split('.')[0]

        self.set_metadata('user', user)
        self.set_metadata('ctime', ctime)
        self.set_metadata('version', self.VERSION)


@decorators.add_metaclass(_MetaDataTransferObject)
class DataTransferObject(object):
    pass
