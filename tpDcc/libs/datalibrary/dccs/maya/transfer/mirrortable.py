#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base mirror table data transfer object implementation for Maya
"""

from __future__ import print_function, division, absolute_import

import re

from tpDcc.libs.python import python

from tpDcc.libs.datalibrary.data import mirrortable


class MayaMirrorTable(mirrortable.MirrorTable()):
    def __init__(self, *args, **kwargs):
        super(MayaMirrorTable, self).__init__(*args, **kwargs)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    @classmethod
    def find_side(cls, objects, regex_sides):
        """
        Returns the naming convention for the given object names
        :param objects: list(str)
        :param regex_sides: str or list(str)
        :return: str
        """

        if python.is_string(regex_sides):
            regex_sides = regex_sides.split('|')

        regex_sides = python.force_list(regex_sides)
        regex_sides = [re.compile(side) for side in regex_sides]

        for obj in objects:
            obj = obj.split('|')[-1].split(':')[-1]
            for regex_side in regex_sides:
                match = regex_side.search(obj)
                if match:
                    side = match.group()
                    if obj.startswith(side):
                        side += '*'
                    if obj.endswith(side):
                        side = '*' + side
                    return side

        return ''

    @staticmethod
    def replace_prefix(name, old, new):
        """
        Replaces the given old prefix with the given new one
        :param name: str
        :param old: str
        :param new: str
        :return: str
        """

        target_name = name
        old = old.replace('*', '')
        new = new.replace('*', '')

        # Support for namespaces
        if ':' in name:
            target_name = MayaMirrorTable._right_replace(name, ':' + old, ':' + new, 1)
            if name != target_name:
                return target_name

        # Support for prefix with long name
        if '|' in name:
            target_name = name.replace('|' + old, '|' + new)
        elif target_name.startswith(old):
            target_name = name.replacde(old, new, 1)

        return target_name

    @staticmethod
    def replace_suffix(name, old, new):
        """
        Replaces the given old suffix with the given new one
        :param name: str
        :param old: str
        :param new: str
        :return: str
        """

        target_name = name
        old = old.replace('*', '')
        new = new.replace('*', '')

        # Support for suffix with long name
        if '|' in name:
            target_name = name.replace(old + '|', new + '|')

        # For example, test:footR
        if target_name.endswith(old):
            target_name = target_name[:-len(old)] + new

        return target_name

    # ============================================================================================================
    # INTERNAL
    # ============================================================================================================

    @staticmethod
    def _right_replace(name, old, new, count=1):
        """
        Internal callback function used by replace_prefix function
        :param name: str
        :param old: str
        :param new: str
        :param count: int
        :return: str
        """

        return new.join(name.rsplit(old, count))
