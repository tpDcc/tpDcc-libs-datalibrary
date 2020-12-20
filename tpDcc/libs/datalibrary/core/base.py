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
from tpDcc.libs.python import fileio, folder, timedate
from tpDcc.libs.qt.core import decorators as qt_decorators

from tpDcc.libs.datalibrary.core import utils, dataitem

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class BaseDataItem(dataitem.DataItem):

    emitError = Signal(str, str)
    loadValueChanged = Signal(object, object)

    def __init__(self, *args, **kwargs):
        super(BaseDataItem, self).__init__(*args, **kwargs)

        self._current_load_values = dict()

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

        count = self.transfer_object().object_count()
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
                "value": self.transfer_object().owner(),
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
                "value": self.transfer_object().description() or "No comment",
            }
        ]

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def cancel_safe_save(self):
        self._cancel_save = True

    @qt_decorators.show_wait_cursor
    def safe_save(self, *args, **kwargs):

        sync = kwargs.pop('sync', False)

        orig_target = self.path
        # if target and self.EXTENSION and not target.endswith(self.EXTENSION):
        #     target += self.EXTENSION

        if orig_target.endswith(self.EXTENSION):
            target = os.path.dirname(self.path)
        else:
            target = orig_target

        LOGGER.debug('Saving item: {}'.format(orig_target))
        self.saving.emit(orig_target)

        if self._cancel_save:
            return False

        temp = utils.create_temp_path(os.path.splitext(os.path.basename(self.path))[0])
        self.path = temp
        self.save(*args, **kwargs)

        if self.TRANSFER_CLASS:
            shutil.move(temp, target)
            target_data = self.library.item_from_path(target)
            target_data.sync_item_data()
        else:
            folder.move_folder(temp, target, only_contents=True)
        self.path = orig_target

        self.sync_item_data()

        LOGGER.debug('Item Saved: {}'.format(orig_target))

        self.saved.emit(self)

        if sync and self.library:
            self.library.sync(progress_callback=None)

        return True

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

    def import_from_current_values(self):
        """
        Loads the values from current selected objects
        """

        kwargs = self._current_load_values

        try:
            self.import_data(**kwargs)
        except Exception as exc:
            LOGGER.error('Item Error: {}'.format(traceback.format_exc()))
            self.emitError.emit('Item Error', str(exc))

    def reference_from_current_values(self):
        """
        Loads the values from current selected objects
        """

        kwargs = self._current_load_values

        try:
            self.reference_data(**kwargs)
        except Exception as exc:
            LOGGER.error('Item Error: {}'.format(traceback.format_exc()))
            self.emitError.emit('Item Error', str(exc))

    def export_from_current_values(self):
        """
        Loads the values from current selected objects
        """

        kwargs = self._current_load_values

        try:
            self.export_data(**kwargs)
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
            self.transfer_object().select(**kwargs)
        except Exception as exc:
            LOGGER.error('Item Error: {}'.format(traceback.format_exc()))
            self.emitError.emit('Item Error', str(exc))

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

        selection = list()
        library = self.library
        if library:
            library_window = library.library_window()
            if library_window:
                selection = library_window.client.selected_nodes(full_path=True) or list()

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

        if self.TRANSFER_CLASS and self.TRANSFER_BASENAME:
            self.transfer_object().load(**kwargs)

    def save(self, thumbnail='', **kwargs):
        """
        Saves all the given data to the item path on disk
        :param thumbnail: str
        :param kwargs: dict
        """

        LOGGER.debug('Saving {} | {}'.format(self.path, kwargs))

        if self.TRANSFER_CLASS and self.TRANSFER_BASENAME:
            self.transfer_object(save=True).save(self.transfer_path(save=True))

        self.create(**kwargs)

        # Copy icon path to the given path
        if thumbnail:
            basename = os.path.basename(thumbnail)
            shutil.copyfile(thumbnail, self.path + '/' + basename)

    def import_data(self, *args, **kwargs):
        """
        Imports data to current DCC
        :param args: list
        :param kwargs: dict
        """

        raise NotImplemented('Data of type "{}" does not support import operation'.format(self.DATA_TYPE))

    def reference_data(self, *args, **kwargs):
        """
        References data to current DCC
        :param args: list
        :param kwargs: dict
        """

        raise NotImplementedError('Data of type "{}" does not support reference operation'.format(self.DATA_TYPE))

    def export_data(self, *args, **kwargs):
        """
        Exports data from current DCC
        :param args: list
        :param kwargs: dict
        """

        raise NotImplementedError('Data of type "{}" does not support export operation'.format(self.DATA_TYPE))

    def write_lines(self, lines, append=True):
        """
        Writes a list of text lines to a file. Every entry in the list is a new line
        :param lines: list<str>, list of text lines in which each entry is a new line
        :param append: bool, Whether to append the text or replace it
        """

        if not self.path or not os.path.isfile(self.path):
            return

        return fileio.write_lines(self.path, lines, append=append)

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
