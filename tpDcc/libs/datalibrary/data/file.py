#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains file data part implementation
"""

from __future__ import print_function, division, absolute_import

import os
import re

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
        return 'file'

    def icon(cls):
        return 'file'

    def label(self):
        return os.path.basename(self.identifier())

    def functionality(self):
        return dict(
            directory=self.directory,
            write_lines=self.write_lines,
            open=self.open,
            save=self.save,
            rename=self.rename,
            copy=self.copy,
            move=self.move,
            delete=self.delete
        )

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

        return path_utils.clean_path(os.path.dirname(self.format_identifier()))

    def write_lines(self, lines, append=True):
        """
        Writes a list of text lines to a file. Every entry in the list is a new line
        :param lines: list(str), list of text lines in which each entry is a new line
        :param append: bool, Whether to append the text or replace it
        """

        file_path = self.format_identifier()
        if not file_path or not os.path.isfile(file_path):
            return

        return fileio.write_lines(file_path, lines, append=append)

    def open(self):
        file_path = self.format_identifier()
        print('Opening : %s' % file_path)

    def save(self, **kwargs):
        file_path = self.format_identifier()

        fileio.create_file(file_path)

    def delete(self):

        # TODO :Take into account dependencies

        fileio.delete_file(self.format_identifier())
        self._db.remove(self.identifier())

    def rename(self, new_name):

        identifier = self.format_identifier()

        file_directory, file_name, file_extension = path_utils.split_path(identifier)
        if not new_name.endswith(file_extension):
            new_name = '{}{}'.format(new_name, file_extension)
        new_name = fileio.rename_file('{}{}'.format(file_name, file_extension), file_directory, new_name)

        self._db.rename(identifier, new_name)

        return new_name

    def move(self, new_folder):

        if not new_folder or not os.path.isdir(new_folder):
            return

        identifier = self.format_identifier()

        file_directory, file_name, file_extension = path_utils.split_path(identifier)
        new_path = path_utils.join_path(new_folder, '{}{}'.format(file_name, file_extension))

        valid = fileio.move_file(self.format_identifier(), new_path)
        if not valid:
            return

        self._db.move(identifier, new_path)

        return new_path

    def copy(self, target_path, replace=True):

        # TODO :Take into account dependencies

        if not target_path:
            return

        if os.path.isfile(target_path):
            if not replace:
                return
            fileio.delete_file(target_path)

        _, _, file_extension = path_utils.split_path(self.format_identifier())
        target_directory, target_name, target_extension = path_utils.split_path(target_path)
        if target_extension != file_extension:
            target_path = path_utils.join_path(target_directory, '{}{}'.format(target_name, file_extension))

        copy_path = fileio.copy_file(self.format_identifier(), target_path)

        self._db.sync()

        return copy_path
