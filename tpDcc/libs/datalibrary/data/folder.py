#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains folder data part implementation
"""

from __future__ import print_function, division, absolute_import

import os
import re

from tpDcc.libs.python import folder, path as path_utils

from tpDcc.libs.datalibrary.core import datapart


class FolderData(datapart.DataPart):

    DATA_TYPE = 'folder'
    MENU_ICON = 'folder'
    MENU_NAME = 'Folder'
    PRIORITY = 2

    _split = re.compile(r'/|\.|,|-|:|_', re.I)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    @classmethod
    def can_represent(cls, identifier, only_extension=False):
        if only_extension:
            return False
        if os.path.isdir(identifier):
            return True

        return False

    def label(self):
        return os.path.basename(self.identifier())

    def icon(self):
        return 'folder'

    def type(self):
        return 'folder'

    def menu_name(self):
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
            directory=self.directory,
            save=self.save,
            rename=self.rename,
            copy=self.copy,
            move=self.move,
            delete=self.delete
        )

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def directory(self):
        """
        Returns identifier directory
        :return: str
        """

        return path_utils.clean_path(os.path.dirname(self.format_identifier()))

    def save(self, **kwargs):

        new_folder = folder.create_folder(self.format_identifier())

        return os.path.isdir(new_folder)

    def rename(self, new_name):

        current_path = self.format_identifier()

        current_name = os.path.basename(current_path)
        if current_name == new_name:
            return current_path

        new_path = folder.rename_folder(current_path, new_name)
        if new_path == current_path:
            return current_path

        # TODO: Instead of calling sync we should add a specific rename SQL function
        self._db.sync()

        return new_path

    def copy(self, target_path):
        current_path = self.format_identifier()

        if not os.path.isdir(target_path):
            folder.create_folder(target_path)

        folder.copy_directory_contents(current_path, target_path)

        # We force sync after doing copy operation
        self._db.sync()

        return target_path

    def move(self, target_path):
        current_path = self.format_identifier()

        before_identifiers = list()
        folders = folder.get_folders(current_path, recursive=True, full_path=True)
        files = folder.get_files(current_path, recursive=True, full_path=True)
        for file_folder in folders + files:
            before_identifiers.append(file_folder)

        valid = folder.move_folder(current_path, target_path)
        if not valid:
            return None

        self._db.move(current_path, target_path)

        after_identifiers = list()
        folders = folder.get_folders(target_path, recursive=True, full_path=True)
        files = folder.get_files(target_path, recursive=True, full_path=True)
        for file_folder in folders + files:
            after_identifiers.append(file_folder)

        for identifier, new_identifier in zip(before_identifiers, after_identifiers):
            self._db.move(identifier, new_identifier)

        return target_path

    def delete(self):
        folder.delete_folder(self.format_identifier())
        self._db.remove(self.identifier())
