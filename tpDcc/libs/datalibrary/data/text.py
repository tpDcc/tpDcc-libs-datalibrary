#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains text data part implementation
"""

from __future__ import print_function, division, absolute_import

import re
import os
import subprocess

from tpDcc.libs.datalibrary.core import datapart


class TextData(datapart.DataPart):

    DATA_TYPE = 'txt'
    MENU_ICON = 'document'
    PRIORITY = 4

    _has_trait = re.compile('\.txt$', re.I)

    @classmethod
    def can_represent(cls, identifier):
        if TextData._has_trait.search(identifier):
            if os.path.isfile(identifier):
                return True

        return False

    @classmethod
    def menu_name(cls):
        return 'Text File'

    def label(self):
        return os.path.basename(self.identifier())

    def icon(self):
        return 'document'

    def mandatory_tags(self):
        return list()

    def functionality(self):
        return dict(edit=self.edit)

    def edit(self):
        subprocess.Popen(['notepad', self.identifier()])
