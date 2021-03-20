#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains pose data part implementation
"""

from __future__ import print_function, division, absolute_import

import os
import re
import logging
import traceback

from tpDcc import dcc
from tpDcc.core import dcc as core_dcc
from tpDcc.libs.datalibrary.core import consts, datapart

logger = logging.getLogger(consts.LIB_ID)


class PoseData(datapart.DataPart):

    DATA_TYPE = 'maya.pose'
    MENU_ICON = 'pose'
    MENU_NAME = 'Pose'
    PRIORITY = 16
    EXTENSION = '.pose'

    _has_trait = re.compile(r'\.pose$', re.I)

    @classmethod
    def can_represent(cls, identifier, only_extension=False):
        if PoseData._has_trait.search(identifier):
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
        return 'pose'

    def extension(self):
        return '.pose'

    def type(self):
        return 'maya.pose'

    def menu_name(self):
        return 'Pose'

    def functionality(self):
        return dict(
            save=self.save,
            import_data=self.import_data
        )

    def save(self, *args, **kwargs):
        from tpDcc.libs.datalibrary.dccs.maya.core import pose

        filepath = self.format_identifier()
        if not filepath.endswith(PoseData.EXTENSION):
            filepath = '{}{}'.format(filepath, PoseData.EXTENSION)

        if not filepath:
            logger.warning('Impossible to save pose file because save file path not defined!')
            return

        objects = kwargs.get('objects', None)
        if not objects:
            objects = dcc.client().selected_nodes(full_path=True)
        if not objects:
            logger.warning('Select objects to export pose from')
            return False

        logger.debug('Saving {} | {}'.format(filepath, kwargs))

        new_pose = pose.Pose.from_objects(objects=objects)
        try:
            new_pose.save(filepath)
        except IOError:
            logger.error('Pose data not saved to file {}'.format(filepath))
            return False

        logger.debug('Saved {} successfully!'.format(filepath))

        return True

    def import_data(self, *args, **kwargs):
        from tpDcc.libs.datalibrary.dccs.maya.core import pose

        filepath = self.format_identifier()
        if not filepath.endswith(PoseData.EXTENSION):
            filepath = '{}{}'.format(filepath, PoseData.EXTENSION)

        if not filepath:
            logger.warning('Impossible to save pose file because save file path not defined!')
            return False

        try:
            kwargs['clear_cache'] = True
            loaded_pose = pose.load_pose(filepath, *args, **kwargs)
        except Exception:
            logger.error('Error while loading pose data "{}" | "{}"'.format(filepath, traceback.format_exc()))
            return False

        logger.debug('Loading {} | {}'.format(filepath, kwargs))

        return loaded_pose
