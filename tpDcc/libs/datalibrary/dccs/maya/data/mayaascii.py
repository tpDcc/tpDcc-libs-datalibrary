#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Maya ASCII file item implementation
"""

from __future__ import print_function, division, absolute_import

import logging

from tpDcc import dcc
from tpDcc.libs.datalibrary.dccs.maya.core import dataitem
from tpDcc.libs.datalibrary.dccs.maya.core import transfer

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class MayaAsciiData(dataitem.MayaDataItem):

    EXTENSION = '.ma'

    ICON_NAME = 'maya'
    MENU_NAME = 'Maya ASCII'

    TRANSFER_CLASS = transfer.MayaTransferObject
    TRANSFER_BASENAME = 'mayaascii.json'

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def transfer_path(self):
        """
        Returns the disk location to transfer path
        :return: str
        """

        return self.path + '/{}.json'.format(self._transfer_name())

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
                "name": "name",
                "type": "string",
                "layout": "vertical"
            },
            {
                "name": "objects",
                "type": "objects",
                "layout": "vertical"
            }
        ]

    def load(self, *args, **kwargs):
        """
        Loads the data from the transfer object
        :param args: list
        :param kwargs: dict
        """

        LOGGER.info('Loading: {} | {}'.format(self.path, kwargs))

        # load_path = self.path + '/{}'.format(self.name)
        dcc.client().import_dcc_file(self.path)

        LOGGER.info('Loaded: {} | {}'.format(self.path, kwargs))

    def save(self, thumbnail='', **kwargs):
        """
        Saves all the given data to the item path on disk
        :param thumbnail: str
        :param kwargs: dict
        """

        LOGGER.debug('Saving {} | {}'.format(self.path, kwargs))

        super(MayaAsciiData, self).save(thumbnail=thumbnail, **kwargs)

        item_name = kwargs.get('name', self._transfer_name())
        save_path = self.path + '/{}{}'.format(item_name, self.EXTENSION)

        self.transfer_object.save(self.transfer_path())
        dcc.client().save_dcc_file(save_path)

    def _transfer_name(self):
        """
        Internal function that returns the transfer name that should be used
        :return: str
        """

        return 'mayaascii'
