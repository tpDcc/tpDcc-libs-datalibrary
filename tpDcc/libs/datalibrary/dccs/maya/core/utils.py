#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains utils functions used by data library in Maya
"""

from __future__ import print_function, division, absolute_import

import logging

from tpDcc import dcc
from tpDcc.libs.python import python

from tpDcc.libs.datalibrary.core import consts, exceptions

logger = logging.getLogger(consts.LIB_ID)


class Node(object):

    @classmethod
    def ls(cls, objects=None, selection=False):
        if objects is None and not selection:
            objects = dcc.client().all_scene_nodes(full_path=False)
        else:
            objects = objects or list()
            if selection:
                objects.extend(dcc.client().selected_nodes(full_path=False) or [])

        return [cls(name) for name in objects]

    def __init__(self, name, attributes=None):
        try:
            self._name = name.encode('ascii')
        except Exception:
            raise Exception('Not a valid ASCII name "{}".'.format(name))

        self._short_name = None
        self._namespace = None
        self._mirror_axis = None
        self._attributes = attributes

    def __str__(self):
        return self.name()

    def name(self):
        try:
            return self._name.decode()
        except AttributeError:
            return self._name

    def attributes(self):
        return self._attributes

    def short_name(self):
        if self._short_name is None:
            self._short_name = self.name().split('|')[-1]
        return str(self._short_name)

    def to_short_name(self):
        names = dcc.client().list_nodes(node_name=self.short_name(), full_path=False) or list()
        if len(names) == 1:
            return Node(names[0])
        elif len(names) > 1:
            raise exceptions.MoreThanOneObjectFoundError('More than one object found {}'.format(str(names)))
        else:
            raise exceptions.NoObjectFoundError('No object found {}'.format(self.short_name()))

    def namespace(self):
        if self._namespace is None:
            self._namespace = ':'.join(self.short_name().split(':')[:-1])
        return self._namespace

    def strip_first_pipe(self):
        if self.name().startswith('|'):
            self._name = self.name()[1:]

    def exists(self):
        return dcc.client().node_exists(self.name())

    def is_long(self):
        return '|' in self.name()

    def is_referenced(self):
        return dcc.client().node_is_referenced(self.name())

    def set_mirror_axis(self, mirror_axis):
        """
        Sets node mirror axis
        :param mirror_axis: list(int)
        """

        self._mirror_axis = mirror_axis

    def set_namespace(self, namespace):
        """
        Sets namespace for current node
        :param namespace: str
        """

        new_name = self.name()
        old_name = self.name()

        new_namespace = namespace
        old_namespace = self.namespace()

        if new_namespace == old_namespace:
            return self.name()

        if old_namespace and new_namespace:
            new_name = old_name.replace(old_namespace + ":", new_namespace + ":")
        elif old_namespace and not new_namespace:
            new_name = old_name.replace(old_namespace + ":", "")
        elif not old_namespace and new_namespace:
            new_name = old_name.replace("|", "|" + new_namespace + ":")
            if new_namespace and not new_name.startswith("|"):
                new_name = new_namespace + ":" + new_name

        self._name = new_name

        self._short_name = None
        self._namespace = None

        return self.name()


class Attribute(object):
    def __init__(self, name, attr=None, value=None, type=None, cache=True):
        if '.' in name:
            name, attr = name.split('.')
        if attr is None:
            raise AttributeError('Cannot initialize attribute instance without a given attribute.')

        try:
            self._name = name.encode('ascii')
            self._attr = attr.encode('ascii')
        except UnicodeEncodeError:
            raise UnicodeEncodeError('Not a valid ASCII name "{}.{}"'.format(name, attr))

        self._type = type
        self._value = value
        self._cache = cache
        self._full_name = None

    def __str__(self):
        return str(self.to_dict())

    # =================================================================================================================
    # PROPERTIES
    # =================================================================================================================

    @property
    def name(self):
        """
        Returns the maya object name for the attribute
        :return: str
        """

        return self._name

    @property
    def attr(self):
        """
        Returns the attribute name
        :return: str
        """

        return self._attr

    @property
    def fullname(self):
        """
        Returns the full name (node.attribute) of the node attribute
        :return: str
        """

        if self._full_name is None:
            self._full_name = '{}.{}'.format(self.name, self.attr)

        return self._full_name

    @property
    def type(self):
        """
        Returns the type of data currently in the attribute
        :return: str
        """

        if self._type is None:
            try:
                if dcc.client().attribute_exists(self.name, self.attr):
                    self._type = dcc.client().get_attribute_type(self.name, self.attr)
                    if self._type:
                        self._type = self._type.encode('ascii')
            except Exception:
                logger.exception('Cannot get attribute type for "{}'.format(self.fullname))

        return self._type

    @property
    def value(self):
        if self._value is None or not self._cache:
            try:
                self._value = dcc.client().get_attribute_value(self.name, self.attr)
            except Exception:
                logger.exception('Cannot get attribute value for "{}'.format(self.fullname))

        return self._value

    # =================================================================================================================
    # BASE
    # =================================================================================================================

    def to_dict(self):
        """
        Returns a dictionary of the attribute object
        :return: dict
        """

        result = {
            'type': self.type,
            'value': self.value,
            'fullname': self.fullname
        }

        return result

    def exists(self):
        """
        Returns whether or not node with attribute exists in current scene
        :return: bool
        """

        return dcc.attribute_exists(self.name, self.attr)

    def is_valid(self):
        """
        Returns True if the attribute type is valid; False otherwise.
        :return: bool
        """

        return self.type in dcc.client().get_valid_attribute_types()

    def is_locked(self):
        """
        Returns True if the attribute is locked; False otherwise.
        :return: bool
        """

        return dcc.client().is_attribute_locked(self.name, self.attr)

    def is_unlocked(self):
        """
        Returns True if the attribute is unlocked; False otherwise.
        :return: bool
        """

        return not self.is_locked()

    def is_connected(self, ignore_connections=None):
        """
        Returns True if the attribute is connected; False otherwise.
        :param ignore_connections: list(str) or None
        :return: bool
        """

        ignore_connections = python.force_list(ignore_connections)
        try:
            connection = dcc.list_connections(self.name, self.attr, destination=False)
        except ValueError:
            return False

        if not connection:
            return False

        if ignore_connections:
            connection_type = dcc.node_type(connection)
            for ignore_type in ignore_connections:
                if connection_type.startswith(ignore_type):
                    return False

        return True

    def is_blendable(self):
        """
        Returns True if the attribute can be blended; False otherwise.
        :return: bool
        """

        return self.type in dcc.get_valid_blendable_attribute_types()

    def is_settable(self, valid_connections=None):
        """
        Returns True if the attribute can be set; False otherwise.
        :param valid_connections: list(str) or None
        """

        valid_connections = python.force_list(valid_connections)
        if not self.exists():
            return False

        if not dcc.list_attributes(self.fullname, unlocked=True, keyable=True, multi=True, scalar=True):
            return False

        connection = dcc.list_connections(self.name, self.attr, destination=False)
        if connection:
            connection_type = dcc.node_type(connection)
            for valid_type in valid_connections:
                if connection_type.startswith(valid_type):
                    return True
            return False

        return True

    def set(self, value, blend=100, key=False, clamp=True, additive=False):
        """
        Sets the value for the given attribute
        :param value: float or str or list
        :param blend: int
        :param key: bool
        :param clamp: bool
        :param additive: bool
        """

        try:
            if additive and self.type != 'bool':
                if self.attr.startswith('scale'):
                    value = self.value * (1 + (value - 1) * (blend / 100.0))
                else:
                    value = self.value + value * (blend / 100.0)
            elif int(blend) == 0:
                value = self.value
            else:
                value = (value - self.value) * (blend / 100.0)
                value = self.value + value
        except TypeError as exc:
            logger.warning('Cannot blend or add attribute "{}" | {}'.format(self.fullname, exc))

        try:
            if self.type in ['string']:
                dcc.set_attribute_value(self.name, self.attr, value)
            elif self.type in ['list', 'matrix']:
                dcc.set_attribute_value(self.name, self.attr, *value)
            else:
                dcc.set_attribute_value(self.name, self.attr, value, clamp=clamp)
        except (ValueError, RuntimeError) as exc:
            logger.warning('Cannot set attribute "{}" | {}'.format(self.fullname, exc))

        try:
            if key:
                self.set_keyframe(value=value)
        except TypeError as exc:
            logger.warning('Cannot key attribute "{}" | {}'.format(self.fullname, exc))

    def set_keyframe(self, value, respect_keyable=True, **kwargs):
        """
        Sets a keyframe with the given value
        :param value:object
        :param respect_keyable: bool
        :param kwargs:dict
        """

        if dcc.get_minimum_attribute_value_exists(self.name, self.attr):
            minimum = dcc.get_minimum_float_attribute_value(self.name, self.attr)
            if value < minimum:
                value = minimum

        if dcc.get_maximum_attribute_value_exists(self.name, self.attr):
            maximum = dcc.get_maximum_float_attribute_value(self.name, self.attr)
            if value > maximum:
                value = maximum

        kwargs.setdefault('value', value)
        kwargs.setdefault('respectKeyable', respect_keyable)

        dcc.set_keyframe(self.name, self.attr, **kwargs)

    def clear_cache(self):
        """
        Clears all cached values
        """

        self._type = None
        self._value = None


def group_objects(objects):
    """
    Group objects as Nodes
    :param objects: list(str)
    :return: dict
    """

    results = dict()
    for name in objects:
        node = Node(name)
        results.setdefault(node.namespace(), list())
        results[node.namespace()].append(name)

    return results


def get_reference_paths(objects, without_copy_number=False):
    """
    Returns the reference paths for the given objects
    :param objects: list(str)
    :param without_copy_number: bool
    :return: list(str)
    """

    paths = list()
    for obj in objects:
        if dcc.client().node_is_referenced(obj):
            paths.append(dcc.client().node_reference_path(obj, without_copy_number=without_copy_number))

    return list(set(paths))


def get_reference_data(objects):
    """
    Returns the reference paths for the given objects
    :param objects: list(str)
    :return: list(dict)
    """

    data = list()
    paths = get_reference_paths(objects)
    for path in paths:
        data.append({
            'filename': path,
            'unresolved': dcc.client().node_reference_path(path, without_copy_number=True),
            'namespace': dcc.client().node_namespace(path),
            'node': dcc.client().node_is_referenced(path)
        })

    return data


def index_objects(objects):
    """
    :param objects: list(str)
    :return: dict
    """

    result = dict()
    if objects:
        for name in objects:
            node = Node(name)
            result.setdefault(node.short_name(), list())
            result[node.short_name()].append(node)

    return result


def match_in_index(node, index):
    """
    :param node: str
    :param index: int
    :return: Node
    """

    result = None
    if node.short_name() in index:
        nodes = index[node.short_name()]
        if nodes:
            for node_found in nodes:
                if node.name().endswith(node_found.name()) or node_found.name().endswith(node.name()):
                    result = node_found
                    break
            if result is not None:
                index[node.short_name()].remove(result)

    return result


def match_names(source_objects, target_objects=None, target_namespaces=None, search=None, replace=None):
    """
    :param source_objects: list(str)
    :param target_objects: list(str)
    :param target_namespaces: list(str)
    :param search: str
    :param replace: str
    :return: list(Node, Node)
    """

    # To avoid cyclic ipmorts
    from tpDcc.libs.datalibrary.dccs.maya.core import mirrortable

    def _rotate_sequence(sequence, current):
        n = len(sequence)
        for num in range(n):
            yield sequence[(num + current) % n]

    results = list()
    target_objects = python.force_list(target_objects)
    target_namespaces = python.force_list(target_namespaces)

    source_group = group_objects(source_objects)
    source_namespaces = source_group.keys()

    if not target_objects and not target_namespaces:
        target_namespaces = source_namespaces
    if not target_namespaces and target_objects:
        target_group = group_objects(target_objects)
        target_namespaces = target_group.keys()

    target_index = index_objects(target_objects)
    target_namespaces2 = list(set(target_namespaces) - set(source_namespaces))      # Target ns not in source objects
    target_namespaces1 = list(set(target_namespaces) - set(target_namespaces2))     # Target ns in source objects

    used_namespaces = list()
    not_used_namespaces = list()

    # Loop through all target namespaces in source objects
    for source_namespace in source_namespaces:
        if source_namespace in target_namespaces1:
            used_namespaces.append(source_namespace)
            for name in source_group[source_namespace]:
                source_node = Node(name)
                if search is not None and replace is not None:
                    name = mirrortable.MayaMirrorTable.replace(name, search, replace)
                target_node = Node(name)
                if target_objects:
                    target_node = match_in_index(target_node, target_index)
                if target_node:
                    results.append((source_node, target_node))
                    yield (source_node, target_node)
                else:
                    logger.debug('Cannot find matching target object for "{}"'.format(source_node.name()))
        else:
            not_used_namespaces.append(source_namespace)

    # Loop through all other target namespaces
    source_namespaces = not_used_namespaces
    source_namespaces.extend(used_namespaces)
    index = 0
    for target_namespace in target_namespaces2:
        match = False
        i = index
        for source_namespace in _rotate_sequence(source_namespaces, index):
            if match:
                index = i
                break
            i += 1
            for name in source_group[source_namespace]:
                source_node = Node(name)
                target_node = Node(name)
                target_node.set_namespace(target_namespace)
                if target_objects:
                    target_node = match_in_index(target_node, target_index)

                if target_node:
                    match = True
                    results.append((source_node, target_node))
                    yield (source_node, target_node)
                else:
                    logger.debug('Cannot find matching target object for "{}"'.format(source_node.name()))

    for target_nodes in target_index.values():
        for target_node in target_nodes:
            logger.debug('Cannot find matching source object for {}'.format(target_node.name()))
