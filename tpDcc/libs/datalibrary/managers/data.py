#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains data manager implementation
"""

from __future__ import print_function, division, absolute_import

import inspect
import logging
import pkgutil
import importlib

from tpDcc.libs.python import python, modules, path as path_utils

from tpDcc.libs.datalibrary.core import data, dataitem
from tpDcc.libs.datalibrary.data import scripts

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


_REGISTERED_DIRECTORIES = python.UniqueDict()
_LOADED_DATA_CLASSES = python.UniqueDict()
_LOADED_DATA_ITEMS = python.UniqueDict()

_LOADED_DATA_CLASSES.setdefault('tpDcc', python.UniqueDict())
_LOADED_DATA_ITEMS.setdefault('tpDcc', python.UniqueDict())

_STANDARD_DATA_CLASSES = {
    scripts.ScriptManifestData.get_data_type(): scripts.ScriptManifestData,
    scripts.ScriptPythonData.get_data_type(): scripts.ScriptPythonData
}


def add_directory(directory, package_name=None, do_reload=True):
    """
    Adds a new directory where data should be find
    :param directory: str
    :param package_name: str
    :param do_reload: bool
    """

    if not directory or not path_utils.is_dir(directory):
        return

    package_name = package_name or 'tpDcc'

    clean_directory = path_utils.clean_path(directory)

    _REGISTERED_DIRECTORIES.setdefault(package_name, set())
    if clean_directory not in _REGISTERED_DIRECTORIES[package_name]:
        _REGISTERED_DIRECTORIES[package_name].add(directory)
        update_data_classes(package_name=package_name, do_reload=do_reload)
        update_data_items(package_name=package_name, do_reload=do_reload)


def get_all_data_classes(package_name=None, do_reload=False):
    """
    Returns all data classes loaded by the manager
    :return: list<DataWidget>
    """

    return update_data_classes(package_name=package_name, do_reload=do_reload)


def get_all_data_items(package_name=None, do_reload=False):
    """
    Returns all data classes loaded by the manager
    :return: list<DataWidget>
    """

    return update_data_items(package_name=package_name, do_reload=do_reload)


def update_data_classes(package_name=None, do_reload=False):
    """
    Updates all data classes available in the registered data paths
    :param package_name: str or None
    :param do_reload: bool
    :return: set(classes)
    """

    return_all_package_classes = False
    if not package_name:
        package_name = 'tpDcc'
        return_all_package_classes = True

    if not _LOADED_DATA_ITEMS or package_name not in _LOADED_DATA_ITEMS or do_reload:
        _LOADED_DATA_CLASSES.setdefault(package_name, python.UniqueDict())
        for pkg_name, directories in _REGISTERED_DIRECTORIES.items():
            if package_name and package_name != pkg_name:
                continue
            for directory in directories:
                _LOADED_DATA_CLASSES[package_name].update(_load_data_classes(directory))

    if return_all_package_classes:
        all_classes = dict()
        for classes_list in list(_LOADED_DATA_CLASSES.values()):
            all_classes.update(classes_list)
        return all_classes

    return _LOADED_DATA_CLASSES[package_name]


def update_data_items(package_name=None, do_reload=False):
    """
    Updates all data items available in the registered data paths
    :param package_name: str or None
    :param do_reload: bool
    :return: set(classes)
    """

    return_all_package_classes = False
    if not package_name:
        package_name = 'tpDcc'
        return_all_package_classes = True

    if not _LOADED_DATA_ITEMS or package_name not in _LOADED_DATA_ITEMS or do_reload:
        _LOADED_DATA_ITEMS.setdefault(package_name, python.UniqueDict())
        for pkg_name, directories in _REGISTERED_DIRECTORIES.items():
            if package_name and package_name != pkg_name:
                continue
            for directory in directories:
                _LOADED_DATA_ITEMS[pkg_name].update(_load_data_items(directory))

    if return_all_package_classes:
        all_classes = dict()
        for classes_list in list(_LOADED_DATA_ITEMS.values()):
            all_classes.update(classes_list)
        return all_classes

    return _LOADED_DATA_ITEMS[package_name]


def _load_data_classes(directory):
    imported = python.UniqueDict()
    if not directory or not path_utils.is_dir(directory):
        return imported

    module_name = modules.convert_to_dotted_path(directory)

    for importer, sub_mod_name, is_pkg in pkgutil.walk_packages([directory]):
        import_path = '{}.{}'.format(module_name, sub_mod_name)
        module = importlib.import_module(import_path)
        # Important to allow inspect to retrieve classes from given module
        importer.find_module(sub_mod_name).load_module(sub_mod_name)
        for cname, obj_class in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj_class, data.Data):
                continue
            if not hasattr(obj_class, 'get_data_type'):
                LOGGER.warning(
                    'Impossible to register Data "{}" because not get_data_type function found!'.format(obj_class))
                continue
            data_type = obj_class.get_data_type()
            if not data_type:
                LOGGER.warning(
                    'Impossible to register Data "{}" because no data type defined!'.format(obj_class))
                continue
            imported[data_type] = obj_class

    return imported


def _load_data_items(directory):
    imported = python.UniqueDict()
    if not directory or not path_utils.is_dir(directory):
        return imported

    module_name = modules.convert_to_dotted_path(directory)

    for importer, sub_mod_name, is_pkg in pkgutil.walk_packages([directory]):
        import_path = '{}.{}'.format(module_name, sub_mod_name)
        module = importlib.import_module(import_path)
        # Important to allow inspect to retrieve classes from given module
        importer.find_module(sub_mod_name).load_module(sub_mod_name)
        for cname, obj_class in inspect.getmembers(module, inspect.isclass):
            if not issubclass(obj_class, dataitem.DataItem):
                continue
            if not hasattr(obj_class, 'DATA_TYPE') or not obj_class.DATA_TYPE:
                LOGGER.warning(
                    'Impossible to register Data Item "{}" because its DATA_TYPE attribute is not defined!'.format(
                        obj_class))
                continue
            imported[obj_class.DATA_TYPE] = obj_class

    return imported
