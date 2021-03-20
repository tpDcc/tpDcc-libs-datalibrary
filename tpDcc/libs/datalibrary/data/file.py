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

    _split = re.compile(r'/|\.|,|-|:|_', re.I)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    @classmethod
    def can_represent(cls, identifier, only_extension=False):
        try:
            if only_extension:
                extension = os.path.splitext(os.path.basename(identifier))[-1]
                if not extension:
                    return False
                return True
            else:
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

    def mandatory_tags(self):

        return os.path.splitext(os.path.basename(self.identifier()))

    def save_schema(self):
        """
        Returns the schema used for saving the item
        :return: dict
        """

        return [
            {
                'name': 'folder',
                'type': 'path',
                'layout': 'vertical',
                'visible': False,
                'errorVisible': True
            },
            {
                'name': 'name',
                'type': 'string',
                'layout': 'vertical',
                'errorVisible': True
            },
            {
                'name': 'comment',
                'type': 'text',
                'layout': 'vertical'
            }
        ]

    def export_schema(self):
        """
        Returns the schema used for exporting the item
        :return: dict
        """

        return [
            {
                'name': 'folder',
                'type': 'path',
                'layout': 'vertical',
                'visible': False,
                'readOnly': True
            },
            {
                'name': 'name',
                'type': 'string',
                'layout': 'vertical',
                'readOnly': True,
            },
            {
                'name': 'comment',
                'type': 'text',
                'layout': 'vertical'
            }
        ]

    def save_validator(self, **kwargs):
        """
        Validates the given save fields
        Called when an input field has changed
        :param kwargs: dict
        :return: list(dict)
        """

        fields = list()

        if not kwargs.get('folder'):
            fields.append({
                'name': 'folder', 'error': 'No folder selected. Please select a target folder.'})
        if not kwargs.get('name'):
            fields.append({'name': 'name', 'error': 'No name specified. Please set a name before saving.'})

        return fields

    def functionality(self):
        return dict(
            directory=self.directory,
            write_lines=self.write_lines,
            open=self.open,
            save=self.save,
            rename=self.rename,
            copy=self.copy,
            move=self.move,
            delete=self.delete,
            delete_with_dependencies=self.delete_with_dependencies
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
        fileio.delete_file(self.format_identifier())
        self._db.remove(self.identifier())

    def delete_with_dependencies(self, recursive=True):
        library = self.library
        if not library:
            self.delete()

        dependencies = library.get_dependencies(self.format_identifier(), as_uuid=False)
        for dependency_identifier in dependencies:
            dependency_item = library.get(dependency_identifier)
            if dependency_item:
                if recursive:
                    delete_function = dependency_item.functionality().get('delete_with_dependencies')
                    if delete_function:
                        delete_function(recursive=recursive)
                        continue
                    else:
                        # Fallback to normal delete if dependencies removal is not supported by data type
                        recursive = False
                if not recursive:
                    delete_function = dependency_item.functionality().get('delete')
                    if delete_function:
                        delete_function()
                        continue
            else:
                self._db.remove(dependency_identifier)

        self.delete()

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
