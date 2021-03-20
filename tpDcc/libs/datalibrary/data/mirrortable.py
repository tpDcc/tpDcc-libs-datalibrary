#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains locators (transform) data part implementation
"""

from __future__ import print_function, division, absolute_import

import os
import re
import logging

from tpDcc import dcc
from tpDcc.core import dcc as core_dcc
from tpDcc.libs.datalibrary.core import consts, datapart, mirrortable

logger = logging.getLogger(consts.LIB_ID)


class MirrorTableData(datapart.DataPart):

    DATA_TYPE = 'dcc.mirror'
    MENU_ICON = 'mirror'
    MENU_NAME = 'Mirror Table'
    PRIORITY = 17
    EXTENSION = '.mirror'

    _has_trait = re.compile(r'\.mirror$', re.I)

    def __init__(self, *args, **kwargs):
        super(MirrorTableData, self).__init__(*args, **kwargs)

        self._validated_objects = list()

    @classmethod
    def can_represent(cls, identifier, only_extension=False):
        if MirrorTableData._has_trait.search(identifier):
            if only_extension:
                return True
            if os.path.isfile(identifier):
                return True

        return False

    @classmethod
    def supported_dccs(cls):
        return [core_dcc.Dccs.Maya]

    def label(self):
        return os.path.basename(self.identifier())

    def icon(self):
        return 'mirror'

    def extension(self):
        return '.mirror'

    def type(self):
        return 'dcc.mirror'

    def menu_name(self):
        return 'Mirror Table'

    def load_schema(self):

        mirror_table = mirrortable.MirrorTable().from_path(self.format_identifier())

        return [
            {
                'name': 'Left',
                'value': mirror_table.left_side()
            },
            {
                'name': 'Right',
                'value': mirror_table.right_side()
            },
            {
                'name': 'optionsGroup',
                'title': 'Options',
                'type': 'group',
                'order': 2
            },
            {
                'name': 'keysOption',
                'title': 'keys',
                'type': 'radio',
                'value': 'Selected Range',
                'items': ['All Keys', 'Selected Range'],
                'persistent': True
            },
            {
                'name': 'option',
                'type': 'enum',
                'default': 'swap',
                'items': ['swap', 'left to right', 'right to left'],
                'persistent': True
            }
        ]

    def save_schema(self):

        return [
            {
                'name': 'mirrorPlane',
                'type': 'buttonGroup',
                'default': 'YZ',
                'layout': 'vertical',
                'items': ['YZ', 'XY', 'XZ']
            },
            {
                'name': 'leftSide',
                'type': 'string',
                'layout': 'vertical',
                'menu': {'name': '0'}
            },
            {
                'name': 'rightSide',
                'type': 'string',
                'layout': 'vertical',
                'menu': {'name': '0'}
            }
        ]

    def save_validator(self, **kwargs):

        results = list()
        objects = dcc.client().selected_nodes() or list()

        dirty = kwargs.get('fieldChanged') in ['leftSide', 'rightSide']
        dirty = dirty or self._validated_objects != objects
        if dirty:
            self._validated_objects = objects
            left_side = kwargs.get('leftSide', '')
            if not left_side:
                left_side = mirrortable.MirrorTable().find_left_side(objects)
            right_side = kwargs.get('rightSide', '')
            if not right_side:
                right_side = mirrortable.MirrorTable().find_right_side(objects)
            mirror_table = mirrortable.MirrorTable().from_objects([], left_side=left_side, right_side=right_side)
            results.extend([
                {
                    'name': 'leftSide',
                    'value': left_side,
                    'menu': {'name': str(mirror_table.left_count(objects))}
                },
                {
                    'name': 'rightSide',
                    'value': right_side,
                    'menu': {'name': str(mirror_table.right_count(objects))}
                }
            ])

        return results

    def functionality(self):
        return dict(
            save=self.save,
            import_data=self.import_data
        )

    def save(self, *args, **kwargs):
        filepath = self.format_identifier()
        if not filepath:
            logger.warning('Impossible to save Mirror Table file because save file path not defined!')
            return False

        objects = kwargs.get('objects', None)
        if not objects:
            objects = dcc.client().selected_nodes(full_path=True)

        logger.debug('Saving {} | {}'.format(filepath, kwargs))

        mirrortable.save_mirror_table(
            filepath, objects,
            left_side=kwargs.get('leftSide'),
            right_side=kwargs.get('rightSide'),
            mirror_plane=kwargs.get('mirrorPlane')
        )

        logger.debug('Saved {} successfully!'.format(filepath))

        return True

    def import_data(self, *args, **kwargs):
        filepath = self.format_identifier()
        if not filepath or not os.path.isfile(filepath):
            return
            return

        if not filepath:
            logger.warning('Impossible to load pose because save file path not defined!')
            return False

        logger.debug('Loading {} | {}'.format(filepath, kwargs))

        mirror_table = mirrortable.MirrorTable().from_path(self.format_identifier())
        mirror_table.load(
            objects=kwargs.get('objects'), namespaces=kwargs.get('namespaces'),
            option=kwargs.get('option'), keys_option=kwargs.get('keysOption'), time=kwargs.get('time'))

        logger.debug('Loaded {} successfully!'.format(filepath))

        return True
