#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains 3ds Max file data part implementation
"""

from __future__ import print_function, division, absolute_import

import os
import re
import logging

from tpDcc import dcc
from tpDcc.core import dcc as core_dcc

from tpDcc.libs.datalibrary.core import consts, datapart

logger = logging.getLogger(consts.LIB_ID)


class MaxFile(datapart.DataPart):

    DATA_TYPE = 'max.file'
    MENU_ICON = 'max'
    MENU_NAME = '3ds Max File'
    PRIORITY = 10
    EXTENSION = '.max'

    _has_trait = re.compile(r'\.max$', re.I)

    @classmethod
    def can_represent(cls, identifier, only_extension=False):
        if MaxFile._has_trait.search(identifier):
            if only_extension:
                return True
            if os.path.isfile(identifier):
                return True

        return False

    @classmethod
    def supported_dccs(cls):
        return [core_dcc.Dccs.Max]

    def label(self):
        return os.path.basename(self.identifier())

    def icon(self):
        return 'max'

    def extension(self):
        return '.max'

    def type(self):
        return 'max.file'

    def menu_name(self):
        return '3ds Max File'

    def functionality(self):
        return dict(
            load=self.load,
            import_data=self.import_data,
            export_data=self.export_data,
            save=self.save
        )

    def load(self):
        """
        Loads 3ds Max file into current 3ds Max scene
        """

        filepath = self.format_identifier()
        if not filepath.endswith(MaxFile.EXTENSION):
            filepath = '{}{}'.format(filepath, MaxFile.EXTENSION)

        if not filepath or not os.path.isfile(filepath):
            logger.warning('Impossible to open 3ds Max file data from: "{}"'.format(filepath))
            return

        return dcc.open_file(filepath)

    def import_data(self):
        """
        Imports 3ds Max file into current 3ds Max scene
        """

        filepath = self.format_identifier()
        if not filepath.endswith(MaxFile.EXTENSION):
            filepath = '{}{}'.format(filepath, MaxFile.EXTENSION)

        if not filepath or not os.path.isfile(filepath):
            return

        return dcc.merge_file(filepath, force=True)

    def export_data(self, *args, **kwargs):
        return self.save(*args, **kwargs)

    def save(self, **kwargs):
        """
        Saes 3ds Max file into current 3ds Max scene
        """

        filepath = self.format_identifier()
        if not filepath.endswith(MaxFile.EXTENSION):
            filepath = '{}{}'.format(filepath, MaxFile.EXTENSION)

        if not filepath:
            logger.warning('Impossible to save 3ds Max file because save file path not defined!')
            return

        logger.debug('Saving {} | {}'.format(filepath, kwargs))

        path_directory = os.path.dirname(filepath)
        file_name = os.path.basename(filepath)
        result = dcc.save_current_scene(path_to_save=path_directory, name_to_save=file_name, force=True)

        logger.debug('Saved {} successfully!'.format(filepath))

        return result
