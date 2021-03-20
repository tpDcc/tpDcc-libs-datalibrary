#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module function that contains util class to handle pose data information
"""

from __future__ import print_function, division, absolute_import

import logging

from tpDcc import dcc
from tpDcc.libs.python import decorators, path as path_utils

from tpDcc.libs.datalibrary.core import consts, exceptions
from tpDcc.libs.datalibrary.dccs.maya.core import utils, transfer, selectionset

logger = logging.getLogger(consts.LIB_ID)

_LOADED_POSE = None


def save_pose(path, objects, metadata=None):
    """
    Function for saving pose to disk
    :param path: str
    :param objects: list(str)
    :param metadata: dict or None
    :return: Pose
    """

    pose_to_save = Pose.from_objects(objects)
    if metadata:
        pose_to_save.update_metadata(metadata)
    pose_to_save.save(path)

    return pose_to_save


def load_pose(path, *args, **kwargs):
    """
    Loads pose from file in disk
    :param path: str
    :param args: list
    :param kwargs: dict
    :return: Pose
    """

    global _LOADED_POSE

    clear_cache = kwargs.get('clear_cache', False)
    if not _LOADED_POSE or path_utils.clean_path(_LOADED_POSE.path) != path_utils.clean_path(path) or clear_cache:
        _LOADED_POSE = Pose.from_path(path)
    _LOADED_POSE.load(*args, **kwargs)

    return _LOADED_POSE


class Pose(transfer.MayaDataTransferObject):
    def __init__(self):
        super(Pose, self).__init__()

        self._cache = None
        self._cache_key = None
        self._mtime = None
        self._mirror_table = None
        self._is_loading = False
        self._selection = None
        self._auto_key_frame = None

    # =================================================================================================================
    # PROPERTIES
    # =================================================================================================================

    @property
    def cache(self):
        """
        Returns the current cached attributes for the pose
        :return: list
        """

        return self._cache

    # =================================================================================================================
    # OVERRIDES
    # =================================================================================================================

    def parse_object(self, name):
        """
        Returns the object data for the given object name
        :param name: str
        :return: dict
        """

        attrs = list(set(dcc.client().list_attributes(name, unlocked=True, keyable=True) or list()))
        attrs = [utils.Attribute(name, attr) for attr in attrs]

        data_dict = {'attrs': self.attrs(name), 'uuid': dcc.client().node_handle(name)}

        for attr in attrs:
            if not attr.is_valid():
                continue
            if attr.value is None:
                logger.warning('Cannot save the attribute {} with value None'.format(attr.fullname))
            else:
                data_dict['attrs'][attr.attr] = {'type': attr.type, 'value': attr.value}

        return data_dict

    @decorators.timestamp
    def load(self, *args, **kwargs):
        """
        Loads the pose to the given objects or namespaces
        :param args:
        :param kwargs:
        :return:
        """

        blend = kwargs.get('blend', 100)
        key = kwargs.get('key', False)
        additive = kwargs.get('additive', False)
        mirror = kwargs.get('mirror', False)
        mirror_table = kwargs.get('mirror_table', None)
        batch_mode = kwargs.get('batch_mode', False)
        clear_selection = kwargs.get('clear_selection', False)
        refresh = kwargs.get('refresh', False)

        if mirror and not mirror_table:
            logger.warning('Impossible to mirror pose without a mirror table!')
            mirror = False

        if batch_mode:
            key = False

        self.update_cache(**kwargs)

        self._before_load(clear_selection=clear_selection)

        try:
            self.load_cache(blend=blend, key=key, mirror=mirror, additive=additive)
        finally:
            if not batch_mode:
                self._after_load()
                dcc.focus_ui_panel('MayaWindow')

        if refresh:
            dcc.refresh_viewport()

    # =================================================================================================================
    # BASE
    # =================================================================================================================

    def attrs(self, name):
        """
        Returns the attributes data of the given node
        :param name: str
        :return: dict
        """

        return self.object(name).get('attrs', dict())

    def attr(self, name, attr):
        """
        Returns the attribute data for the given name and attribute
        :param name: str
        :param attr: str
        :return: dict
        """

        return self.attrs(name).get(attr, dict())

    def attr_type(self, name, attr):
        """
        Returns the attribute type for the given name and attribute
        :param name: str
        :param attr: str
        :return: str
        """

        return self.attr(name, attr).get('type', None)

    def attr_value(self, name, attr):
        """
         Returns the attribute value for the given name and attribute
         :param name: str
         :param attr: str
         :return: str
         """

        return self.attr(name, attr).get('value', None)

    def mirror_table(self):
        """
        Returns the mirror table for the current pose
        :return: MirrorTable
        """

        return self._mirror_table

    def set_mirror_table(self, mirror_table):
        """
        Sets the mirror table for the current pose
        :param mirror_table: MirrorTable
        """

        objects = list(self.objects().keys())
        self._mirror_table = mirror_table

        for source_name, target_name, mirror_axis in mirror_table.match_objects(objects):
            self.set_mirror_axis(target_name, mirror_axis)

    def mirror_axis(self, name):
        """
        Returns the mirror axis for the given object name
        :param name: str
        :return: list(int) or None
        """

        result = None
        if name in self.objects():
            result = self.object(name).get('mirror_axis', None)
        if result is None:
            logger.debug('Cannot find mirror axis in pose for "{}"'.format(name))

        return result

    def set_mirror_axis(self, name, mirror_axis):
        """
        Sets the mirror axis for the given object name
        :param name: str
        :param mirror_axis: list(int)
        """

        if name in self.objects():
            self.object(name).setdefault('mirror_axis', mirror_axis)
        else:
            logger.debug('Object does not exist in pose. Cannot set mirror axis for "{}"'.format(name))

    def mirror_value(self, name, attr, mirror_axis):
        """
        Returns the mirror value for the given object name, attribute name and mirror axis
        :param name: str
        :param attr: str
        :param mirror_axis: list(int)
        :return: None or int or float
        """

        value = None
        if self.mirror_table() and name:
            value = self.attr_value(name, attr)
            if value is not None:
                value = self.mirror_table().format_value(attr, value, mirror_axis)
            else:
                logger.warning('Cannot find mirror value for "{}.{}"'.format(name, attr))

        return value

    def update_cache(self, **kwargs):
        """
        Updates the pose cache
        :param kwargs: dict
        """

        objects = kwargs.get('objects', None)
        namespaces = kwargs.get('namespaces', None)
        attrs = kwargs.get('attrs', None)
        ignore_connected = kwargs.get('ignore_connected', False)
        only_connected = kwargs.get('only_connected', False)
        mirror_table = kwargs.get('mirror_table', None)
        batch_mode = kwargs.get('batch_mode', False)
        clear_cache = kwargs.get('clear_cache', True)
        search_and_replace = kwargs.get('search_and_replace', None)

        if clear_cache or not batch_mode or not self._mtime:
            self._mtime = self.mtime()
        mtime = self._mtime

        current_time = dcc.get_current_time()
        cache_key_list = [mtime, objects, attrs, namespaces, ignore_connected, search_and_replace, current_time]
        cache_key = ''.join([str(cache_key_item) for cache_key_item in cache_key_list])
        if self._cache_key != cache_key or clear_cache:
            self.validate(namespaces=namespaces)
            self._cache = list()
            self._cache_key = cache_key
            target_objects = objects
            source_objects = self.objects()
            using_namespaces = not objects and namespaces
            if mirror_table:
                self.set_mirror_table(mirror_table)
            search = None
            replace = None
            if search_and_replace:
                search = search_and_replace[0]
                replace = search_and_replace[1]
            matches = utils.match_names(source_objects, target_objects=target_objects, search=search, replace=replace)
            for source_node, target_node in matches:
                self.cache_node(
                    source_node, target_node, attrs=attrs, only_connected=only_connected,
                    ignore_connected=ignore_connected, using_namespaces=using_namespaces)

        if not self.cache:
            raise exceptions.NoMatchFoundError('No objects match when loading pose data')

    def cache_node(self, source_node, target_node, **kwargs):
        """
        :param source_node: Node
        :param target_node: Node
        Caches the given pair of nodes
        :param kwargs: dict
        """

        attrs = kwargs.get('attrs', None)
        ignore_connected = kwargs.get('ignore_connected', None)
        only_connected = kwargs.get('only_connected', None)
        using_namespaces = kwargs.get('using_namespaces', None)

        mirror_axis = None
        mirror_object = None

        # remove first pipe in case object has a parent node
        target_node.strip_first_pipe()
        source_name = source_node.name()

        if self.mirror_table():
            mirror_object = self.mirror_table().mirror_object(source_name)
            if not mirror_object or not dcc.node_exists(mirror_object):
                mirror_object = self.mirror_table().mirror_object(dcc.client().node_short_name(source_name))
            if not mirror_object:
                mirror_object = source_name
                logger.warning('Cannot find mirror object in pose for "{}"'.format(source_name))

            # retrieve mirror axis from mirror object or from source node
            mirror_axis = self.mirror_axis(mirror_object) or self.mirror_axis(source_name)

            if mirror_object and not dcc.node_exists(mirror_object):
                logger.warning('Mirror object does not exist in the scene {}'.format(mirror_object))

        if using_namespaces:
            try:
                target_node = target_node.to_short_name()
            except exceptions.NoObjectFoundError as exc:
                logger.warning(exc)
                return
            except exceptions.MoreThanOneObjectFoundError as exc:
                logger.warning(exc)
                return

        for attr in self.attrs(source_name):
            if attrs and attr not in attrs:
                continue
            target_attribute = utils.Attribute(target_node.name(), attr)
            is_connected = target_attribute.is_connected()
            if (ignore_connected and is_connected) or (only_connected and not is_connected):
                continue

            attr_type = self.attr_type(source_name, attr)
            attr_value = self.attr_value(source_name, attr)
            source_mirror_value = self.mirror_value(mirror_object, attr, mirror_axis=mirror_axis)
            source_attribute = utils.Attribute(target_node.name(), attr, value=attr_value, type=attr_type)
            target_attribute.clear_cache()

            self._cache.append((source_attribute, target_attribute, source_mirror_value))

    def load_cache(self, blend=100, key=False, mirror=False, additive=False):
        """
        Loads poses from current cache
        :param blend: float
        :param key: bool
        :param mirror: bool
        :param additive: bool
        """

        cache = self.cache
        if not cache:
            return

        for i in range(len(cache)):
            source_attribute, target_attribute, source_mirror_value = cache[i]
            if not source_attribute or not target_attribute:
                continue
            value = source_mirror_value if mirror and source_mirror_value is not None else source_attribute.value
            try:
                target_attribute.set(value, blend=blend, key=key, additive=additive)
            except (ValueError, RuntimeError):
                cache[i] = (None, None)
                logger.warning('Ignoring {}'.format(target_attribute.fullname))

    def select(self, objects=None, namespaces=None, **kwargs):
        """
        Select the objects contained in the pose file
        :param objects: list(str) or None
        :param namespaces: list(str) or None
        :param kwargs: dict
        """

        selection_set = selectionset.SelectionSet.from_path(self.path)
        selection_set.load(objects=objects, namespaces=namespaces, **kwargs)

    # =================================================================================================================
    # INTERNAL
    # =================================================================================================================

    def _before_load(self, clear_selection=True):
        """
        Internal function that is called before loading the pose
        :param clear_selection:
        """

        logger.debug('Before Load Pose "{}"'.format(self.path))

        if not self._is_loading:
            self._is_loading = True
            dcc.enable_undo()
            self._selection = dcc.selected_nodes() or list()
            self._auto_key_frame = dcc.is_auto_keyframe_enabled()
            dcc.set_auto_keyframe_enabled(False)
            if clear_selection:
                dcc.clear_selection()

    def _after_load(self):
        """
        Internal function that is called after loading the pose
        """

        if not self._is_loading:
            return

        logger.debug('After Load Pose "{}"'.format(self.path))

        self._is_loading = False
        if self._selection:
            dcc.select_node(self._selection)
            self._selection = None
        dcc.set_auto_keyframe_enabled(self._auto_key_frame)
        dcc.disable_undo()

        logger.info('Loaded Pose "{}"'.format(self.path))
