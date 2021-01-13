#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base data parts scanner implementation
"""

from __future__ import print_function, division, absolute_import


class BaseScanner(object):

    class ScanStatus(object):

        # Indicates that plugin identifier is still active and valid
        VALID = 0

        # Indicates that plugin identifier should no longer considered within the database
        NOT_VALID = 1

        # Indicates plugin identifier cannot be digested by this process any reason
        UNKNOWN = 2

    SCAN_TYPE = ''

    @classmethod
    def can_represent(cls, location):
        """
        Returns whether or not the scanner plugin is able to scrape the given dat source identifier or not
        :param location: str, location identifier. This could be a URL, a file path, a UUID, etc
        :return: bool
        """

        return False

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

        return list()

    @classmethod
    def above(cls, location):
        """
        Returns all the search locations above the current one. If there is no locations above, or the concept of
        above makes no sense for the scan plugin an empty list should be returned
        :param location:
        :return: list
        """

        return list()

    @classmethod
    def below(cls, location):
        """
        Returns all the search locations below the current one. If there is no locations below, or the concept of
        below makes no sense for the scan plugin an empty list should be returned
        :param location:
        :return: list
        """

        return list()

    @classmethod
    def check(cls, identifier):
        """
        Returns whether the given identifier is still considered valid or not or whether it cannot make that assumption
        :param identifier: str, plugin identifier to check
        :return: int
        """

        return cls.ScanStatus.UNKNOWN
