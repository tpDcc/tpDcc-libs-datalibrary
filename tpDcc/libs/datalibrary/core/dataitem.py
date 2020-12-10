#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains library data item widget implementation
"""

from __future__ import print_function, division, absolute_import

import os
import shutil
import logging

from Qt.QtCore import Signal

from tpDcc.managers import configs
from tpDcc.libs.python import path as path_utils
from tpDcc.libs.qt.core import decorators as qt_decorators

from tpDcc.libs.datalibrary.core import item, utils
from tpDcc.libs.datalibrary.core import consts

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class DataItem(item.BaseItem):

    DATA_TYPE = ''
    EXTENSION = consts.ITEM_DEFAULT_EXTENSION
    EXTENSIONS = list()
    SYNC_ORDER = 10

    ICON_NAME = consts.ITEM_DEFAULT_MENU_ICON
    MENU_ORDER = consts.ITEM_DEFAULT_MENU_ORDER

    ENABLE_DELETE = False
    ENABLE_NESTED_ITEMS = False

    dataChanged = Signal(object)
    metaDataChanged = Signal(dict)
    saved = Signal(object)
    saving = Signal(str)
    copied = Signal(object, str, str)
    renamed = Signal(object, str, str)
    deleted = Signal(object)
    loaded = Signal(object)

    def __init__(self, path='', data=None, library=None):

        self._library = library
        self._metadata = dict()
        self._cancel_save = False

        super(DataItem, self).__init__(path=path, data=data)

    # =================================================================================================================
    # PROPERTIES
    # =================================================================================================================

    @property
    def id(self):
        return self.path

    @property
    def library(self):
        return self._library

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        self._metadata = value
        self.metaDataChanged.emit(self._metadata)

    # =================================================================================================================
    # OVERRIDES
    # =================================================================================================================

    def create_item_data(self):
        """
        Creates the data dictionary of the current item
        :return: dict
        """

        path = self.path
        item_data = dict(self.read_metadata())

        dirname, basename, extension = path_utils.split_path(path)
        name = os.path.basename(path)
        category = os.path.basename(dirname) or dirname

        modified = ''
        if os.path.exists(path):
            modified = os.path.getmtime(path)

        item_data.update({
            'name': name,
            'path': path,
            'type': self.DATA_TYPE or extension,
            'folder': dirname,
            'category': category,
            'modified': modified,
            '__class__': '{}.{}'.format(self.__class__.__module__, self.__class__.__name__)
        })

        return item_data

    def sync_item_data(self, emit_data_changed=True):
        """
        Syncs the item data to the data located in the data base
        :param emit_data_changed: bool
        Override in custom items
        """

        data = self.create_item_data()
        self.data = data

        if self.library:
            self.library.save_item_data([self], emit_data_changed=emit_data_changed)

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    @classmethod
    def match(cls, path):
        """
        Returns whether the given path locations is supported by the item
        :param path: str
        :return: bool
        """

        extensions = cls.EXTENSIONS if cls.EXTENSIONS else [cls.EXTENSION]
        for ext in extensions:
            path_extension = os.path.splitext(path)[-1]
            if path_extension == ext:
                return True

        return False

    @classmethod
    def match_type(cls, data_type):
        """
        Returns whether or not given data type matches with the data type of the data item
        :param data_type: str
        :return: bool
        """

        return data_type == cls.DATA_TYPE

    # =================================================================================================================
    # METADATA
    # =================================================================================================================

    def metadata_path(self):
        """
        Returns item metadata paths
        :return: str
        """

        metadata_path = None
        datalib_config = configs.get_library_config('tpDcc-libs-datalibrary')
        if datalib_config:
            metadata_path = datalib_config.get('metadata_path')
            if metadata_path:
                metadata_path = utils.format_path(metadata_path, self.path)
        if not metadata_path:
            metadata_path = path_utils.join_path(path_utils.get_user_data_dir('dataLibrary'), 'metadata.db')

        return metadata_path

    def read_metadata(self):
        """
        Reads the item metadata from disk
        :return: dict
        """

        if not self._metadata:
            metadata_path = self.metadata_path()
            if os.path.isfile(metadata_path):
                self._metadata = utils.read_json(metadata_path)
            else:
                self._metadata = dict()

        return self._metadata

    def update_metadata(self, metadata):
        """
        Updates the current metadata from disk with the given metadata
        :param metadata: dict
        """

        current_metadata = self.read_metadata()
        current_metadata.update(metadata)
        self.save_metadata(current_metadata)

    def save_metadata(self, metadata):
        """
        Saves the given metadata into disk
        :param metadata: dict
        """

        metadata_path = self.metadata_path()
        if not metadata_path or not os.path.isfile(metadata_path):
            return
        utils.save_json(metadata_path, metadata)
        self._metadata = metadata
        self.sync_item_data(emit_data_changed=False)

    def reset(self):
        """
        Reset data object
        """

        self.__init__()

    # ============================================================================================================
    # LOAD / SAVE
    # ============================================================================================================

    def load(self, *args, **kwargs):
        """
        This function MUST be reimplemented to load any item data
        :param args: list
        :param kwargs: dict
        """

        raise NotImplementedError('load method for {} has not been implemented!'.format(self.__class__.__name__))

    def save(self, *args, **kwargs):
        """
        This function MUST be reimplemented to load any item data
        :param args: list
        :param kwargs: dict
        """

        raise NotImplementedError('save method for {} has not been implemented!'.format(self.__class__.__name__))

    def cancel_safe_save(self):
        self._cancel_save = True

    @qt_decorators.show_wait_cursor
    def safe_save(self, *args, **kwargs):

        target = self.path
        if target and self.EXTENSION and not target.endswith(self.EXTENSION):
            target += self.EXTENSION

        self.path = target
        LOGGER.debug('Saving item: {}'.format(target))
        self.saving.emit(target)

        if self._cancel_save:
            return False

        temp = utils.create_temp_path(self.__class__.__name__)
        self.path = temp
        self.save(*args, **kwargs)
        shutil.move(temp, target)
        self.path = target

        self.sync_item_data()

        LOGGER.debug('Item Saved: {}'.format(target))

        self.item.saved.emit(self)

        return True

    # ============================================================================================================
    # SCHEMA
    # ============================================================================================================

    def save_schema(self):
        """
        Returns the schema used for saving the item
        :return: dict
        """

        return list()

    def load_schema(self):
        """
        Gets the options used to load the item
        :return: list(dict)
        """

        return list()

    def save_validator(self, **fields):
        """
        Validates the given save fields
        Called when an input field has changed
        :param fields: dict
        :return: list(dict)
        """

        return list()

    def load_validator(self, **options):
        """
        Validates the current load options
        Called when the load fields change
        :param options: dict
        :return: list(dict)
        """

        return list()

    # ============================================================================================================
    # COPY / RENAME
    # ============================================================================================================

    def copy(self, target):
        """
        Makes a copy/duplicate the current item to the given destination
        :param target: str
        """

        source = self.path
        target = utils.copy_path(source, target)
        if self.library:
            self.library.copy_path(source, target)
        self.copied.emit(self, source, target)

    def move(self, target):
        """
        Moves the current item to the given destination
        :param target: str
        """

        source = self.path
        if os.path.dirname(source):
            target = os.path.join(target, os.path.basename(source))

        self.rename(target)

    def rename(self, target, extension=None):
        """
        Renames the current path to the give destination path
        :param target: str
        :param extension: bool or None
        """

        library = self.library

        extension = extension or self.EXTENSION
        if target and extension not in target:
            target += extension

        source = self.path
        target = utils.rename_path(source, target)
        if library:
            library.rename_path(source, target)

        self.path = target

        self.sync_item_data()

        self.renamed.emit(self, source, target)

    def delete(self):
        """
        Deletes the item from disk and the library model
        """

        utils.remove_path(self.path)
        if self.library:
            self.library.remove_path(self.path)

        self.deleted.emit(self)
