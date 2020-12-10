#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base item factory implementation
"""

from __future__ import print_function, division, absolute_import

from tpDcc import dcc
from tpDcc.libs.python import decorators

from tpDcc.libs.datalibrary.core.views import base
from tpDcc.libs.datalibrary.data import folder
from tpDcc.libs.datalibrary.data.views import folder as folder_view


class _MetaItemsFactory(type):

    def __call__(self, *args, **kwargs):
        if dcc.client().is_maya():
            from tpDcc.libs.datalibrary.dccs.maya.core import factory
            return type.__call__(factory.MayaItemsFactory, *args, **kwargs)
        else:
            return type.__call__(BaseItemsFactory, *args, **kwargs)


class BaseItemsFactory(object):

    def create_item(self, item_class, path, data, library):

        return item_class(path=path, library=library, data=data)

    def create_view(self, item_class, path, data, library):

        new_item = self.create_item(item_class, path, data, library)
        if not new_item:
            return None

        return self.create_view_from_item(new_item)

    def create_view_from_item(self, item):

        library_window = item.library.library_window()
        view_item_class = self.get_view_class_from_item(item)

        return view_item_class(data_item=item, library_window=library_window)

    def get_view_class_from_item_class(self, item_class):
        if item_class == folder.FolderData:
            item_view_class = folder_view.FolderItemView
        else:
            item_view_class = base.BaseDataItemView

        return item_view_class

    def get_view_class_from_item(self, item):
        if isinstance(item, folder.FolderData):
            item_view_class = folder_view.FolderItemView
        else:
            item_view_class = base.BaseDataItemView

        return item_view_class


@decorators.add_metaclass(_MetaItemsFactory)
class ItemsFactory(object):
    pass
