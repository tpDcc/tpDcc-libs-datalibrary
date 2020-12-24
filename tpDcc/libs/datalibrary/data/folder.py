#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains folder data part implementation
"""

from __future__ import print_function, division, absolute_import

import os
import re
from functools import partial

from tpDcc.libs.python import folder

from tpDcc.libs.datalibrary.core import datapart


class FolderData(datapart.DataPart):

    DATA_TYPE = 'folder'
    MENU_ICON = 'folder'
    PRIORITY = 2

    _split = re.compile('/|\.|,|-|:|_', re.I)

    @classmethod
    def can_represent(cls, identifier):
        if os.path.isdir(identifier):
            return True

        return False

    @classmethod
    def menu_name(cls):
        return 'Folder'

    def label(self):
        return os.path.basename(self.identifier())

    def icon(self):
        return 'folder'

    def type(self):
        return 'Folder'

    def mandatory_tags(self):
        tags = [
            part.lower()
            for part in self._split.split(self.identifier())
            if 2 < len(part) < 20
        ]
        return tags

    def functionality(self):
        return dict(
            save=partial(FolderData.save, self.format_identifier())
        )

    @staticmethod
    def save(folder_path):

        if not folder_path or os.path.isdir(folder_path):
            return

        new_folder = folder.create_folder(folder_path)

        return os.path.isdir(new_folder)
