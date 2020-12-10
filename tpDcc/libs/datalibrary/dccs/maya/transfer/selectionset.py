#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base class to handle data for selection sets
"""

from __future__ import print_function, division, absolute_import

import logging

from tpDcc import dcc
from tpDcc.libs.datalibrary.core import transfer, exceptions
from tpDcc.libs.datalibrary.dccs.maya.core import utils

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class SelectionSet(transfer.TransferObject()):

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def load(self, objects=None, namespaces=None, **kwargs):
        """
        Implements abstract TransferObject function
        Loads/Select the transfer objects to the given objects or namespaces
        :param objects: list(str) or None
        :param namespaces: list(str) or None
        :param kwargs: dict
        """

        valid_nodes = list()
        target_objects = objects
        source_objects = self.objects()

        self.validate(namespace=namespaces)

        matches = utils.match_names(source_objects, target_objects=target_objects, target_namespaces=namespaces)
        for source_node, target_node in matches:
            if '*' in target_node.name():
                valid_nodes.append(target_node.name())
            else:
                target_node.strip_first_pipe()
                try:
                    target_node = target_node.to_short_name()
                except exceptions.NoObjectFoundError as error:
                    LOGGER.debug(error)
                    continue
                except exceptions.MoreThanOneObjectFoundError as error:
                    LOGGER.debug(error)
                    continue

                valid_nodes.append(target_node.name())

        if valid_nodes:

            print(valid_nodes)

            dcc.client().select_node(valid_nodes, **kwargs)
            dcc.client().set_focus('MayaWindow')
        else:
            raise exceptions.NoMatchFoundError('No objects match when loading data.')

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def select(self, objects=None, namespaces=None, **kwargs):
        """
        Selects selection set objects
        :param objects: list(str)
        :param namespaces: list(str)
        :param kwargs: dict
        """

        SelectionSet.load(self, objects=objects, namespaces=namespaces, **kwargs)


def save_selection_set(path, objects, metadata=None):
    """
    Saves a selection set to the given disk location
    :param path: str
    :param objects: list(str)
    :param metadata: dict
    :return: SelectionSet
    """

    selection_set = SelectionSet.from_objects(objects)

    if metadata:
        selection_set.update_metadata(metadata)

    selection_set.save(path)

    return selection_set
