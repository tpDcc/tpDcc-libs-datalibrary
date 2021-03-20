#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains FBX data part implementation
"""

from __future__ import print_function, division, absolute_import

import os
import re
import logging

from tpDcc import dcc
from tpDcc.core import dcc as core_dcc
from tpDcc.libs.datalibrary.core import consts, datapart

LOGGER = logging.getLogger(consts.LIB_ID)


class FBXData(datapart.DataPart):

    DATA_TYPE = 'dcc.fbx'
    MENU_ICON = 'fbx'
    MENU_NAME = 'FBX'
    PRIORITY = 15
    EXTENSION = '.fbx'

    _has_trait = re.compile(r'\.fbx$', re.I)

    @classmethod
    def can_represent(cls, identifier, only_extension=False):
        if FBXData._has_trait.search(identifier):
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
        return 'fbx'

    def extension(self):
        return '.fbx'

    def type(self):
        return 'dcc.fbx'

    def menu_name(self):
        return 'FBX'

    def functionality(self):
        return dict(
            import_data=self.import_data
        )

    def import_data(self, *args, **kwargs):
        filepath = self.format_identifier()
        if not filepath:
            LOGGER.warning('Impossible to save FBX file because save file path not defined!')
            return

        LOGGER.debug('Saving {} | {}'.format(filepath, kwargs))

        result = dcc.client().import_fbx_file(filepath)

        LOGGER.debug('Saved {} successfully!'.format(filepath))

        return result
