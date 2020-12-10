#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains utils functions used by data library in Maya
"""

from __future__ import print_function, division, absolute_import

import logging

from tpDcc import dcc
from tpDcc.libs.python import python

from tpDcc.libs.datalibrary.core import exceptions

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


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
        return dcc.node_is_referenced(self.name())

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

    # To avoid cycle imports
    from tpDcc.libs.datalibrary.dccs.maya.data import mirrortable

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
                    LOGGER.debug('Cannot find matching target object for "{}"'.format(source_node.name()))
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
                    LOGGER.debug('Cannot find matching target object for "{}"'.format(source_node.name()))

    for target_nodes in target_index.values():
        for target_node in target_nodes:
            LOGGER.debug('Cannot find matching source object for {}'.format(target_node.name()))
