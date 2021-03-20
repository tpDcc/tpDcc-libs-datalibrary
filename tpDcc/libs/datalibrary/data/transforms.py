#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains locators (transform) data part implementation
"""

from __future__ import print_function, division, absolute_import

import os
import re
import json
import logging

from tpDcc import dcc
from tpDcc.core import dcc as core_dcc
from tpDcc.libs.datalibrary.core import consts, datapart

LOGGER = logging.getLogger(consts.LIB_ID)


class TransformsData(datapart.DataPart):

    DATA_TYPE = 'dcc.transforms'
    MENU_ICON = 'matrix'
    MENU_NAME = 'Transforms'
    PRIORITY = 15
    EXTENSION = '.xform'

    _has_trait = re.compile(r'\.xform$', re.I)

    @classmethod
    def can_represent(cls, identifier, only_extension=False):
        if TransformsData._has_trait.search(identifier):
            if only_extension:
                return True
            if os.path.isfile(identifier):
                return True

        return False

    @classmethod
    def supported_dccs(cls):
        return [core_dcc.Dccs.Maya, core_dcc.Dccs.Max]

    def label(self):
        return os.path.basename(self.identifier())

    def icon(self):
        return 'matrix'

    def extension(self):
        return '.xform'

    def type(self):
        return 'dcc.transforms'

    def menu_name(self):
        return 'Transforms'

    def functionality(self):
        return dict(
            save=self.save,
            import_data=self.import_data,
            export_data=self.export_data
        )

    def save(self, *args, **kwargs):
        filepath = self.format_identifier()
        if not filepath.endswith(TransformsData.EXTENSION):
            filepath = '{}{}'.format(filepath, TransformsData.EXTENSION)

        if not filepath:
            LOGGER.warning('Impossible to save locators file because save file path not defined!')
            return

        objects = kwargs.get('objects', None)
        if not objects:
            objects = dcc.client().selected_nodes(full_path=True)
        if not objects:
            LOGGER.warning('Select locators to export')
            return False

        valid_nodes = list()
        for object in objects:
            if not dcc.node_is_transform(object):
                LOGGER.warning('Object "{}" is not a transform. Skipping ...'.format(object))
                continue
            valid_nodes.append(object)

        transforms_data = list()

        visited_nodes = dict()
        for i, node in enumerate(valid_nodes):
            node_data = dict()
            node_short_name = dcc.client().node_short_name(node, remove_namespace=True)
            node_data['name'] = node_short_name
            node_data['index'] = i
            node_data['world_matrix'] = dcc.client().node_world_matrix(node)
            visited_nodes[node_short_name] = i
            parent_index = None
            parent_node = dcc.client().node_parent(node)
            if parent_node:
                parent_short_name = dcc.client().node_short_name(parent_node, remove_namespace=True)
                if parent_short_name in visited_nodes:
                    parent_index = visited_nodes[parent_short_name]
            if parent_index is None:
                parent_index = -1
            node_data['parent_index'] = parent_index

            # For now we only store namespaces in Maya
            if dcc.client().is_maya():
                node_namespace = dcc.client().node_namespace(node) or ''
                if node_namespace.startswith('|'):
                    node_namespace = node_namespace[1:]
                node_data['namespace'] = node_namespace

            transforms_data.append(node_data)

        if not transforms_data:
            LOGGER.warning('No transforms data found!')
            return False

        LOGGER.debug('Saving {} | {}'.format(filepath, kwargs))

        try:
            with open(filepath, 'w') as json_file:
                json.dump(transforms_data, json_file, indent=2)
        except IOError:
            LOGGER.error('Transforms data not saved to file {}'.format(filepath))
            return False

        LOGGER.debug('Saved {} successfully!'.format(filepath))

        return True

    def import_data(self, *args, **kwargs):
        filepath = self.format_identifier()
        if not filepath.endswith(TransformsData.EXTENSION):
            filepath = '{}{}'.format(filepath, TransformsData.EXTENSION)

        if not filepath:
            LOGGER.warning('Impossible to load Locators file because save file path not defined!')
            return False

        LOGGER.debug('Loading {} | {}'.format(filepath, kwargs))

        with open(filepath, 'r') as fh:
            transforms_data = json.load(fh)
        if not transforms_data:
            LOGGER.warning('No transforms data found in file: "{}"'.format(filepath))
            return False

        # TODO: Use metadata to verify DCC and also to create nodes with proper up axis
        metadata = self.metadata()

        transform_list = list()
        created_transforms = dict()

        for node_data in transforms_data:
            node_index = node_data.get('index', 0)
            node_parent_index = node_data.get('parent_index', -1)
            node_name = node_data.get('name', 'new_transform')
            node_namespace = node_data.get('namespace', '')
            node_world_matrix = node_data.get(
                'world_matrix', [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0])
            dcc.client().clear_selection()
            new_node = dcc.client().create_locator(name=node_name)
            dcc.client().set_node_world_matrix(new_node, node_world_matrix)
            created_transforms[node_index] = {
                'node': new_node, 'parent_index': node_parent_index, 'namespace': node_namespace
            }
            transform_list.append(new_node)

        for node_index, node_data in created_transforms.items():
            parent_index = node_data['parent_index']
            if parent_index < -1:
                continue
            node_data = created_transforms.get(node_index, None)
            if not node_data:
                continue
            node_name = node_data.get('node')
            parent_node_data = created_transforms.get(parent_index, None)
            if not parent_node_data:
                continue
            parent_node_name = parent_node_data.get('node')
            dcc.client().set_parent(node_name, parent_node_name)

        # We assign namespaces once the hierarchy of nodes is created
        for node_index, node_data in created_transforms.items():
            node_name = node_data.get('node')
            node_namespace = node_data.get('namespace')
            if node_namespace:
                dcc.client().assign_node_namespace(node_name, node_namespace, force_create=True)

        dcc.client().clear_selection()

        LOGGER.debug('Loaded {} successfully!'.format(filepath))

        return transform_list

    def export_data(self, *args, **kwargs):

        filepath = self.format_identifier()
        if not filepath.endswith(TransformsData.EXTENSION):
            filepath = '{}{}'.format(filepath, TransformsData.EXTENSION)

        if not filepath or not os.path.isfile(filepath):
            LOGGER.warning('Impossible to export transforms data to: "{}"'.format(filepath))
            return

        LOGGER.debug('Exporting: {} | {}'.format(filepath, kwargs))

        with open(filepath, 'r') as fh:
            transforms_data = json.load(fh)
        if not transforms_data:
            LOGGER.warning('No transforms data found in file: "{}"'.format(filepath))
            return False

        selected_nodes = dcc.client().selected_nodes(full_path=False)

        saved_nodes = list()
        if not selected_nodes:
            for node_data in transforms_data:
                node_name = node_data.get('name')
                if not node_name:
                    continue
                saved_nodes.append(node_name)
        else:
            for selected_node in selected_nodes:
                if selected_node not in saved_nodes:
                    saved_nodes.append(selected_node)

        valid_nodes = list()
        for selected_node in saved_nodes:
            if not dcc.client().node_exists(selected_node) or not dcc.client().node_is_transform(selected_node):
                continue
            valid_nodes.append(selected_node)

        if not valid_nodes:
            LOGGER.warning('No transforms to export to file found: "{}"'.format(filepath))
            return False

        return self.save(objects=valid_nodes)
