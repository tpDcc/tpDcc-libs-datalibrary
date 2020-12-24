#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains file data part implementation
"""

from __future__ import print_function, division, absolute_import

import os
import re
from functools import partial

from tpDcc.libs.python import fileio, path as path_utils

from tpDcc.libs.datalibrary.core import datapart


class FileData(datapart.DataPart):

    DATA_TYPE = 'file'
    PRIORITY = 3

    _split = re.compile('/|\.|,|-|:|_', re.I)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    @classmethod
    def can_represent(cls, identifier):
        try:
            if os.path.isfile(identifier):
                return True
        except Exception:
            pass

        return False

    def type(self):
        return 'File'

    def icon(cls):
        return 'file'

    def label(self):
        return os.path.basename(self.identifier())

    def functionality(self):
        return dict(
            open=partial(FileData.open, self.identifier()),
            rename=partial(self.rename),
            move=partial(self.move),
            delete=partial(self.delete)
        )

    # ============================================================================================================
    # STATIC FUNCTIONS
    # ============================================================================================================

    @staticmethod
    def open(filepath):
        print('Opening : %s' % filepath)

    def mandatory_tags(self):

        return os.path.splitext(os.path.basename(self.identifier()))

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def directory(self):
        """
        Returns identifier directory
        :return: str
        """

        return path_utils.clean_path(os.path.dirname(self.identifier()))

    def delete(self):

        # TODO :Take into account dependencies

        fileio.delete_file(self.format_identifier())
        self._db.remove(self.identifier())

    def rename(self, new_name):

        # TODO: Take into account dependencies

        file_directory, file_name, file_extension = path_utils.split_path(self.format_identifier())
        if not new_name.endswith(file_extension):
            new_name = '{}{}'.format(new_name, file_extension)
        fileio.rename_file('{}{}'.format(file_name, file_extension), file_directory, new_name)

        self._db.sync()

    def move(self, new_folder):

        # TODO :Take into account dependencies

        if not new_folder or not os.path.isdir(new_folder):
            return

        file_directory, file_name, file_extension = path_utils.split_path(self.format_identifier())
        new_path = path_utils.join_path(new_folder, '{}{}'.format(file_name, file_extension))

        fileio.move_file(self.format_identifier(), new_path)

        self._db.sync()
