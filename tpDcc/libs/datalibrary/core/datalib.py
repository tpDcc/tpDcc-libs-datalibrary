#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Customizable and easy to use data library
"""

from __future__ import print_function, division, absolute_import

import os
import time
import copy
import logging
from collections import OrderedDict

from Qt.QtCore import Signal, QObject

from tpDcc import dcc
from tpDcc.managers import configs
from tpDcc.libs.python import python, modules, path as path_utils

from tpDcc.libs.datalibrary.core import consts, utils, factory
from tpDcc.libs.datalibrary.managers import data

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class DataLibrary(QObject):

    Fields = [
        {
            "name": "icon",
            "sortable": False,
            "groupable": False,
        },
        {
            "name": "name",
            "sortable": True,
            "groupable": False,
        },
        {
            "name": "path",
            "sortable": True,
            "groupable": False,
        },
        {
            "name": "type",
            "sortable": True,
            "groupable": True,
        },
        {
            "name": "folder",
            "sortable": True,
            "groupable": False,
        },
        {
            "name": "category",
            "sortable": True,
            "groupable": True,
        },
        {
            "name": "modified",
            "sortable": True,
            "groupable": False,
        },
        {
            "name": "Custom Order",
            "sortable": True,
            "groupable": False,
        },
    ]

    dataChanged = Signal()
    searchStarted = Signal()
    searchFinished = Signal()
    searchTimeFinished = Signal()

    def __init__(self, path=None, library_window=None, items_factory=None, *args):
        super(DataLibrary, self).__init__(*args)

        self._path = path
        self._mtime = None
        self._data = dict()
        self._items = list()
        self._fields = list()
        self._sort_by = list()
        self._group_by = list()
        self._results = list()
        self._grouped_results = dict()
        self._queries = dict()
        self._global_queries = dict()
        self._search_time = 0
        self._search_enabled = True
        self._library_window = library_window
        self._factory = items_factory or factory.ItemsFactory()

        self.set_path(path)
        self.set_dirty(True)

    # =================================================================================================================
    # BASE
    # =================================================================================================================

    def path(self):
        """
        Returns the path where library is located
        :return: str
        """

        return self._path

    def set_path(self, value):
        """
         Sets path where muscle data is located
         :param value: str
         """

        self._path = value

    def add_paths(self, paths, data=None):
        """
        Adds the give npath and data to the database
        :param paths: list(str)
        :param data: dict or None
        """

        data = data or dict()
        self.update_paths(paths, data)

    def update_paths(self, paths, data):
        """
        Updates the given paths with the given data in the database
        :param paths: list(str)
        :param data: dict
        """

        current_data = self._read()
        paths = path_utils.normalize_paths(paths)
        for path in paths:
            if path in current_data:
                current_data[path].update(data)
            else:
                current_data[path] = data

        self._save(current_data)

    def rename_path(self, source, target):
        """
        Renames the source path to the given name
        :param source: str
        :param target: str
        :return: str
        """

        utils.rename_path_in_file(self.database_path(), source, target)
        self.set_dirty(True)

        return target

    def remove_path(self, path):
        """
        Removes the given path from the database
        :param path: str
        """

        self.remove_paths([path])

    def remove_paths(self, paths):
        """
        Removes the given paths from the database
        :param paths: list(str)
        """

        data = self._read()
        paths = path_utils.normalize_paths(paths)
        for path in paths:
            if path in data:
                del data[path]

        self._save(data)

    def database_path(self):
        """
        Returns path where library data base is located
        :return: str
        """

        datalib_path = None
        datalib_config = configs.get_library_config('tpDcc-libs-datalibrary')
        if datalib_config:
            datalib_path = datalib_config.get('database_path')
            if datalib_path:
                datalib_path = utils.format_path(datalib_path, self.path())
        if not datalib_path:
            datalib_path = path_utils.join_path(path_utils.get_user_data_dir('dataLibrary'), 'data.db')

        return path_utils.clean_path(datalib_path)

    def library_window(self):
        """
        Returns library window this library is attached into
        :return:
        """

        return self._library_window

    def is_dirty(self):
        """
        Returns whether the data has changed on disk or not
        :return: bool
        """

        return not self._items or self._mtime != self._get_mtime()

    def set_dirty(self, value):
        """
        Updates the model object with the current data timestamp
        :param value: bool
        """

        if value:
            self._mtime = None
        else:
            self._mtime = self._get_mtime()

    def recursive_depth(self):
        """
        Return the recursive search depth
        :return: int
        """

        recursive_steps = consts.DEFAULT_RECURSIVE_DEPTH
        datalib_config = configs.get_library_config('tpDcc-libs-datalibrary')
        if datalib_config:
            recursive_steps = datalib_config.get('recursive_search_depth')

        return recursive_steps

    def item_class_from_data_type(self, data_type, **kwargs):
        """
        Returns data instance class from the given data type
        :param data_type: str
        :param kwargs:
        :return: variant
        """

        package_name = kwargs.pop('package_name', None)
        do_reload = kwargs.pop('do_reload', False)

        for item_class in data.get_all_data_items(package_name=package_name, do_reload=do_reload):
            if item_class.DATA_TYPE == data_type:
                return item_class

        return None

    def item_from_path(self, path, **kwargs):
        """
        Returns a new data item instance from the given path
        :param path: str
        :param kwargs:
        :return:
        """

        path = path_utils.clean_path(path)

        data_type = kwargs.pop('data_type', None)
        item_data = kwargs.pop('data', None)
        package_name = kwargs.pop('package_name', None)
        do_reload = kwargs.pop('do_reload', False)
        for item_class in data.get_all_data_items(package_name=package_name, do_reload=do_reload):
            if item_class.match(path):
                return factory.ItemsFactory().create_item(item_class, path=path, data=item_data, library=self)
            if data_type:
                if item_class.match_type(data_type):
                    return factory.ItemsFactory().create_item(item_class, path=path, data=item_data, library=self)

    def items_from_paths(self, paths, **kwargs):
        """
        Returns new instances for the given paths
        :param paths: list(str)
        :param kwargs:
        :return:
        """

        for path in paths:
            item = self.item_from_path(path, **kwargs)
            if item:
                yield item

    def items_from_urls(self, urls, **kwargs):
        """
        Returns new item instances for the given QUrl objects
        :param urls: list(QUrl)
        :param kwargs:
        :return:
        """

        items = list()
        for path in utils.paths_from_urls(urls):
            item = self.item_from_path(path, **kwargs)
            if item:
                data = item.create_item_data()
                item.set_item_data(data)
            else:
                LOGGER.warning('Cannot find the item for path "{}"'.format(path))

        return items

    def sync(self, progress_callback=lambda message, percent: None):
        """
        Sync the file sytem wit hthe library data
        """

        if not self.path():
            LOGGER.warning('No path set for syncing data')
            return

        if progress_callback:
            progress_callback('Syncing')

        new_item_data = dict()
        old_item_data = self._read()
        items = list(self._walker(self.path()))
        count = len(items)

        for i, item in enumerate(items):
            percent = (float(i + 1) / float(count))
            if progress_callback:
                percent *= 100
                label = '{0:.0f}%'.format(percent)
                progress_callback(label, percent)
            path = item.get('path')
            new_item_data[path] = old_item_data.get(path, dict())
            new_item_data[path].update(item)

        if progress_callback:
            progress_callback('Post Callbacks')

        self._post_sync(new_item_data)

        if progress_callback:
            progress_callback('Saving Cache')

        self._save(new_item_data)

        self.dataChanged.emit()

    def clear(self):
        """
        Clears all the library data
        """

        self._items = list()
        self._results = list()
        self._grouped_results = list()
        self.dataChanged.emit()

    # =================================================================================================================
    # CREATE
    # =================================================================================================================

    def create_folder(self, folder_name, folder_directory):

        data_folder_class = self.item_class_from_data_type(data_type='folder')
        folder_path = path_utils.join_path(folder_directory, folder_name)
        folder_item = self._factory.create_item(data_folder_class, folder_path, {}, self)
        valid_save = folder_item.safe_save()
        if not valid_save:
            return None

        self.add_item(folder_item)

        return folder_item

    # =================================================================================================================
    # SEARCH
    # =================================================================================================================

    def is_search_enabled(self):
        """
        Returns whether search functionality is enabled or not
        :return: bool
        """

        return self._search_enabled

    def set_search_enabled(self, flag):
        """
        Sets whether search functionality is enabled or not
        :param flag: bool
        """

        self._search_enabled = flag

    def search(self):
        """
        Run a search using the queries added to library data
        """

        if not self.is_search_enabled():
            return

        start_time = time.time()
        LOGGER.debug('Searching items ...')
        self.searchStarted.emit()
        self._results = self.find_items(self.queries())
        self._grouped_results = self.group_items(self._results, self.group_by())
        self.searchFinished.emit()
        self._search_time = time.time() - start_time
        self.searchTimeFinished.emit()
        LOGGER.debug('Search time: {}'.format(self._search_time))

    def sort_by(self):
        """
        Return the list of fields to sorty by
        :return: list(str)
        """

        return self._sort_by

    def set_sort_by(self, fields):
        """
        Set the list of fields to group by
        >>> set_sorty_by(['name:asc', 'type:asc'])
        :param fields: list(str)
        """

        self._sort_by = fields

    def group_by(self):
        """
        Return the list of fields to group by
        :return: list(str)
        """

        return self._group_by

    def set_group_by(self, fields):
        """
        Set the list of fields to group by
        >>> set_group_by(['name:asc', 'type:asc'])
        :param fields: list(str)
        """

        self._group_by = fields

    def fields(self):
        """
        Returns all the fields for the library
        :return: list(str)
        """

        return self.Fields

    def field_names(self):
        """
        Returns all field names for the library
        :return: list(str)
        """

        return [field['name'] for field in self.fields()]

    def queries(self, exclude=None):
        """
        Return all queries for the data base excluding the given ones
        :param exclude: list(str) or None
        :return: list(dict)
        """

        queries = list()
        exclude = exclude or list()

        for query in self._queries.values():
            if query.get('name') not in exclude:
                queries.append(query)

        return queries

    def query_exists(self, name):
        """
        Check if the given query name exists
        :param name: str
        :return: bool
        """

        return name in self._queries

    def add_global_query(self, query):
        """
        Add a global query to library
        :param query: dict
        """

        self._global_queries[query['name']] = query

    def add_query(self, query):
        """
        Add a search query to the library
        >>> add_query({
        >>>    'name': 'Test Query',
        >>>    'operator': 'or',
        >>>    'filters': [
        >>>        ('folder', 'is', '/lib/proj/test'),
        >>>        ('folder', 'startswith', '/lib/proj/test'),
        >>>    ]
        >>>})
        :param query: dict
        """

        self._queries[query['name']] = query

    def remove_query(self, name):
        """
        Remove the query with the given name
        :param name: str
        """

        if name in self._queries:
            del self._queries[name]

    def distinct(self, field, queries=None, sort_by='name'):
        """
        Returns all values for the given field
        :param field: str
        :param queries: variant, None or list(dict)
        :param sort_by: str
        :return: list
        """

        results = dict()
        queries = queries or list()
        queries.extend(self._global_queries.values())

        items = self.create_items() or list()
        for item in items:
            value = item.item_data().get(field)
            if value:
                results.setdefault(value, {'count': 0, 'name': value})
                match = self.match(item.item_data(), queries)
                if match:
                    results[value]['count'] += 1

        def sort_key(facet):
            return facet.get(sort_by)

        return sorted(list(results.values()), key=sort_key)

    def registered_items(self):
        """
        Returns registered data items
        :return: list(LibraryDataItem)
        """

        return data.get_all_data_items()

    def create_items(self):
        """
        Create all teh items for the library model
        :return: list(LibraryItem)
        """

        # TODO: Item creation should be managed outside of this class

        if not self.is_dirty():
            return self._items

        self._items = list()
        data_found = self._read()
        modules_found = list()
        for item_data in list(data_found.values()):
            if '__class__' in item_data:
                modules_found.append(item_data.get('__class__'))
        modules_found = set(modules_found)

        classes = dict()
        for module in modules_found:
            imported_module = modules.resolve_module(module, log_error=True)
            if not imported_module:
                LOGGER.warning('Impossible to import data library item: "{}"'.format(module))
                continue
            classes[module] = imported_module

        for path in list(data_found.keys()):
            module = data_found[path].get('__class__')
            item_class = classes.get(module)
            if item_class and self.item_is_supported_in_current_dcc(item_class):
                # item_view = self._factory.create_view(item_class, path, data_found[path], self, self._library_window)
                item = self._factory.create_item(item_class, path, data_found[path], self)
                self._items.append(item)

        return self._items

    def item_is_supported_in_current_dcc(self, item):
        """
        Returns whether or not given item is supported in current DCC
        :param item: class or DataItem instance
        :return: bool
        """

        if not item.SUPPORTED_DCCS:
            return True

        current_dcc = dcc.client().get_name()
        if current_dcc not in item.SUPPORTED_DCCS:
            return False

        return True

    def add_item(self, item):
        """
        Add the given item to the library data
        :param item: LibraryItem
        """

        self.save_item_data([item])

    def add_items(self, items):
        """
        Add the given items to the library data
        :param items: list(LibraryItem)
        """

        self.save_item_data(items)

    def save_item_data(self, items, emit_data_changed=True):
        """
        Add the given items to the library data
        :param items: list(LibraryItem)
        :param emit_data_changed: bool
        """

        LOGGER.debug('Saving Items: {}'.format(items))

        current_data = self._read()
        for item in items:
            path = item.path
            item_data = item.data
            current_data.setdefault(path, dict())
            current_data[path].update(item_data)

        self._save(current_data)

        if emit_data_changed:
            self.search()
            self.dataChanged.emit()

    def find_items(self, queries):
        """
        Get the items that match the given queries
        :param queries: list(dict)
        :return: list(LibraryItem)
        """

        fields = list()
        results = list()

        queries = copy.copy(queries)
        queries.extend(self._global_queries.values())

        items = self.create_items() or list()
        for item in items:
            match = self.match(item.data, queries)
            if match:
                results.append(item)
            fields.extend(list(item.data.keys()))

        self._fields = list(set(fields))

        if self.sort_by():
            results = self.sorted(results, self.sort_by())

        return results

    def find_items_views(self, queries):
        """
        Get the item views that match the given queries
        :param queries: list(dict)
        :return: list(LibraryItem)
        """

        items = self.find_items(queries)
        if not items:
            return items

        item_views = list()
        for item in items:
            item_view = factory.ItemsFactory().create_view_from_item(item)
            if not item_view:
                continue
            item_views.append(item_view)

        return item_views

    def results(self):
        """
        Return the items found after a search is executed
        :return: list(LibraryItem)
        """

        return self._results

    def grouped_results(self):
        """
        Return the results grouped after a search is executed
        :return: dict
        """

        return self._grouped_results

    def search_time(self):
        """
        Return the time taken to run a search
        :return: float
        """

        return self._search_time

    # =================================================================================================================
    # STATIC FUNCTIONS
    # =================================================================================================================

    @staticmethod
    def match(data, queries):
        """
        Matches the given data with the given queries
        :param data: dict
        :param queries: list(dict)
        :return: list
        """

        matches = list()

        for query in queries:
            filters = query.get('filters')
            operator = query.get('operator', 'and')
            if not filters:
                continue

            match = False
            for key, cond, value in filters:
                if key == '*':
                    item_value = str(data)
                else:
                    item_value = data.get(key)

                if python.is_string(value):
                    value = value.lower()
                if python.is_string(item_value):
                    item_value = item_value.lower()
                if not item_value:
                    match = False
                elif cond == 'contains':
                    match = value in item_value
                elif cond == 'not_contains':
                    match = value not in item_value
                elif cond == 'is':
                    match = value == item_value
                elif cond == 'not':
                    match = value != item_value
                elif cond == 'startswith':
                    match = item_value.startswith(value)
                elif cond == 'endswith':
                    match = item_value.endswith(value)

                if operator == 'or' and match:
                    break
                if operator == 'and' and not match:
                    break

            matches.append(match)

        return all(matches)

    @staticmethod
    def sorted(items, sort_by):
        """
        Return the given data sorted using the sort by argument
        data = [
                {'name':'a', 'index':1},
                {'name':'b', 'index':2},
                {'name':'c', 'index':3},
            ]
        sortBy = ['index:asc', 'name']
        :param items: list(LibraryItem)
        :param sort_by: list(str)
        :return: list(LibraryItem)
        """

        LOGGER.debug('Sort by: {}'.format(sort_by))
        start_time = time.time()
        for field in reversed(sort_by):
            tokens = field.split(':')
            reverse = False
            if len(tokens) > 1:
                field = tokens[0]
                reverse = tokens[1] != 'asc'

            def sort_key(item):
                default = False if reverse else ''
                if hasattr(item, 'item_data') and callable(item.item_data):
                    return item.item_data().get(field, default)
                else:
                    return item.get(field, default)

            items = sorted(items, key=sort_key, reverse=reverse)
        LOGGER.debug('Sort items took {}'.format(time.time() - start_time))

        return items

    @staticmethod
    def group_items(items, fields):
        """
        Group the given items by the given field
        :param items: list(LibraryItem)
        :param fields: list(str)
        :return: dict
        """

        LOGGER.debug('Group by: {}'.format(fields))

        # TODO: Implement support for multiple groups not only top level group

        if fields:
            field = fields[0]
        else:
            return {'None': items}

        start_time = time.time()
        results_ = dict()
        tokens = field.split(':')

        reverse = False
        if len(tokens) > 1:
            field = tokens[0]
            reverse = tokens[1] != 'asc'

        for item in items:
            value = item.item_data().get(field)
            if value:
                results_.setdefault(value, list())
                results_[value].append(item)

        groups = sorted(results_.keys(), reverse=reverse)

        results = OrderedDict()
        for group in groups:
            results[group] = results_[group]

        LOGGER.debug('Group Items Took {}'.format(time.time() - start_time))

        return results

    # =================================================================================================================
    # SETTINGS
    # =================================================================================================================

    def settings(self):
        """
        Returns the stetins for the data
        :return: dict
        """

        return {
            'sortBy': self.sort_by(),
            'groupBy': self.group_by()
        }

    def set_settings(self, settings):
        """
        Set the settings for the data
        :param settings: dict
        """

        value = settings.get('sortBy')
        if value is not None:
            self.set_sort_by(value)
        value = settings.get('groupBy')
        if value is not None:
            self.set_group_by(value)

    # =================================================================================================================
    # INTERNAL
    # =================================================================================================================

    def _get_mtime(self):
        """
        Internal function that returns when the data was last modified
        :return: float or None
        """

        path = self.database_path()
        mtime = None
        if os.path.exists(path):
            mtime = os.path.getmtime(path)

        return mtime

    def _is_valid_path(self, path):
        """
        Internal function taht returns whether or not given path should be ignored
        :param path: str
        :return: bool
        """

        if not path:
            return False

        ignore_paths = list()
        datalib_config = configs.get_library_config('tpDcc-libs-datalibrary')
        if datalib_config:
            ignore_paths = python.force_list(datalib_config.get('ignore_paths', default=ignore_paths))

        path = path_utils.clean_path(path)
        for ignore_path in ignore_paths:
            if path in path_utils.clean_path(ignore_path):
                return False

        return True

    def _walker(self, path):
        """
        Internal function that walks the given root path looking for valid items and returning the item data
        :param path: str
        """

        path = path_utils.clean_path(path)
        max_depth = self.recursive_depth()
        start_depth = path.count(os.path.sep)

        for root, dirs, files in os.walk(path, followlinks=True):

            files.extend(dirs)

            for file_name in files:
                path = path_utils.join_path(root, file_name)
                if not self._is_valid_path(path):
                    continue
                item = self.item_from_path(path)
                remove = False
                if item:
                    yield item.create_item_data()
                    if not item.ENABLE_NESTED_ITEMS:
                        remove = True
                if remove and file_name in dirs:
                    dirs.remove(file_name)

            if max_depth == 1:
                break

            current_depth = root.count(os.path.sep)
            if (current_depth - start_depth) >= max_depth:
                del dirs[:]

    def _post_sync(self, item_data):
        """
        Internal function that executed once the library items data have been synced
        Override to implement custom functionality
        :param item_data: dict
        """

        pass

    def _read(self):
        """
        Internal function that reads the data from disk and returns it a dictionary object
        :return: dict
        """

        if not self.path():
            LOGGER.info('No path set for reading the data from disk')
            return self._data

        if not self.is_dirty():
            return self._data

        self._data = utils.read_json(self.database_path())
        self.set_dirty(False)

        return self._data

    def _save(self, data):
        """
        Internal function that writes the given data dict object to the data on disk
        :param data: dict
        """

        if not self.path():
            LOGGER.info('No path set for saving the data to disk')
            return

        utils.save_json(self.database_path(), data)
        self.set_dirty(True)

    def _clear(self):
        """
        Internal function that clears all the item data
        """

        self._items = list()
        self._results = list()
        self._grouped_results = dict()
        self.dataChanged.emit()
