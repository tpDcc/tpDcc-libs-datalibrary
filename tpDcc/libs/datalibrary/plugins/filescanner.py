#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base data scanner for files located in disk
"""

from __future__ import print_function, division, absolute_import

import os
import time
import locale
import getpass
from collections import OrderedDict

from tpDcc.libs.python import python, fileio, path as path_utils

from tpDcc.libs.datalibrary.core import scanner


class FileScannerPlugin(scanner.BaseScanner):

    SCAN_TYPE = 'file_scanner'

    @classmethod
    def can_represent(cls, location):
        """
        Returns whether or not the scanner plugin is able to scrape the given dat source identifier or not
        :param location: str, location identifier. This could be a URL, a file path, a UUID, etc
        :return: bool
        """

        return os.path.exists(location)

    @classmethod
    def identifiers(cls, location, skip_pattern, recursive=True):
        """
        Returns a list of data identifiers found in the given data locations

        NOTE: This should always yield results!

        :param location: str, location to scan
        :param skip_pattern: regex, regular expression object which, if matched on a location should be skipped
        :param recursive: bool, If True, all locations below the given one will also be scanned, otherwise only the
            immediate location will be scanned
        :return: generator
        """

        location = path_utils.clean_path(location)
        if not skip_pattern or not skip_pattern.search(location):
            yield location

        if recursive:
            for root, _, files in os.walk(location):
                root = path_utils.clean_path(root)
                if not skip_pattern or not skip_pattern.search(root):
                    yield root
                for file_name in files:
                    result = path_utils.clean_path(os.path.join(root, file_name))
                    if not skip_pattern or not skip_pattern.search(result):
                        yield result
        else:
            for file_name in os.listdir(location):
                result = path_utils.clean_path(os.path.join(location, file_name))
                if not skip_pattern or not skip_pattern.search(result):
                    yield result

    @classmethod
    def above(cls, location):
        """
        Returns all the search locations above the current one. If there is no locations above, or the concept of
        above makes no sense for the scan plugin an empty list should be returned
        :param location:
        :return: list
        """

        location = path_utils.clean_path(location)
        parts = location.split(path_utils.SEPARATOR)
        folders = list()

        for i in range(len(parts)):
            folder_path = '/'.join(parts[:-i])
            if folder_path and not folder_path.endswith(':'):
                folders.append(folder_path)

        return folders

    @classmethod
    def below(cls, location):
        """
        Returns all the search locations below the current one. If there is no locations below, or the concept of
        below makes no sense for the scan plugin an empty list should be returned
        :param location:
        :return: list
        """

        folders = list()
        for folder in os.listdir(location):
            folder_path = path_utils.clean_path(os.path.join(location, folder))

            if os.path.isdir(folder_path):
                folders.append(folder_path)

        return folders

    @classmethod
    def check(cls, identifier):
        """
        Returns whether the given identifier is still considered valid or not or whether it cannot make that assumption
        :param identifier: str, plugin identifier to check
        :return: int
        """

        if len(identifier) < 2 or identifier[1] != ':' or (identifier[2] != '\\' and identifier[2] != '/'):
            return cls.ScanStatus.UNKNOWN

        if not os.path.exists(identifier):
            return cls.ScanStatus.NOT_VALID

        return cls.ScanStatus.VALID

    @classmethod
    def fields(cls, identifier):

        ctime = str(time.time()).split('.')[0]
        user = getpass.getuser()
        if user and python.is_python2():
            user.decode(locale.getpreferredencoding())

        name, extension = os.path.splitext(os.path.basename(identifier))
        return OrderedDict([
            ('name', name),
            ('extension', extension),
            ('directory', os.path.dirname(identifier)),
            ('folder', os.path.isdir(identifier)),
            ('user', user),
            ('modified', fileio.get_last_modified_date(identifier)),
            ('ctime', ctime)
        ])
