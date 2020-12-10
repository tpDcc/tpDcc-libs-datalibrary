#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base item factory implementation for Maya
"""

from __future__ import print_function, division, absolute_import

from tpDcc.libs.datalibrary.core import factory
from tpDcc.libs.datalibrary.dccs.maya.data import mayaascii, mayabinary


class MayaItemsFactory(factory.BaseItemsFactory):

    pass

    # def get_view_class_from_item_class(self, item_class):
    #     if item_class == mayaascii.MayaAsciiData:
    #         item_view_class = folder_view.FolderItemView
    #     else:
    #         item_view_class = base.BaseDataItemView
    #
    #     return item_view_class
    #
    # def get_view_class_from_item(self, item):
    #     if isinstance(item, folder.FolderData):
    #         item_view_class = folder_view.FolderItemView
    #     else:
    #         item_view_class = base.BaseDataItemView
    #
    #     return item_view_class

    # def create_view_from_view_class(self, view_class, library, path=''):
    #
    #     item = None
    #
    #     if view_class == mayaascii.MayaAsciiFileItemView:
    #         item = mayaascii.MayaAsciiFileItem(path=path, library=library)
    #     elif view_class == mayabinary.MayaBinaryFileItemView:
    #         item = mayabinary.MayaBinaryFileItem(path=path, library=library)
    #
    #     if item:
    #         item_view = self.create_view_from_item(item=item)
    #         return item_view
    #
    #     return super(MayaItemsFactory, self).create_view_from_view_class(view_class, library, path)
