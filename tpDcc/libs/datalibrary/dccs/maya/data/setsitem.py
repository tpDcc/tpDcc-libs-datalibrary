#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Maya sets item implementation
"""

from __future__ import print_function, division, absolute_import

from tpDcc.libs.datalibrary.dccs.maya.core import dataitem
from tpDcc.libs.datalibrary.dccs.maya.transfer import selectionset


class SetsItem(dataitem.MayaDataItem):

    EXTENSION = '.set'

    ICON_NAME = 'selection_set'
    MENU_NAME = 'Selection Set'

    TRANSFER_CLASS = selectionset.SelectionSet
    TRANSFER_BASENAME = 'set.json'

    def load(self, namespaces=None):
        """
        Loads the selection using the settings for this item
        :param namespaces: list(str)
        """

        self.select_content(namespaces=namespaces)

    def save(self, objects, **kwargs):
        """
        Saves all the given objects data to the item path on disk
        :param objects: list(str)
        :param kwargs: dict
        """

        super(SetsItem, self).save(**kwargs)

        selectionset.save_selection_set(
            self.path() + '/set.json', objects=objects, metadata={'description': kwargs.get('comment', '')})


def save(path, *args, **kwargs):
    """
    Saves data as SetItem
    :param path: str
    :param args: list
    :param kwargs: dict
    """

    SetsItem(path).safe_save(*args, **kwargs)


def load(path, *args, **kwargs):
    """
    Loads data item
    :param path: str
    :param args: list
    :param kwargs: dict
    """

    SetsItem(path).load(*args, **kwargs)
