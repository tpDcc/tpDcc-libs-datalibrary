#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base mirror table data transfer object implementation for Maya
"""

from __future__ import print_function, division, absolute_import

import re
import logging

import maya.cmds

from tpDcc import dcc
from tpDcc.libs.python import python, decorators
from tpDcc.dccs.maya.core import animation as anim_utils, decorators as maya_decorators

from tpDcc.libs.datalibrary.core import consts, exceptions, mirrortable
from tpDcc.libs.datalibrary.dccs.maya.core import utils

logger = logging.getLogger(consts.LIB_ID)


class MayaMirrorTable(mirrortable.BaseMirrorTable):
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

    def match_objects(self, objects=None, **kwargs):
        namespaces = kwargs.pop('namespaces', None)

        source_objects = list(self.objects().keys())
        matches = utils.match_names(source_objects, target_objects=objects, target_namespaces=namespaces)
        for source_node, target_node in matches:
            target_name = target_node.name()
            mirror_axis = self.mirror_axis(source_node.name())
            yield source_node.name(), target_name, mirror_axis

    def is_attribute_mirrored(self, attr, mirror_axis):
        if mirror_axis == [-1, 1, 1]:
            if attr == "translateX" or attr == "rotateY" or attr == "rotateZ":
                return True

        elif mirror_axis == [1, -1, 1]:
            if attr == "translateY" or attr == "rotateX" or attr == "rotateZ":
                return True

        elif mirror_axis == [1, 1, -1]:
            if attr == "translateZ" or attr == "rotateX" or attr == "rotateY":
                return True

        elif mirror_axis == [-1, -1, -1]:
            if attr == "translateX" or attr == "translateY" or attr == "translateZ":
                return True

        return False

    @decorators.timestamp
    @maya_decorators.undo
    @maya_decorators.show_wait_cursor
    @maya_decorators.restore_selection
    def load(self, *args, **kwargs):

        objects = kwargs.get('objects', None)
        namespaces = kwargs.get('namespaces', None)
        option = kwargs.get('option', None)
        keys_option = kwargs.get('keys_option', None)
        time = kwargs.get('time', None)

        if option and not isinstance(option, int):
            if option.lower() == 'swap':
                option = 0
            elif option.lower() == 'left to right':
                option = 1
            elif option.lower() == 'right to left':
                option = 2
            else:
                raise ValueError('Invalid load option: {}'.format(option))

        self.validate(namespaces=namespaces)

        results = dict()
        animation = True
        found_object = False
        source_objects = list(self.objects().keys())

        if option is None:
            option = mirrortable.MirrorOptions.Swap
        if keys_option == mirrortable.KeysOptions.All:
            time = None
        elif keys_option == mirrortable.KeysOptions.SelectedRange:
            time = anim_utils.get_selected_frame_range()

        # check that given time is not a single frame
        if time and time[0] == time[1]:
            time = None
            animation = None

        matches = utils.match_names(source_objects=source_objects, target_objects=objects, target_namespaces=namespaces)
        for source_node, target_node in matches:
            target_object = target_node.name()
            target_object2 = self.mirror_object(target_object) or target_object
            if target_object2 not in results:
                results[target_object] = target_object2
                mirror_axis = self.mirror_axis(source_node.name())
                target_object_exists = dcc.node_exists(target_object)
                target_object2_exists = dcc.node_exists(target_object2)
                if target_object_exists and target_object2_exists:
                    found_object = True
                    if animation:
                        self.transfer_animation(
                            target_object, target_object2, mirror_axis=mirror_axis, option=option, time=time)
                    else:
                        self.transfer_static(target_object, target_object2, mirror_axis=mirror_axis, option=option)
                else:
                    if not target_object_exists:
                        logger.warning('Cannot find destination object {}'.format(target_object))
                    if not target_object2_exists:
                        logger.warning('Cannot find mirrored destination object {}'.format(target_object2))

        dcc.focus_ui_panel('MayaWindow')

        if not found_object:
            raise exceptions.NoMatchFoundError('No objects match wne loading mirror table data')

    def _transfer_animation(self, source_object, target_object, attrs=None, mirror_axis=None, time=None):
        maya.cmds.cutKey(target_object, time=time or ())
        if maya.cmds.copyKey(source_object, time=time or ()):
            if not time:
                maya.cmds.pasteKey(target_object, option='replaceCompletely')
            else:
                maya.cmds.pasteKey(target_object, time=time, option='replace')
        if attrs is None:
            attrs = maya.cmds.listAttr(source_object, keyable=True) or list()
        for attr in attrs:
            source_attr = utils.Attribute(source_object, attr)
            target_attr = utils.Attribute(target_object, attr)
            if target_attr.exists():
                if target_attr.is_connected():
                    if self.is_attribute_mirrored(attr, mirror_axis):
                        maya.cmds.scaleKey(target_attr.name(), valueScale=-1, attribute=attr)
                else:
                    value = source_attr.value
                    self.set_attribute(target_object, attr, value, mirror_axis=mirror_axis)

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

        pass
