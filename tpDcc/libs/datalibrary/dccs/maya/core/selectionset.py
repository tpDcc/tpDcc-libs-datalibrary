#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module function that contains util class to handle selection set data information
"""

from __future__ import print_function, division, absolute_import

import logging

from tpDcc import dcc

from tpDcc.libs.datalibrary.core import consts, exceptions
from tpDcc.libs.datalibrary.dccs.maya.core import utils, transfer

logger = logging.getLogger(consts.LIB_ID)


def save_selection_set(path, objects, metadata=None):
    """
    Function that saves a selection set to disk
    :param path: str
    :param objects: list(str)
    :param metadata: dikct or None
    :return: SelectionSet
    """

    selection_set = SelectionSet.from_objects(objects)
    if metadata:
        selection_set.update_metadata(metadata)
    selection_set.save(path)

    return selection_set


class SelectionSet(transfer.MayaDataTransferObject):

    def load(self, *args, **kwargs):

        objects = kwargs.get('objects', None)
        namespaces = kwargs.get('namespaces', None)

        valid_nodes = list()
        target_objects = objects
        source_objects = self.objects()

        self.validate(namespaces=namespaces)

        matches = utils.match_names(source_objects, target_objects=target_objects, target_namespaces=namespaces)
        for source_node, target_node in matches:
            if '*' in target_node.name():
                valid_nodes.append(target_node.name())
            else:
                target_node.strip_first_pipe()
                try:
                    target_node = target_node.to_short_name()
                except exceptions.NoObjectFoundError as exc:
                    logger.warning(exc)
                    continue
                except exceptions.MoreThanOneObjectFoundError as exc:
                    logger.warning(exc)
                valid_nodes.append(target_node.name())

        if valid_nodes:
            dcc.select_node(valid_nodes, **kwargs)
            dcc.focus_ui_panel('MayaWindow')
        else:
            raise exceptions.NoMatchFoundError('No objects match when loading selection set data')

    def select(self, objects=None, namespaces=None, **kwargs):
        """
        :param objects:
        :param namespaces:
        :param kwargs:
        :return:
        """

        SelectionSet.load(self, objects=objects, namespaces=namespaces, **kwargs)
