#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Maya binary data part implementation
"""

from __future__ import print_function, division, absolute_import

import os
import re

from tpDcc import dcc
from tpDcc.core import dcc as core_dcc
from tpDcc.libs.datalibrary.core import datapart


class MayaBinaryData(datapart.DataPart):

    DATA_TYPE = 'maya.binary'
    MENU_ICON = 'maya'
    MENU_NAME = 'Maya Binary'
    PRIORITY = 10
    EXTENSION = '.mb'

    _has_trait = re.compile(r'\.mb$', re.I)

    @classmethod
    def can_represent(cls, identifier, only_extension=False):
        if MayaBinaryData._has_trait.search(identifier):
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
        return 'maya'

    def extension(self):
        return '.mb'

    def type(self):
        return 'maya.binary'

    def menu_name(self):
        return 'Maya Binary'

    def functionality(self):
        return dict(
            load=self.load,
            save=self.save
        )

    def load(self):
        """
        Opens OS explorer where data is located
        """

        filepath = self.format_identifier()
        if not filepath.endswith(MayaBinaryData.EXTENSION):
            filepath = '{}{}'.format(filepath, MayaBinaryData.EXTENSION)

        if not filepath or not os.path.isfile(filepath):
            return

        dcc.client().open_file(filepath)

    def save(self, **kwargs):
        """
        Opens OS explorer where data is located
        """

        filepath = self.format_identifier()
        if not filepath.endswith(MayaBinaryData.EXTENSION):
            filepath = '{}{}'.format(filepath, MayaBinaryData.EXTENSION)

        if not filepath or os.path.isfile(filepath):
            return

        return dcc.client().save_dcc_file(filepath)
