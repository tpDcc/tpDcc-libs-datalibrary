#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Python script file item implementation
"""

from __future__ import print_function, division, absolute_import

import logging

from tpDcc.libs.datalibrary.core import base, transfer

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class PythonScriptData(base.BaseDataItem):

    EXTENSION = '.py'
    DATA_TYPE = 'script.python'

    ICON_NAME = 'python'
    MENU_NAME = 'Python Script'

    TRANSFER_CLASS = transfer.TransferObject(as_class=True)
    TRANSFER_BASENAME = 'pythonscript.json'

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

    def save(self, thumbnail='', **kwargs):
        """
        Saves all the given data to the item path on disk
        :param thumbnail: str
        :param kwargs: dict
        """

        LOGGER.info('Saving {} | {}'.format(self.path, kwargs))

        super(PythonScriptData, self).save(thumbnail=thumbnail, **kwargs)

        self.transfer_object.save(self.transfer_path())

        item_name = kwargs.get('name', self._transfer_name())
        data = scripts.ScriptPythonData(name='{}{}'.format(item_name, self.EXTENSION), path=self.path)
        data.save('')

    def _transfer_name(self):
        """
        Internal function that returns the transfer name that should be used
        :return: str
        """

        return 'pythonscript'


