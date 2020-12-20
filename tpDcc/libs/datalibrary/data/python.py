#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Python script file item implementation
"""

from __future__ import print_function, division, absolute_import

import os
import logging

from tpDcc.libs.python import fileio

from tpDcc.libs.datalibrary.core import base, transfer

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class PythonScriptData(base.BaseDataItem):

    EXTENSION = '.py'
    DATA_TYPE = 'script.python'

    ICON_NAME = 'python'
    MENU_NAME = 'Python Script'

    TRANSFER_CLASS = transfer.TransferObject(as_class=True)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

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

        return fields

    def create(self, **kwargs):
        """
        Creates the data file
        :return: str
        """

        file_path = super(PythonScriptData, self).create(**kwargs)
        if not file_path or not os.path.isfile(file_path):
            return

        lines = kwargs.pop('lines', None)
        if not lines:
            return

        fileio.write_lines(file_path, lines, append=True)

        return file_path

    def load(self, *args, **kwargs):
        """
        Loads the data from the transfer object
        :param args: list
        :param kwargs: dict
        """

        LOGGER.debug('Loading: {}'.format(self.path))

        if self.path and os.path.isfile(self.path):
            return fileio.get_file_lines(self.path)

        LOGGER.debug('Loaded: {}'.format(self.path))
