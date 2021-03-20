#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains curve data part implementation
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


class MayaCurveData(datapart.DataPart):

    DATA_TYPE = 'maya.curve'
    MENU_ICON = 'circle'
    MENU_NAME = 'Curve'
    PRIORITY = 11
    EXTENSION = '.curve'

    _has_trait = re.compile(r'\.curve$', re.I)

    @classmethod
    def can_represent(cls, identifier, only_extension=False):
        if MayaCurveData._has_trait.search(identifier):
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
        return 'circle'

    def extension(self):
        return '.curve'

    def type(self):
        return 'maya.curve'

    def menu_name(self):
        return 'Curve'

    def save_schema(self):
        """
        Returns the schema used for saving the item
        :return: dict
        """

        return [
            {
                'name': 'objects',
                'type': 'objects',
                'layout': 'vertical',
                'errorVisible': True
            },
            {
                'name': 'world_space',
                'type': 'bool',
                'layout': 'vertical',
                'errorVisible': False
            }
        ]

    def functionality(self):
        return dict(
            import_data=self.import_data,
            export_data=self.export_data,
            save=self.save,
        )

    def save(self, **kwargs):
        filepath = self.format_identifier()
        if not filepath.endswith(MayaCurveData.EXTENSION):
            filepath = '{}{}'.format(filepath, MayaCurveData.EXTENSION)

        if not filepath:
            LOGGER.warning('Impossible to save curve data file because save file path not defined!')
            return

        objects = kwargs.get('objects', None)
        if not objects:
            objects = dcc.client().selected_nodes(full_path=True)
        if not objects:
            LOGGER.warning(
                'Nothing selected to export curve data of. Please, select a curve to export')
            return False

        LOGGER.debug('Saving {} | {}'.format(filepath, kwargs))

        valid_nodes = list()

        for obj in objects:
            if dcc.client().node_is_a_shape(obj):
                obj = dcc.client().node_parent(obj, full_path=True)
            if not dcc.client().node_is_curve(obj):
                continue
            valid_nodes.append(obj)

        if not valid_nodes:
            LOGGER.warning('Curve data export failed! No curves to export found!')
            return False

        world_space = kwargs.pop('world_space', False)
        curve_data = dict()

        for curve in objects:
            curve_degree = dcc.client().get_curve_degree(curve)
            curve_form = dcc.client().get_curve_form(curve)

            # We need to do this because we return the form using maya.cmds but we expect to use
            # it using OpenMaya, and the form index in OpenMaya starts with 1 instead of 0
            curve_form += 1

            curve_knots = dcc.client().get_curve_knots(curve)
            curve_cvs = dcc.client().get_curve_cvs(curve, world_space=world_space)

            curve_data[curve] = {
                'degree': curve_degree,
                'form': curve_form,
                'knots': curve_knots,
                'cvs': curve_cvs,
                '2d': False,
                'rational': True
            }
        if not curve_data:
            LOGGER.warning('Curve data export failed! No curve data found for given curves!')
            return False

        with open(filepath, 'w') as fh:
            json.dump(curve_data, fh)

        LOGGER.debug('Saved {} successfully!'.format(filepath))

        return True

    def import_data(self, *args, **kwargs):
        filepath = self.format_identifier()
        if not filepath.endswith(MayaCurveData.EXTENSION):
            filepath = '{}{}'.format(filepath, MayaCurveData.EXTENSION)

        if not filepath:
            LOGGER.warning('Impossible to load Maya Curves from file: "{}"!'.format(filepath))
            return False

        with open(filepath, 'r') as fh:
            curves_data = json.load(fh)
        if not curves_data:
            LOGGER.warning('No curves data found in file: "{}"'.format(filepath))
            return False

        created_curves = list()

        for curve_name, curve_data in curves_data.items():
            new_curve = dcc.client().create_curve(curve_name, **curve_data)
            created_curves.append(new_curve)

        return created_curves

    def export_data(self, *args, **kwargs):
        pass
