#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains library data item widget implementation
"""

from __future__ import print_function, division, absolute_import

import os
import logging

from Qt.QtCore import Signal

from tpDcc.managers import configs
from tpDcc.libs.python import path as path_utils

from tpDcc.libs.datalibrary.core import item, utils
from tpDcc.libs.datalibrary.core import consts, transfer

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class DataItem(item.BaseItem):

    DATA_TYPE = ''
    EXTENSION = consts.ITEM_DEFAULT_EXTENSION
    EXTENSIONS = list()
    SYNC_ORDER = 10

    ICON_NAME = consts.ITEM_DEFAULT_MENU_ICON
    MENU_ORDER = consts.ITEM_DEFAULT_MENU_ORDER

    ENABLE_DELETE = True
    ENABLE_NESTED_ITEMS = False

    TRANSFER_CLASS = transfer.TransferObject()
    TRANSFER_BASENAME = '.meta'

    dataChanged = Signal(object)
    metaDataChanged = Signal(dict)
    saved = Signal(object)
    saving = Signal(str)
    copied = Signal(object, str, str)
    renamed = Signal(str, str)
    moved = Signal(str, str)
    deleted = Signal(object)
    loaded = Signal(object)

    def __init__(self, path='', data=None, library=None):

        self._library = library
        self._metadata = dict()
        self._cancel_save = False
        self._transfer_object = None

        if path and not self.EXTENSION and not path.endswith(self.EXTENSION):
            path = '{}{}'.format(path, self.EXTENSION)

        super(DataItem, self).__init__(path=path, data=data)

    def __eq__(self, other):
        if not other:
            return False
        if other.name == self.name and other.path == self.path and other.DATA_TYPE == self.DATA_TYPE:
            return True

        return False

    # =================================================================================================================
    # PROPERTIES
    # =================================================================================================================

    @property
    def full_name(self):
        name = self.name
        if self.EXTENSION and not name.endswith(self.EXTENSION):
            name = '{}{}'.format(name, self.EXTENSION)

        return name

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
        name = os.path.splitext(os.path.basename(path))[0]
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

    def transfer_object(self, save=False):

        if not self.TRANSFER_CLASS or not self.TRANSFER_BASENAME:
            return None

        if not self._transfer_object:
            path = self.transfer_path(save=save)
            force_creation = not bool(os.path.isfile(path))
            self._transfer_object = self.TRANSFER_CLASS.from_path(path, force_creation=force_creation)

        return self._transfer_object


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
    # TRANSFER OBJECT
    # ============================================================================================================

    def transfer_path(self, save=False):
        """
        Returns the disk location to transfer path
        :return: str
        """

        # NOTE: Here we use path instead of get_directory because when a transfer file is created the path points
        # to the temporal directory where the transfer file will be created
        if self.TRANSFER_BASENAME and self.TRANSFER_CLASS:
            return os.path.join(self.path if save else self.get_directory(), self.TRANSFER_BASENAME)

        return None

    # ============================================================================================================
    # COPY / RENAME
    # ============================================================================================================

    def copy(self, target, replace=False, sync=False):
        """
        Makes a copy/duplicate the current item to the given destination
        :param target: str
        """

        source = self.path if not self.TRANSFER_BASENAME or not self.TRANSFER_CLASS else self.get_directory()
        target = utils.copy_path(source, target, force=replace)
        if self.library:
            # NOTE: In the library we always path the full path of the file/folder
            self.library.copy_path(self.path, target)

        if self.TRANSFER_BASENAME and self.TRANSFER_CLASS:
            if os.path.isdir(target):
                target_name = '{}{}'.format(os.path.basename(target), self.EXTENSION)
                old_file_path = path_utils.join_path(target, self.full_name)
                new_file_path = path_utils.join_path(target, target_name)
                if old_file_path != new_file_path:
                    utils.rename_path(old_file_path, new_file_path)

        self.copied.emit(self, source, target)

        if sync and self.library:
            self.library.sync(progress_callback=None)

        return target

    def move(self, target, sync=False):
        """
        Moves the current item to the given destination
        :param target: str
        :param sync: bool
        """

        source = self.path if not self.TRANSFER_BASENAME or not self.TRANSFER_CLASS else self.get_directory()

        # TODO: Check tests. This is not valid.
        # if os.path.isdir(source):
        #     target = path_utils.clean_path(os.path.join(target, self.name))

        library = self.library

        extension = self.EXTENSION
        if target and extension and extension not in target:
            target += extension

        source = self.path
        if self.TRANSFER_BASENAME and self.TRANSFER_CLASS:
            target_path = target
            target_no_extension = os.path.splitext(target)[0]
            data_folder = self.get_directory()
            renamed_folder = utils.rename_path(data_folder, target_no_extension)
            if library:
                library.rename_path(data_folder, target_no_extension)
            new_path = path_utils.join_path(renamed_folder, os.path.basename(target_path))
            if os.path.basename(target_path) != os.path.basename(source):
                old_path = path_utils.join_path(renamed_folder, os.path.basename(source))
                target_path = utils.rename_path(old_path, new_path)
            else:
                target_path = new_path
        else:
            target_path = utils.rename_path(source, target)
            if library:
                library.rename_path(source, target_path)

        self.path = target_path

        self.sync_item_data()

        self.moved.emit(source, target_path)

        if sync and self.library:
            self.library.sync(progress_callback=None)

        return target_path

    def rename(self, target, extension=None, sync=False):
        """
        Renames the current path to the give destination path
        :param target: str
        :param extension: bool or None
        :param sync: bool
        """

        library = self.library

        extension = extension or self.EXTENSION
        if target and extension and extension not in target:
            target += extension

        source = self.path
        target_path = utils.rename_path(source, target)
        if library:
            library.rename_path(source, target_path)

        if self.TRANSFER_BASENAME and self.TRANSFER_CLASS:
            target_no_extension = os.path.splitext(target)[0]
            data_folder = self.get_directory()
            renamed_folder = utils.rename_path(data_folder, target_no_extension)
            if library:
                library.rename_path(data_folder, target_no_extension)
            target_path = path_utils.join_path(renamed_folder, os.path.basename(target_path))

        self.path = target_path

        self.sync_item_data()

        self.renamed.emit(source, target_path)

        if sync and self.library:
            self.library.sync(progress_callback=None)

        return target_path

    def delete(self, sync=False):
        """
        Deletes the item from disk and the library model
        """

        source = self.path if not self.TRANSFER_BASENAME or not self.TRANSFER_CLASS else self.get_directory()
        utils.remove_path(source)
        if self.library:
            self.library.remove_path(source)

        self.deleted.emit(self)

        if sync and self.library:
            self.library.sync(progress_callback=None)
