#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Python script file item implementation
"""

from __future__ import print_function, division, absolute_import

import os
import re

from tpDcc.libs.python import fileio

from tpDcc.libs.datalibrary.core import datapart


class PythonData(datapart.DataPart):

    DATA_TYPE = 'script.python'
    MENU_ICON = 'python'
    MENU_NAME = 'Python Script'
    PRIORITY = 5
    EXTENSION = '.py'

    _has_trait = re.compile(r'\.py$', re.I)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    @classmethod
    def can_represent(cls, identifier, only_extension=False):
        if PythonData._has_trait.search(identifier):
            if only_extension:
                return True
            if os.path.isfile(identifier):
                return True
        return False

    def type(self):
        return 'script.python'

    def icon(self):
        return 'python'

    def label(self):
        return os.path.basename(self.identifier())

    def extension(self):
        return '.py'

    def menu_name(self):
        return 'Python Script'

    def functionality(self):
        return dict(
            save=self.save
        )

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def save(self, **kwargs):

        lines = kwargs.get('lines', None)

        file_path = fileio.create_file(self.format_identifier())
        if not os.path.isfile(file_path):
            return False, 'Was not possible to create Python file'

        lines = lines or ["if __name__ == '__main__':\n\tpass"]

        fileio.write_lines(file_path, lines)

        return True, ''
