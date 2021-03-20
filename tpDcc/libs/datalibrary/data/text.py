#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains text data part implementation
"""

from __future__ import print_function, division, absolute_import

import re
import os
import subprocess

from tpDcc.libs.python import fileio

from tpDcc.libs.datalibrary.core import datapart


class TextData(datapart.DataPart):

    DATA_TYPE = 'txt'
    MENU_ICON = 'document'
    MENU_NAME = 'Text File'
    PRIORITY = 4
    EXTENSION = '.txt'

    _has_trait = re.compile(r'\.txt$', re.I)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    @classmethod
    def can_represent(cls, identifier, only_extension=False):
        if TextData._has_trait.search(identifier):
            if only_extension:
                return True
            if os.path.isfile(identifier):
                return True

        return False

    def label(self):
        return os.path.basename(self.identifier())

    def extension(self):
        return '.txt'

    def icon(self):
        return 'document'

    def menu_name(self):
        return 'Text File'

    def mandatory_tags(self):
        return list()

    def functionality(self):
        return dict(
            edit=self.edit,
            save=self.save
        )

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def edit(self):
        subprocess.Popen(['notepad', self.identifier()])

    def save(self):
        file_path = self.format_identifier()

        fileio.create_file(file_path)

        self._db.sync()
