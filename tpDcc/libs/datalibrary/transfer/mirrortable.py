#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base mirror table data transfer object implementation
"""

from __future__ import print_function, division, absolute_import

import re
import logging

from tpDcc import dcc
from tpDcc.libs.python import python, decorators
from tpDcc.libs.qt.core import decorators as qt_decorators

from tpDcc.libs.datalibrary.core import transfer

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')

# TODO: We should be able to configure this data using a configuration file
RE_LEFT_SIDE = "Left|left|Lf|lt_|_lt|lf_|_lf|_l_|_L|L_|:l_|^l_|_l$|:L|^L"
RE_RIGHT_SIDE = "Right|right|Rt|rt_|_rt|_r_|_R|R_|:r_|^r_|_r$|:R|^R"

# TODO: Node data types should be configured depending of the DCC
VALID_NODE_TYPES = ["joint", "transform"]


class _MetaMirrorTable(type):

    def __call__(self, *args, **kwargs):
        as_class = kwargs.get('as_class', True)
        if dcc.is_maya():
            from tpDcc.libs.datalibrary.dccs.maya.data import mirrortable
            if as_class:
                return mirrortable.MayaMirrorTable
            else:
                return type.__call__(mirrortable.MayaMirrorTable, *args, **kwargs)
        else:
            if as_class:
                return BaseMirrorTable
            else:
                return type.__call__(BaseMirrorTable, *args, **kwargs)


class MirrorPlane:
    YZ = [-1, 1, 1]
    XZ = [1, -1, 1]
    XY = [1, 1, -1]


class MirrorOptions:
    Swap = 0
    LeftToRight = 1
    RightToLeft = 2


class KeysOptions:
    All = "All Keys"
    SelectedRange = "Selected Range"


class BaseMirrorTable(transfer.TransferObject()):

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    @classmethod
    @decorators.timestamp
    @dcc.undo_decorator()
    @qt_decorators.show_wait_cursor
    @dcc.restore_selection_decorator()
    def from_objects(cls, objects, left_side=None, right_side=None, mirror_plane=None):
        """
        Creates a new mirror table instance from the given objects
        :param objects: list(str)
        :param left_side: str
        :param right_side: str
        :param mirror_plane: MirrorPlane or str
        :return: MirrorTable
        """

        mirror_plane = mirror_plane or MirrorPlane.YZ
        if python.is_string(mirror_plane):
            if mirror_plane.lower() == 'yz':
                mirror_plane = MirrorPlane.YZ
            elif mirror_plane.lower() == 'xz':
                mirror_plane = MirrorPlane.XZ
            elif mirror_plane.lower() == 'xy':
                mirror_plane = MirrorPlane.XY

        mirror_table = cls()
        mirror_table.set_metadata('left', left_side)
        mirror_table.set_metadata('right', right_side)
        mirror_table.set_metadata('mirrorPlane', mirror_plane)

        for obj in objects:
            node_type = dcc.node_type(obj)
            if node_type in VALID_NODE_TYPES:
                mirror_table.add(obj)
            else:
                LOGGER.info('Node of type {} is not supported. Node name: {}'.format(node_type, obj))

        return mirror_table

    # ============================================================================================================
    # CLASS METHODS
    # ============================================================================================================

    @classmethod
    def find_side(cls, objects, regex_sides):
        """
        Returns the naming convention for the given object names
        :param objects: list(str)
        :param regex_sides: str or list(str)
        :return: str
        """

        regex_sides = python.force_list(regex_sides)
        regex_sides = [re.compile(side) for side in regex_sides]

        for obj in objects:
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

    @classmethod
    def match_side(cls, name, side):
        """
        Returns True if the name contains the given side
        :param name: str
        :param side: str
        :return: bool
        """

        if side:

            # Prefix
            if side.endswith('*'):
                return cls.replace_prefix(name, side, 'X') != name

            # Suffix
            elif side.startswith('*'):
                return cls.replace_suffix(name, side, 'X') != name

            # Other
            else:
                return side in name

        return False

    @classmethod
    def replace(cls, name, old, new):
        """
        Replaces prefix given name prefix or suffix
        :param name: str
        :param old: str
        :param new: str
        :return: str
        """

        # Prefix
        if old.endswith('*') or new.endswith('*'):
            name = cls.replace_prefix(name, old, new)

        # Suffix
        elif old.startswith('*') or new.startswith('*'):
            name = cls.replace_suffix(name, old, new)

        # Other
        else:
            name = name.replace(old, new)

        return name

    # ============================================================================================================
    # STATIC METHODS
    # ============================================================================================================

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

        if target_name.startswith(old):
            target_name = name.replace(old, new, 1)

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

        # For example, test:footR
        if target_name.endswith(old):
            target_name = target_name[:-len(old)] + new

        return target_name

    @staticmethod
    def find_left_side(objects):
        """
        Returns the left side naming convention for the given objects
        :param objects: list(str)
        :return: str
        """

        return MirrorTable.find_side(objects, RE_LEFT_SIDE)

    @staticmethod
    def find_right_side(objects):
        """
        Returns the right side naming convention for the given objects
        :param objects: list(str)
        :return: str
        """

        return MirrorTable.find_side(objects, RE_RIGHT_SIDE)

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def left_side(self):
        """
        Returns left side name
        :return: str
        """

        return self.metadata().get('left')

    def is_left_side(self, name):
        """
        Returns True if the given object contains the left side string
        :param name: str
        :return: bool
        """

        side = self.left_side()
        return self.match_side(name, side)

    def left_count(self, objects=None):
        """
        Returns number of objects in the left side. If not objects are given, all objects will be taken into
        consideration
        :param objects: list(str)
        :return: int
        """

        objects = objects or self.objects()
        return len([obj for obj in objects if self.is_left_side(obj)])

    def right_side(self):
        """
        Returns right side name
        :return: str
        """

        return self.metadata().get('right')

    def is_right_side(self, name):
        """
        Returns True if the given object contains the right side string
        :param name: str
        :return: bool
        """

        side = self.right_side()
        return self.match_side(name, side)

    def right_count(self, objects=None):
        """
        Returns number of objects in the right side. If not objects are given, all objects will be taken into
        consideration
        :param objects: list(str)
        :return: int
        """

        objects = objects or self.objects()
        return len([obj for obj in objects if self.is_right_side(obj)])

    def mirror_plane(self):
        """
        Returns mirror plane
        :return: list(int) or None
        """

        return self.metadata().get('mirrorPlane')

    def mirror_axis(self, name):
        """
        Returns mirror axis of the given object
        :param name: str
        :return: list(int)
        """

        return self.objects()[name]['mirrorAxis']

    def mirror_object(self, obj):
        """
        Returns the other/opposite side for teh given name (if exists); Otherwise None.
        :param obj: str
        :return: str or None
        """

        left_side = self.left_side()
        right_side = self.right_side()

        return self.mirror_object_from_sides(obj, left_side, right_side)

    def mirror_object_from_sides(self, obj, left_side, right_side):
        """
        Returns mirror name from given object based on given sides (if exists); Otherwise None.
        :param obj: str
        :param left_side: str
        :param right_side: str
        :return: str or None
        """

        # Prefix
        if left_side.endswith('*') or right_side.endswith('*'):
            target_name = self.replace_prefix(obj, left_side, right_side)
            if obj == target_name:
                target_name = self.replace_prefix(obj, right_side, left_side)
            if target_name != obj:
                return target_name

        # Suffix
        elif left_side.startswith('*') or right_side.startswith('*'):
            target_name = self.replace_suffix(obj, left_side, right_side)
            if obj == target_name:
                target_name = self.replace_suffix(obj, right_side, left_side)
            if target_name != obj:
                return target_name

        # Other
        else:
            target_name = obj.replace(left_side, right_side)
            if target_name == obj:
                target_name = obj.replace(right_side, left_side)
            if target_name != obj:
                return target_name

        # At this point, given object has no opposite side object (maybe is a center object)

        return None


@decorators.add_metaclass(_MetaMirrorTable)
class MirrorTable(object):
    pass
