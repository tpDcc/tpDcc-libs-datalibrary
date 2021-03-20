#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains OBJ data part implementation
"""

from __future__ import print_function, division, absolute_import

import os
import re
import logging

from tpDcc import dcc
from tpDcc.core import dcc as core_dcc
from tpDcc.libs.datalibrary.core import consts, datapart

LOGGER = logging.getLogger(consts.LIB_ID)


class OBJData(datapart.DataPart):

    DATA_TYPE = 'dcc.obj'
    MENU_ICON = 'obj'
    MENU_NAME = 'OBJ'
    PRIORITY = 14
    EXTENSION = '.obj'

    _has_trait = re.compile(r'\.obj$', re.I)

    @classmethod
    def can_represent(cls, identifier, only_extension=False):
        if OBJData._has_trait.search(identifier):
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
        return 'obj'

    def extension(self):
        return '.obj'

    def type(self):
        return 'dcc.obj'

    def menu_name(self):
        return 'OBJ'

    def functionality(self):
        return dict(
            import_data=self.import_data
        )

    def import_data(self, *args, **kwargs):
        filepath = self.format_identifier()
        if not filepath.endswith(OBJData.EXTENSION):
            filepath = '{}{}'.format(filepath, OBJData.EXTENSION)

        if not filepath:
            LOGGER.warning('Impossible to save OBJ file because save file path not defined!')
            return

        LOGGER.debug('Saving {} | {}'.format(filepath, kwargs))

        result = dcc.client().import_obj_file(filepath)

        LOGGER.debug('Saved {} successfully!'.format(filepath))

        return result
