#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base library item implementation
"""

from __future__ import print_function, division, absolute_import

import os
import shutil
import logging
import traceback

from Qt.QtCore import Signal

from tpDcc import dcc
from tpDcc.libs.python import fileio, timedate

from tpDcc.libs.datalibrary.core import dataitem, transfer

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class BaseDataItem(dataitem.DataItem):

    TRANSFER_CLASS = transfer.TransferObject()
    TRANSFER_BASENAME = 'data.json'

    emitError = Signal(str, str)
    loadValueChanged = Signal(object, object)

    def __init__(self, *args, **kwargs):
        super(BaseDataItem, self).__init__(*args, **kwargs)

        self._transfer_object = None
        self._current_load_values = dict()

    # =================================================================================================================
    # PROPERTIES
    # =================================================================================================================

    @property
    def transfer_object(self):

        if not self._transfer_object:
            path = self.transfer_path()
            force_creation = not bool(os.path.isfile(path))
            self._transfer_object = self.TRANSFER_CLASS.from_path(path, force_creation=force_creation)

        return self._transfer_object

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def save_schema(self):
        """
        Returns the schema used for saving the item
        :return: dict
        """

        return [
            {
                'name': 'folder',
                'type': 'path',
                'layout': 'vertical',
                'visible': False
            },
            {
                'name': 'name',
                'type': 'string',
                'layout': 'vertical'
            },
            {
                'name': 'comment',
                'type': 'text',
                'layout': 'vertical'
            },
            {
                'name': 'objects',
                'type': 'objects',
                'label': {'visible': False}
            }
        ]

    def load_schema(self):
        """
        Gets the options used to load the item
        :return: list(dict)
        """

        modified = self.data.get('modified')
        if modified:
            modified = timedate.time_ago(modified)

        count = self.transfer_object.object_count()
        plural = 's' if count > 1 else ''
        contains = '{} Object{}'.format(count, plural)

        return [
            {
                'name': 'infoGroup',
                'title': 'Info',
                'type': 'group',
                'order': 1
            },
            {
                "name": "name",
                "value": self.name,
            },
            {
                "name": "owner",
                "value": self.transfer_object.owner(),
            },
            {
                "name": "created",
                "value": modified,
            },
            {
                "name": "contains",
                "value": contains,
            },
            {
                "name": "comment",
                "value": self.transfer_object.description() or "No comment",
            }
        ]

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def current_load_value(self, name):
        """
        Returns the current filed value for the given name
        :param name: str
        :return: variant
        """

        return self._current_load_values.get(name)

    def set_current_load_values(self, values):
        """
        Sets the current field values for the item
        :param values: dict
        """

        self._current_load_values = values

    def load_from_current_values(self):
        """
        Loads the values from current selected objects
        """

        kwargs = self._current_load_values
        objects = dcc.client().selected_nodes(full_path=True) or list()

        try:
            self.load(objects=objects, **kwargs)
        except Exception as exc:
            LOGGER.error('Item Error: {}'.format(traceback.format_exc()))
            self.emitError.emit('Item Error', str(exc))

    def select_content(self, **kwargs):
        """
        Select the contents of this item in the current DCC scene
        :param kwargs: dict
        """

        msg = 'Select content: Item.selectContent(kwargs={})'.format(kwargs)
        LOGGER.debug(msg)

        try:
            self.transfer_object.select(**kwargs)
        except Exception as exc:
            LOGGER.error('Item Error: {}'.format(traceback.format_exc()))
            self.emitError.emit('Item Error', str(exc))

    # ============================================================================================================
    # TRANSFER OBJECT
    # ============================================================================================================

    def transfer_path(self):
        """
        Returns the disk location to transfer path
        :return: str
        """

        if self.TRANSFER_BASENAME:
            return os.path.join(self.path, self.TRANSFER_BASENAME)
        else:
            return self.path

    # =================================================================================================================
    # LOAD / SAVE
    # =================================================================================================================

    def save_validator(self, **values):
        """
        Validates the given save fields
        Called when an input field has changed
        :param values: dict
        :return: list(dict)
        """

        fields = list()

        if not values.get('folder'):
            fields.append({
                "name": "folder",
                "error": "No folder selected. Please select a destination folder.",
            })
        if not values.get('name'):
            fields.append({
                "name": "name",
                "error": "No name specified. Please set a name before saving.",
            })

        selection = self.library_window().client.selected_nodes(full_path=True) or list()

        msg = 'No objects selected. Please select at least one object.' if not selection else ''

        fields.append({
            "name": "objects",
            "value": selection,
            "error": msg
        })

        return fields

    def create(self, **kwargs):
        """
        Creates the data file
        :return: str
        """

        item_name = kwargs.get('name', self.name)
        if not item_name.endswith(self.EXTENSION):
            item_name = '{}{}'.format(item_name, self.EXTENSION)
        return fileio.create_file(filename=item_name, directory=self.path)

    def load(self, *args, **kwargs):
        """
        Loads the data from the transfer object
        :param args: list
        :param kwargs: dict
        """

        LOGGER.debug('Loading: {}'.format(self.transfer_path()))
        self.transfer_object.load(**kwargs)
        LOGGER.debug('Loaded: {}'.format(self.transfer_path()))

    def save(self, thumbnail='', **kwargs):
        """
        Saves all the given data to the item path on disk
        :param thumbnail: str
        :param kwargs: dict
        """

        LOGGER.debug('Saving {} | {}'.format(self.path, kwargs))

        self.transfer_object.save(self.transfer_path())
        self.create(**kwargs)

        # Copy icon path to the given path
        if thumbnail:
            basename = os.path.basename(thumbnail)
            shutil.copyfile(thumbnail, self.path + '/' + basename)

    def write_lines(self, lines, append=True):
        """
        Writes a list of text lines to a file. Every entry in the list is a new line
        :param lines: list<str>, list of text lines in which each entry is a new line
        :param append: bool, Whether to append the text or replace it
        """

        if not self.full_path or not os.path.isfile(self.full_path):
            return

        return fileio.write_lines(self.full_path, lines, append=append)

    # ============================================================================================================
    # INTERNAL
    # ============================================================================================================

    def _emit_load_value_changed(self, field, value):
        """
        Internal function that emits the load value changed to be validated
        :param field: str
        :param value: object
        """

        self.loadValueChanged.emit(field, value)
