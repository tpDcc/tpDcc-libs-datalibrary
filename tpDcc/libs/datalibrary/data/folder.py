#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains library folder item data implementation
"""

from __future__ import print_function, division, absolute_import

import os
import logging

from Qt.QtCore import QLocale, QFileInfo

from tpDcc.libs.python import folder as folder_utils

from tpDcc.libs.datalibrary.core import dataitem

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class FolderData(dataitem.DataItem):

    DATA_TYPE = 'folder'
    SYNC_ORDER = 100        # Last item to run when syncing

    ICON_NAME = 'folder'
    MENU_NAME = 'Folder'
    MENU_ORDER = 0          # First menu item
    TYPE_ICON_NAME = ''     # Do not show a type icon for folder items

    ENABLE_NESTED_ITEMS = True
    ENABLE_DELETE = True

    DEFAULT_ICON_COLOR = 'rgb(150, 150, 150, 100)'
    DEFAULT_ICON_COLORS = [
        "rgb(239, 112, 99)",
        "rgb(239, 207, 103)",
        "rgb(136, 200, 101)",
        "rgb(111, 183, 239)",
        "rgb(199, 142, 220)",
        DEFAULT_ICON_COLOR
    ]

    TRANSFER_BASENAME = None
    TRANSFER_CLASS = None

    # ============================================================================================================
    # PROPERTIES
    # ============================================================================================================

    @property
    def icon_color(self):
        """
        Returns the icon color for the folder item
        :return: str
        """

        return self.data.get('color', '')

    @icon_color.setter
    def icon_color(self, color_string):
        """
        Sets the icon color for the folder item
        :param color_string: str
        """

        if color_string == self.DEFAULT_COLOR_ICON:
            color_string = ''

        self.update_metadata({'color': color_string})

    @property
    def custom_icon_path(self):
        """
        Returns the custom icon path of the folder item
        :return: str
        """

        return self.data.get('icon', '')

    @custom_icon_path.setter
    def custom_icon_path(self, icon_name):
        """
        Sets the custom icon of the folder item
        :param icon_name: str
        """

        if icon_name == self.ICON_NAME:
            return

        self.update_metadata({'icon': icon_name})

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    @dataitem.DataItem.data.getter
    def data(self):
        data = dataitem.DataItem.data.fget(self)

        # If not icon is defined and the item is in trash, we update the icon
        if self.path.endswith('Trash') and not data.get('icon'):
            data['icon'] = 'trash.png'

        return data

    @classmethod
    def match(cls, path):
        """
        Returns whether the given path locations is supported by the item
        :param path: str
        :return: bool
        """

        if os.path.isdir(path):
            return True

    def save(self, *args, **kwargs):
        """
        This function MUST be reimplemented to load any item data
        Override to avoid not implemented exception
        :param args: list
        :param kwargs: dict
        """

        sync = kwargs.pop('sync', False)

        LOGGER.debug('Saving item: {}'.format(self.path))

        # NOTE: for folders, path variable contains the full directory name, so we pass  the dirname of that path
        new_folder = folder_utils.create_folder(self.name, os.path.dirname(self.path))

        self.sync_item_data()

        LOGGER.debug('Item Saved: {}'.format(self.path))

        self.saved.emit(self)

        if sync and self.library:
            self.library.sync(progress_callback=None)

        return os.path.isdir(new_folder)

    def load_schema(self):
        """
        Gets the options used to load the item
        :return: list(dict)
        """

        file_info = QFileInfo(self.path)
        created = QLocale().toString(file_info.created(), QLocale.ShortFormat)
        modified = QLocale().toString(file_info.lastModified(), QLocale.ShortFormat)
        icon_name = self.data.get('icon', '')

        return [
            {
                'name': 'infoGroup',
                'title': 'Info',
                'value': True,
                'type': 'group',
                'persistent': True,
                'persistentKey': 'BaseItem'
            },
            {
                'name': 'name',
                'value': self.name
            },
            {
                'name': 'path',
                'value': self.path
            },
            {
                'name': 'created',
                'value': created
            },
            {
                'name': 'modified',
                'value': modified
            },
            {
                'name': 'color',
                'type': 'color',
                'value': self.icon_color(),
                'layout': 'vertical',
                'label': {'visible': False},
                'colors': self.DEFAULT_ICON_COLORS
            },
            {
                'name': 'icon',
                'type': 'iconPicker',
                'value': icon_name,
                'layout': 'vertical',
                'label': {'visible': False}
            }
        ]

    def load_validator(self, **options):
        """
        Validates the current load options
        :param options: dict
        :return: list(dict)
        """

        if options.get('fieldChanged') == 'color':
            self.set_icon_color(options.get('color'))

        if options.get('fieldChanged') == 'icon':
            self.set_custom_icon(options.get('icon'))
