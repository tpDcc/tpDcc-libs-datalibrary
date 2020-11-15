#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains script data definitions for DCCs
"""

from __future__ import print_function, division, absolute_import


from tpDcc.libs.datalibrary.core import data
from tpDcc.libs.python import path, fileio


class ScriptTypes(object):
    """
    Class that defines different script types supported by DCCs
    """

    Unknown = 'Unknown'
    Python = 'script.python'
    Manifest = 'script.manifest'


class ScriptExtensions(object):
    """
    Class that defines different script extensions supported by DCCs
    """

    Python = 'py'
    Manifest = 'json'


class ScriptData(data.FileData, object):
    """
    Class used to define scripts stored in disk files
    """

    def save(self, lines, comment=None):
        file_path = path.join_path(self.directory, self._get_file_name())
        write_file = fileio.FileWriter(file_path=file_path)
        write_file.write(lines, last_line_empty=False)

        version = fileio.FileVersion(file_path=file_path)
        version.save(comment=comment)

    def set_lines(self, lines):
        self.lines = lines

    def create(self):
        super(ScriptData, self).create()

        file_name = self.get_file()
        if not hasattr(self, 'lines'):
            return

        if self.lines and file_name:
            write = fileio.FileWriter(file_path=file_name)
            write.write(self.lines)


class ScriptManifestData(ScriptData, object):
    """
    Class used to define manifest scripts stored in disk files
    """

    @staticmethod
    def get_data_type():
        return ScriptTypes.Manifest
        # return constants.ScriptLanguages.Manifest

    @staticmethod
    def get_data_extension():
        return ScriptExtensions.Manifest

    @staticmethod
    def get_data_title():
        return 'Scripts Manifest'


class ScriptPythonData(ScriptData, object):
    """
    Class used to define Python scripts stored in disk files
    """

    @staticmethod
    def get_data_type():
        # return constants.ScriptLanguages.Python
        return ScriptTypes.Python

    @staticmethod
    def get_data_extension():
        return ScriptExtensions.Python

    @staticmethod
    def get_data_title():
        return 'Python Script'

    def open(self):
        lines = ''
        return lines
