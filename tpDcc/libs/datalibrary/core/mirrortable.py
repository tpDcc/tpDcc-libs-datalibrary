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

from tpDcc.libs.datalibrary.core import consts, transfer

logger = logging.getLogger(consts.LIB_ID)

# TODO: We should be able to configure this data using a configuration file
RE_LEFT_SIDE = "Left|left|Lf|lt_|_lt|lf_|_lf|_l_|_L|L_|:l_|^l_|_l$|:L|^L"
RE_RIGHT_SIDE = "Right|right|Rt|rt_|_rt|_r_|_R|R_|:r_|^r_|_r$|:R|^R"

# TODO: Node data types should be configured depending of the DCC
VALID_NODE_TYPES = ["joint", "transform"]


class _MetaMirrorTable(type):

    def __call__(self, *args, **kwargs):
        as_class = kwargs.get('as_class', True)
        if dcc.is_maya():
            from tpDcc.libs.datalibrary.dccs.maya.core import mirrortable
            if as_class:
                return mirrortable.MayaMirrorTable
            else:
                return type.__call__(mirrortable.MayaMirrorTable, *args, **kwargs)
        else:
            if as_class:
                return BaseMirrorTable
            else:
                return type.__call__(BaseMirrorTable, *args, **kwargs)


def save_mirror_table(path, objects, metadata=None, *args, **kwargs):
    """
    Function that saves mirror table in disk
    :param path: str
    :param objects: list(str)
    :param metadata: dict or None
    :param args: list
    :param kwargs: dict
    :return: MirrorTable
    """

    mirror_table = MirrorTable().from_objects(objects, *args, **kwargs)
    if metadata:
        mirror_table.update_metadata(metadata)
    mirror_table.save(path)

    return mirror_table


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


class BaseMirrorTable(transfer.DataTransferObject()):

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

        if left_side:
            left_side = left_side.split(',')
            left_side = [split.strip() for split in left_side]
        if right_side:
            right_side = right_side.split(',')
            right_side = [split.strip() for split in right_side]

        mirror_table = cls()
        mirror_table.set_metadata('left', left_side)
        mirror_table.set_metadata('right', right_side)
        mirror_table.set_metadata('mirrorPlane', mirror_plane)

        for obj in objects:
            node_type = dcc.node_type(obj)
            if node_type in VALID_NODE_TYPES:
                mirror_table.add_objects(obj)
            else:
                logger.info('Node of type {} is not supported. Node name: {}'.format(node_type, obj))

        return mirror_table

    def parse_object(self, name):
        """
        Returns the object data for the given object name
        :param name: str
        :return: dict
        """

        result = {'mirrorAxis': self._calculate_mirror_axis(name)}

        return result

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

    @classmethod
    def find_left_side(cls, objects):
        """
        Returns the left side naming convention for the given objects
        :param objects: list(str)
        :return: str
        """

        return cls.find_side(objects, RE_LEFT_SIDE)

    @classmethod
    def find_right_side(cls, objects):
        """
        Returns the right side naming convention for the given objects
        :param objects: list(str)
        :return: str
        """

        return cls.find_side(objects, RE_RIGHT_SIDE)

    @classmethod
    def format_value(cls, attr, value, mirror_axis):

        if cls.is_attribute_mirrored(attr, mirror_axis):
            return value * -1

        return value

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

    def is_valid_mirror(self, obj, option):
        if option == MirrorOptions.Swap:
            return True
        elif option == MirrorOptions.LeftToRight and self.is_left_side(obj):
            return False
        elif option == MirrorOptions.RightToLeft and self.is_right_side(obj):
            return False

        return True

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

        left_sides = python.force_list(self.left_side())
        right_sides = python.force_list(self.right_side())

        for left_side, right_side in zip(left_sides, right_sides):
            obj = self.mirror_object_from_sides(obj, left_side, right_side)

        return obj

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

    def set_attribute(self, name, attr, value, mirror_axis=None):
        if mirror_axis is not None:
            value = self.format_value(attr, value, mirror_axis)
        try:
            dcc.set_attribute_value(name, attr, value)
        except RuntimeError:
            logger.warning('Cannot mirror static attribute {}.{}'.format(name, attr))

    def transfer_static(self, source_object, target_object, mirror_axis=None, attrs=None, option=None):

        option = option or MirrorOptions.Swap

        source_value = None
        target_value = None
        source_valid = self.is_valid_mirror(source_object, option)
        target_valid = self.is_valid_mirror(target_object, option)

        attrs = attrs or dcc.list_attributes(source_object, keyable=True) or list()
        for attr in attrs:
            target_attr = '{}.{}'.format(target_object, attr)
            if dcc.node_exists(target_attr):
                if target_valid:
                    source_value = dcc.get_attribute_value(source_object, attr)
                if source_valid:
                    target_value = dcc.get_attribute_value(target_object, attr)
                if target_valid:
                    self.set_attribute(target_object, attr, source_value, mirror_axis=mirror_axis)
                if source_valid:
                    self.set_attribute(source_object, attr, target_value, mirror_axis=mirror_axis)
            else:
                logger.warning('Cannot find destination attribute "{}"'.format(target_attr))

    def transfer_animation(self, source_object, target_object, mirror_axis=None, option=None, time=None):
        option = option or MirrorOptions.Swap

        source_valid = self.is_valid_mirror(source_object, option)
        target_valid = self.is_valid_mirror(target_object, option)

        temp_obj = dcc.duplicate_node(source_object, new_node_name='DELETE_ME', only_parent=True)
        try:
            if target_valid:
                self._transfer_animation(source_object, temp_obj, time=time)
            if source_valid:
                self._transfer_animation(target_object, source_object, mirror_axis=mirror_axis, time=time)
            if target_valid:
                self._transfer_animation(temp_obj, target_object, mirror_axis=mirror_axis, time=time)
        finally:
            dcc.delete_node(temp_obj)

    def match_objects(self, objects=None, **kwargs):
        raise NotImplementedError()

    def is_attribute_mirrored(self, attr, mirror_axis):
        raise NotImplementedError()

    # ============================================================================================================
    # INTERNAL
    # ============================================================================================================

    def _transfer_animation(self, source_object, target_object, attrs=None, mirror_axis=None, time=None):
        raise NotImplementedError()

    def _calculate_mirror_axis(self, source_object):
        """
        Internal function that calculates the mirror axis of the given object name
        :param source_object: str
        :return: list(int)
        """

        result = [1, 1, 1]
        target_object = self.mirror_object(source_object) or source_object
        mirror_plane = self.mirror_plane()

        if target_object == source_object or not dcc.node_exists(target_object):
            result = dcc.get_mirror_axis(source_object, mirror_plane)
        else:
            if dcc.is_axis_mirrored(source_object, target_object, [1, 0, 0], mirror_plane):
                result[0] = -1
            if dcc.is_axis_mirrored(source_object, target_object, [0, 1, 0], mirror_plane):
                result[1] = -1
            if dcc.is_axis_mirrored(source_object, target_object, [0, 0, 1], mirror_plane):
                result[2] = -1

        return result


@decorators.add_metaclass(_MetaMirrorTable)
class MirrorTable(object):
    pass
