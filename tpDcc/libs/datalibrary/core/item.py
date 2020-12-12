#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base library data item widget implementation
"""

from __future__ import print_function, division, absolute_import

import os

from Qt.QtCore import Signal, QObject
from Qt.QtWidgets import QApplication

from tpDcc.libs.python import path as path_utils, folder as folder_utils


class BaseItem(QObject):

    SUPPORTED_DCCS = list()

    MENU_NAME = ''
    TYPE_ICON_NAME = ''

    pathChanged = Signal(str)
    dataChanged = Signal(dict)
    pathCopiedToClipboard = Signal()

    def __init__(self, path='', data=None):
        super(BaseItem, self).__init__()

        self._url = None
        self._path = path
        self._data = data or self.create_item_data()

    # =================================================================================================================
    # PROPERTIES
    # =================================================================================================================

    @property
    def name(self):
        return self.data.get('name')

    @name.setter
    def name(self, value):
        new_name = str(value)
        self._data['name'] = new_name
        self._data['icon'] = new_name
        self.dataChanged.emit(self._data)

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = path_utils.clean_path(str(value))
        self.pathChanged.emit(self._path)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value
        self.dataChanged.emit(self._data)

    def create_item_data(self):
        """
        Creates the data dictionary of the current item
        Override in custom items
        :return: dict
        """

        return dict()

    def sync_item_data(self, emit_data_changed=True):
        """
        Syncs the item data to the data located in the data base
        :param emit_data_changed: bool
        Override in custom items
        """

        pass

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def get_directory(self):
        """
        Returns directory of the file path
        :return: str
        """

        return os.path.dirname(self.path)

    def show_in_explorer(self):
        """
        Opens folder in OS folder explorer where file is located
        """

        path = self.path

        if os.path.isdir(path):
            folder_utils.open_folder(path)
        elif os.path.isfile(path):
            folder_utils.open_folder(os.path.dirname(path))

    def copy_path_to_clipboard(self):
        """
        Copies the item path to the system clipboard
        """

        clipboard = QApplication.clipboard()
        clipboard.clear(mode=clipboard.Clipboard)
        clipboard.setText(self.path, mode=clipboard.Clipboard)
        self.pathCopiedToClipboard.emit()
