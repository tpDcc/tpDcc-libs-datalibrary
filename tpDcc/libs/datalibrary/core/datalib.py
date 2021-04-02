import os
import re
import sys
import time
import json
import copy
import locale
import getpass
import sqlite3
import logging
from collections import OrderedDict

import shortuuid

from tpDcc import dcc
from tpDcc.managers import configs
from tpDcc.libs.python import python, timedate, fileio, jsonio, signal, version, sqlite, modules
from tpDcc.libs.python import path as path_utils, contexts, decorators, folder as folder_utils
from tpDcc.libs.plugin.core import factory

from tpDcc.libs.datalibrary.core import consts, scanner, datapart

LOGGER = logging.getLogger(consts.LIB_ID)


class DataLibrary(object):

    SQL_COMMANDS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sql')

    def __init__(self, identifier, load_data_plugins_from_settings=True, relative_paths=True, thumbs_path=None):

        self.scanned = signal.Signal()
        self.syncCompleted = signal.Signal()
        self.searchStarted = signal.Signal()
        self.searchFinished = signal.Signal()
        self.dataChanged = signal.Signal()

        self._id = identifier
        self._relative_paths = relative_paths
        self._commands = self._get_commands_dict()

        self._fields = list()
        self._results = list()
        self._grouped_results = dict()
        self._queries = dict()
        self._global_queries = dict()
        self._search_time = 0
        self._search_enabled = True
        self._black_list = ['.git', '.gitattributes']

        plugin_locations = list()
        if os.path.exists(identifier):
            plugin_locations = self.plugin_locations()
        plugin_locations.extend(self.default_plugin_paths())
        plugin_locations = list(set(plugin_locations))

        self._scan_factory = factory.PluginFactory(scanner.BaseScanner, paths=plugin_locations, plugin_id='SCAN_TYPE')
        self._data_factory = factory.PluginFactory(datapart.DataPart, paths=plugin_locations, plugin_id='DATA_TYPE')

        if load_data_plugins_from_settings:
            self._register_data_plugins_classes_from_config()

        self._sort_data_plugins()

    # ============================================================================================================
    # PROPERTIES
    # ============================================================================================================

    @property
    def identifier(self):
        return self._id

    @property
    def data_factory(self):
        return self._data_factory

    # ============================================================================================================
    # STATIC FUNCTIONS
    # ============================================================================================================

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
                    match = str(item_value).startswith(value)
                elif cond == 'endswith':
                    match = str(item_value).endswith(value)

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
            if not item:
                continue

            # TODO: Maybe we should move this to a filter?
            # Skip items that start with '.'
            if item.name().startswith('.'):
                continue
            item_directory = item.data().get('directory', '')
            if item_directory:
                base_dir = os.path.basename(item_directory)
                if not base_dir == '.' and base_dir.startswith('.'):
                    continue

            value = item.data().get(field)
            if value:
                results_.setdefault(value, list())
                results_[value].append(item)

        groups = sorted(results_.keys(), reverse=reverse)

        results = OrderedDict()
        for group in groups:
            results[group] = results_[group]

        LOGGER.debug('Group Items Took {}'.format(time.time() - start_time))

        return results

    # ============================================================================================================
    # CLASS METHODS
    # ============================================================================================================

    @classmethod
    def default_plugin_paths(cls):

        return [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plugins'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dccs', dcc.client().get_name(), 'plugins'),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dccs', dcc.client().get_name(), 'data')
        ]

    @classmethod
    def create(cls, path, plugin_locations=None, load_data_plugins_from_settings=True):
        if not path.endswith('db'):
            path += '.db'

        data_lib = cls(path, load_data_plugins_from_settings)
        data_lib.init()

        plugin_locations = python.force_list(plugin_locations)
        plugin_locations.extend(cls.default_plugin_paths())
        plugin_locations = list(set(plugin_locations))
        for plugin_path in plugin_locations:
            if not os.path.isdir(plugin_path):
                continue
            data_lib.register_plugin_path(plugin_path)

        return data_lib

    @classmethod
    def load(cls, path, load_data_plugins_from_settings=True):
        """
        Loads the given data base and returns DataLib instance
        :param path: str, absolute path pointing to database file
        :param load_data_plugins_from_settings: bool
        :return: DataLib
        """

        return cls(path, load_data_plugins_from_settings)

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def init(self):
        """
        Initializes and creates data source
        """

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            self._execute(connection, 'create')

        # Call it, to force the creation of the thumbs folder if it does not exists
        self.get_thumbs_path()
        self.get_versions_path()
        self.get_metadata_path()
        self.get_dependencies_path()

        return True

    def get_identifier(self, identifier):
        """
        Returns proper item identifier depending of the path type (absolute or relative)
        :param identifier: str
        :return: str
        """

        return path_utils.clean_path(self._get_relative_identifier(identifier) if self._relative_paths else identifier)

    def format_identifier(self, identifier):
        """
        Internal function that returns identifier in the proper format
        :param identifier: str
        :return: str
        """

        if identifier.startswith('./'):
            identifier = identifier[2:]

        return path_utils.clean_path(
            os.path.join(self.get_directory(), identifier)) if self._relative_paths else identifier

    def get_uuid(self, identifier):
        return shortuuid.uuid(self.get_identifier(identifier))

    def get_all_uuids(self):
        with sqlite.ConnectionContext(self._id, get=True) as connection:
            self._execute(connection, 'find_all_uuids')

        return [result[0] for result in connection.results]

    def get_directory(self):
        """
        Returns root path directory where data library is located
        :return: str
        """

        return path_utils.clean_path(os.path.dirname(self._id))

    def add(self, identifier):
        """
        Adds data identifier into data base
        :param identifier: str, data identifier
        """

        identifier = self.get_identifier(identifier)
        full_identifier = self.format_identifier(identifier)

        field_names = self.field_names()

        with sqlite.ConnectionContext(self._id, commit=True) as connection:

            for scan_plugin in self._scan_factory.plugins():
                if not scan_plugin.can_represent(full_identifier):
                    continue

                field_values = list()
                scanned_fields = scan_plugin.fields(full_identifier)
                self._update_fields(full_identifier, scanned_fields)
                for field_name in field_names:
                    field_values.append('' if field_name not in scanned_fields else scanned_fields[field_name])
                field_values = ','.join(
                    "'{}'".format(field) if python.is_string(field) else "'{}'".format(field) for field in field_values)
                self._execute(
                    connection, 'add_with_fields', replacements={
                        '$(IDENTIFIER)': identifier,
                        '$(FIELDS)': ','.join(field_names), '$(FIELDS_VALUES)': field_values})

    # with sqlite.ConnectionContext(self._id, commit=True) as connection:
    #         self._execute(connection, 'add', replacements={'$(IDENTIFIER)': identifier})

    def rename(self, identifier, new_identifier):
        """
        Renames data
        :param identifier: str
        :param new_identifier: str
        :return:
        """

        identifier = self.get_identifier(identifier)
        new_identifier = self.get_identifier(new_identifier)

        current_uuid = self.find_uuid(identifier)
        if not current_uuid:
            return

        new_uuid = self.get_uuid(new_identifier)
        new_name = os.path.splitext(os.path.basename(new_identifier))[0]

        ctime = str(time.time()).split('.')[0]
        user = getpass.getuser()
        if user and python.is_python2():
            user.decode(locale.getpreferredencoding())
        modified = timedate.get_date_and_time()

        current_dependencies = self.get_dependencies(identifier, as_uuid=True)

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            self._execute(connection, 'rename', replacements={
                '$(IDENTIFIER)': identifier, '$(NEW_IDENTIFIER)': new_identifier, '$(NEW_UUID)': new_uuid,
                '$(NEW_NAME)': new_name, '$(USER)': user, '$(MODIFIED)': modified, '$(CTIME)': ctime})

        self.rename_metadata(current_uuid, new_uuid)
        self.rename_thumb(current_uuid, new_uuid)
        self.rename_version(current_uuid, new_uuid)
        self.rename_dependency(current_uuid, new_uuid, current_dependencies)

        self.dataChanged.emit()

    def move(self, identifier, new_identifier):
        """
        Moves data
        :param identifier: str
        :param new_identifier: str
        :return:
        """

        identifier = self.get_identifier(identifier)
        new_identifier = self.get_identifier(new_identifier)

        current_uuid = self.find_uuid(identifier)
        if not current_uuid:
            return

        new_uuid = self.get_uuid(new_identifier)
        new_directory = self.get_identifier(os.path.dirname(new_identifier))

        ctime = str(time.time()).split('.')[0]
        user = getpass.getuser()
        if user and python.is_python2():
            user.decode(locale.getpreferredencoding())
        modified = timedate.get_date_and_time()

        current_dependencies = self.get_dependencies(identifier, as_uuid=True)

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            self._execute(connection, 'move', replacements={
                '$(IDENTIFIER)': identifier, '$(NEW_IDENTIFIER)': new_identifier, '$(NEW_UUID)': new_uuid,
                '$(NEW_DIRECTORY)': new_directory, '$(USER)': user, '$(MODIFIED)': modified, '$(CTIME)': ctime})

        self.rename_metadata(current_uuid, new_uuid)
        self.rename_thumb(current_uuid, new_uuid)
        self.rename_version(current_uuid, new_uuid)
        self.rename_dependency(current_uuid, new_uuid, current_dependencies)

    def remove(self, identifier, recursive=True):
        """
        Removes data from data base
        :param identifier: str, dta identifier
        """

        uuids = list()
        removed_identifiers = list()
        identifiers = python.force_list(identifier)
        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            for identifier in identifiers:
                identifier = self.get_identifier(identifier)
                uuid = self.find_uuid(identifier)
                self._execute(connection, 'remove', replacements={'$(IDENTIFIER)': identifier})
                removed_identifiers.append(identifier)
                if uuid:
                    uuids.append(uuid)

        if removed_identifiers:
            self.dataChanged.emit()

        if uuids:
            self.delete_metadata(uuids)
            self.delete_thumb(uuids)
            self.delete_version(uuids)
            self.delete_dependencies(uuids, recursive=recursive)

        return removed_identifiers

    def skip_regexes(self):
        """
        Returns a list of regular expression strings stored withing the data base
        :return: list(str)
        """

        return self.settings().get('skip_regex', list())

    def add_skip_regex(self, pattern):
        """
        Stores givfen regex pattern into the data base. When a scan is initiated this regex will be picked up and omit
        locations containing this pattern
        :param pattern: str, string regex
        """

        settings = self.settings()
        key = 'skip_regex'
        settings[key] = settings.get(key, list()) + [self._clean_path(pattern)]

        self.save_settings(settings)

    def remove_skip_regex(self, pattern):
        """
        Removes given regex string pattern from the data base
        :param pattern: str, string regex
        """

        settings = self.settings()
        key = 'skip_regex'
        current_settings = settings.get(key, list())
        current_settings.remove(self._clean_path(pattern))
        settings[key] = current_settings
        self.save_settings(settings)

    def get(self, identifier, only_extension=False):
        """
        Returns a composite binding of a DataPart plugin, bringing together all the plugins which can viably
        represent this data
        :param identifier: data identifier to be passed to the DataPart
        :param only_extension: If True, only extensions will be checked during data composition
        :return: DataPart composite
        """

        template = None

        identifier = self.format_identifier(identifier)

        dcc_name = dcc.client().get_name()

        for data_plugin in self._data_plugins:

            if data_plugin.can_represent(identifier, only_extension=only_extension):

                # Skip data that are not supported in current DCC
                supported_dccs = data_plugin.supported_dccs()
                if supported_dccs:
                    if dcc_name not in supported_dccs:
                        break

                proper_identifier = self.get_identifier(identifier)
                template = template or datapart.DataPart(proper_identifier, db=self)
                template.bind(data_plugin(proper_identifier, self))

        if not template:
            return None

        LOGGER.debug('Compounded {} to {}'.format(identifier, template))

        return template

    def get_all_items(self):
        """
        Returns all items in the data base
        :return: list(DataPart)
        """

        identifiers = self.find(None) or list()
        for identifier in identifiers:
            item = self.get(identifier)
            if not item:
                continue
            yield item

    def get_all_data_plugins(self, package_name=None):
        """
        Returns all data plugins available int the library
        :return:
        """

        dcc_name = dcc.client().get_name()

        valid_plugins = list()
        all_plugins = self._data_factory.plugins(package_name=package_name)
        for plugin in all_plugins:
            supported_dccs = plugin.supported_dccs()
            if supported_dccs and dcc_name not in supported_dccs:
                continue
            valid_plugins.append(plugin)

        return valid_plugins

    def explore(self, location):
        """
        Returns the above and below locations for the given one
        :param location: str, location path
        :return: list(str), list(str)
        """

        for plugin in self._scan_factory.plugins():
            if plugin.can_represent(location):
                return plugin.above(location), plugin.below(location)

    @decorators.timestamp
    def sync(self, locations=None, recursive=True, full=True, progress_callback=lambda message, percent: None):
        """
        This function cycles over all the search locations stored in the data base and attempts to populate it with
        data data if that data has been changed or is new
        :param locations: list(str)
        :param recursive: bool
        :param full: bool
        """

        skip_regex = None
        patterns = self.skip_regexes()
        if patterns:
            skip_regex = re.compile('(' + ')|('.join(patterns) + ')')

        locations = python.force_list(locations or self.scan_locations())

        total_progress = 0
        progress_increment = 100 / 9    # 100 / number of sync steps

        if progress_callback:
            progress_callback('Syncing', total_progress)

        LOGGER.debug('Starting Sync : {}'.format(locations))

        scanned_identifiers = list()

        field_names = self.field_names()

        blacklisted_identifiers = list()

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            for location in locations:
                for scan_plugin in self._scan_factory.plugins():
                    if not scan_plugin.can_represent(location):
                        continue
                    for identifier in scan_plugin.identifiers(location, skip_regex, recursive=recursive):

                        if identifier == location:
                            continue

                        identifier_parts = os.path.normpath(identifier).split(os.sep)
                        if any(item in self._black_list for item in identifier_parts):
                            blacklisted_identifiers.append(identifier)
                            continue

                        field_values = list()
                        relative_identifier = self._get_relative_identifier(identifier)
                        scanned_fields = scan_plugin.fields(identifier)
                        self._update_fields(identifier, scanned_fields)
                        for field_name in field_names:
                            field_values.append('' if field_name not in scanned_fields else scanned_fields[field_name])
                        field_values = ','.join("'{}'".format(field) for field in field_values)
                        self._execute(
                            connection, 'add_with_fields', replacements={
                                '$(IDENTIFIER)': relative_identifier if self._relative_paths else identifier,
                                '$(FIELDS)': ','.join(field_names), '$(FIELDS_VALUES)': field_values})
                        self.scanned.emit(relative_identifier if self._relative_paths else identifier)
                        scanned_identifiers.append(relative_identifier if self._relative_paths else identifier)

        if full:
            with contexts.Timer('Tags synced', logger=LOGGER):
                if progress_callback:
                    total_progress += progress_increment
                    progress_callback('Syncing Tags', total_progress)
                self.sync_tags(identifiers=scanned_identifiers)
            with contexts.Timer('Versions synced', logger=LOGGER):
                if progress_callback:
                    total_progress += progress_increment
                    progress_callback('Syncing Versions', total_progress)
                self.sync_versions(identifiers=scanned_identifiers)
            with contexts.Timer('Metadata synced', logger=LOGGER):
                if progress_callback:
                    total_progress += progress_increment
                    progress_callback('Syncing Metadata', total_progress)
                self.sync_metadata(identifiers=scanned_identifiers)
            with contexts.Timer('Thumbs synced', logger=LOGGER):
                if progress_callback:
                    total_progress += progress_increment
                    progress_callback('Syncing Thumbs', total_progress)
                self.sync_thumbs(identifiers=scanned_identifiers)
            with contexts.Timer('Dependencies synced', logger=LOGGER):
                if progress_callback:
                    total_progress += progress_increment
                    progress_callback('Syncing Dependencies', total_progress)
                self.sync_dependencies(identifiers=scanned_identifiers)

        # self.clean_invalid_identifiers(blacklisted_identifiers)
        with contexts.Timer('Cleaned invalid identifiers', logger=LOGGER):
            if progress_callback:
                total_progress += progress_increment
                progress_callback('Cleanup', total_progress)
            self.clean_invalid_identifiers(blacklisted_identifiers)

        if progress_callback:
            if progress_callback:
                total_progress += progress_increment
                progress_callback('Post Callbacks', total_progress)
        self._post_sync()

        self.syncCompleted.emit()
        self.dataChanged.emit()

        end_msg = 'Sync Completed : {}'.format(locations)
        if progress_callback:
            progress_callback(end_msg, 100)
        LOGGER.debug(end_msg)

        return scanned_identifiers

    def clean_invalid_identifiers(self, blacklisted_identifiers=None):
        identifiers_to_remove = list()
        blacklisted_identifiers = list(set(python.force_list(blacklisted_identifiers)))
        for identifier in self.find(None):
            for scan_plugin in self._scan_factory.plugins():
                full_identifier = self.format_identifier(identifier)
                if scan_plugin.check(full_identifier) == scan_plugin.ScanStatus.NOT_VALID or \
                        full_identifier in blacklisted_identifiers:
                    identifiers_to_remove.append(identifier)
                    break

        self.remove(identifiers_to_remove)

    def clear(self):
        """
        Clears all the library data
        """

        self._resulst = list()
        self._grouped_results = list()
        self.dataChanged.emit()

    def cleanup(self):
        self.clean_versions()
        self.clean_thumbnails()
        self.clean_metadata()
        self.clean_dependencies()

    # ============================================================================================================
    # PATHS
    # ============================================================================================================

    def plugin_locations(self):
        """
        Returns all the places this data library is currently loading plugins from
        :return: list(str)
        """

        return self.settings().get('plugin_locations', list()) or list()

    def register_data_class(self, data_class, package_name=None):
        """
        Registers given data class
        :param package_name: str
        :param data_class: DataPart class
        """

        valid = self._data_factory.register_plugin_from_class(data_class, package_name=package_name)
        if valid:
            self._sort_data_plugins()

    def register_plugin_path(self, location, package_name=None):
        """
        Adds the given location to the list of locations being searched for when looking for plugins. This data is
        persistent between sessions and will invoke a reload of plugins
        :param location: str, plugins directory to add
        :param package_name: str
        """

        settings = self.settings()

        key = 'plugin_locations'
        settings[key] = settings.get(key, list()) + [self._clean_path(location)]
        self.save_settings(settings)

        self._scan_factory.register_path(location, package_name=package_name)
        self._data_factory.register_path(location, package_name=package_name)

        self._sort_data_plugins()

    def remove_plugin_path(self, location):
        """
        Removes a plugin location for them plugin location list and triggers a sync for plugins
        :param location: str, plugins location to remove
        """

        settings = self.settings()
        key = 'plugin_locations'
        current_settings = settings.get(key, list())
        current_settings.remove(self._clean_path(location))
        settings[key] = current_settings
        self.save_settings(settings)

        # Update factories
        self._scan_factory.unregister_path(location)
        self._data_factory.unregister_path(location)

        self._sort_data_plugins()

    def scan_locations(self):
        """
        Returns a list of all scan locations within the data base that we want to add to data base
        :return: list(str)
        """

        return self.settings().get('scan_locations', list())

    def add_scan_location(self, location, sync=False):
        """
        Adds given directory to the data base. When a new data base sync process is executed, this location
        will be picked up
        :param location: str, path where data is located
        :param sync: bool, If True, a sync operation will be executed after adding the new location
        """

        location = self._clean_path(location)
        settings = self.settings()
        key = 'scan_locations'
        current_locations = settings.get(key, list())
        if location in current_locations:
            return
        settings[key] = current_locations + [location]
        self.save_settings(settings)

        if sync:
            self.sync()

    def remove_scan_location(self, location, sync=False):
        """
        Removes the given location from the list of locations to scan data from in the data base
        :param location: str, path where data is located that we want to remove from data base
        :param sync: bool, If True, a sync operation will be executed after adding the new location
        """

        settings = self.settings()
        key = 'scan_locations'
        current_settings = settings.get(key, list())
        current_settings.remove(self._clean_path(location))
        settings[key] = current_settings
        self.save_settings(settings)

        if sync:
            self.sync()

    # ============================================================================================================
    # TAGS
    # ============================================================================================================

    def sync_tags(self, identifiers):

        all_tags = list()
        mapped_tags = dict()

        for identifier in identifiers:
            data = self.get(identifier)
            if not data:
                continue

            # Get tags for this data
            expected_tags = data.mandatory_tags()
            all_tags.extend(expected_tags)
            mapped_tags[identifier] = expected_tags

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            for tag in set(all_tags):
                self._execute(connection, 'tag_insert', replacements={'$(TAG)': tag})

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            for identifier in identifiers:
                for tag in mapped_tags.get(identifier, list()):
                    try:
                        self._execute(connection, 'tag_connect',
                                      replacements={'$(IDENTIFIER)': identifier, '$(TAG)': tag})
                    except sqlite3.IntegrityError:
                        pass

    def tag(self, identifier, tags):
        """
        Assigns given tags to the data with the given identifier
        :param identifier: str, data identifier
        :param tags: str or list(str), tag or list of tags to assign to given data identifier
        """

        tags = python.force_list(tags)

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            for tag in tags:
                self._execute(connection, 'tags_add', replacements={'$(IDENTIFIER)': identifier, '$(TAG)': tag.lower()})

    def untag(self, identifier, tags):
        """
        Removes the given tags from the data with the given identifier
        :param identifier: str, data identifier
        :param tags: str or list(str), tag or list of tags to unassign to given data identifier
        :return:
        """

        tags = python.force_list(tags)

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            for tag in tags:
                self._execute(
                    connection, 'tags_remove', replacements={'$(IDENTIFIER)': identifier, '$(TAG)': tag.lower()})

    def tags(self, identifier):
        """
        Returns a list of all the tags which are assigned to the given identifier
        :param identifier: str, data identifier
        :return: list(str)
        """

        with sqlite.ConnectionContext(self._id, get=True) as connection:
            self._execute(connection, 'tags_get', replacements={'$(IDENTIFIER)': identifier})

        return [str(result[0]) for result in connection.results]

    # ============================================================================================================
    # VERSIONS
    # ============================================================================================================

    def sync_versions(self, identifiers):

        all_versions = dict()

        identifiers = python.force_list(identifiers)

        versions_path = self.get_versions_path()
        if not versions_path or not os.path.isdir(versions_path):
            LOGGER.warning(
                'Impossible to sync versions because versions directory was not found: "{}"'.format(versions_path))
            return

        for identifier in identifiers:
            identifier = self.get_identifier(identifier)
            version_path = self.get_version_path(identifier)
            if not version_path or not os.path.isdir(version_path):
                continue

            # name = self.find_data(identifier).get(identifier, dict()).get('name')
            version_folder_name = os.path.basename(version_path)
            version_file = version.VersionFile(versions_path)
            version_file.set_version_folder_name(version_folder_name)
            # version_file.set_version_name(name)
            has_versions = version_file.has_versions()
            if not has_versions:
                continue
            versions = version_file.get_versions()
            if not versions:
                continue
            version_list = list()
            for version_number, version_file_name in versions.items():
                comment, user = version_file.get_version_data(version_number)
                version_list.append({
                    'uuid': version_folder_name, 'version_number': version_number,
                    'name': version_file_name, 'comment': comment, 'user': user})
            if not version_list:
                continue
            all_versions.setdefault(identifier, version_list)

        if not all_versions:
            return

        for identifier, versions in all_versions.items():
            for version_data in versions:
                self.add_version(**version_data)

    def get_versions_path(self):
        """
        Returns path where versions are stored
        :return: str
        """

        versions_path = self.settings().get('versions_path')
        if not versions_path:
            versions_path = path_utils.join_path(self.get_directory(), '.versions')
            self.update_settings({'versions_path': versions_path})
        if not os.path.isdir(versions_path):
            os.makedirs(versions_path)

        return versions_path

    def get_version_path(self, identifier):
        """
        Returns version path for the given identifier
        :param identifier: str
        :return: str
        """

        identifier = self.get_identifier(identifier)

        item_id = self.find_uuid(identifier)
        if not item_id:
            return None

        return path_utils.join_path(self.get_versions_path(), item_id)

    def add_version(self, uuid, version_number, name, comment, user):
        """
        Assigns given tags to the data with the given identifier
        :param uuid: str, data identifier
        """

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            self._execute(connection, 'version_add', replacements={
                '$(UUID)': uuid, '$(VERSION)': str(version_number),
                '$(NAME)': str(name), '$(COMMENT)': str(comment), '$(USER)': str(user)})

    def get_versions(self, identifier):
        """
        Returns all versions of the given data
        :param identifier: str
        :return: list
        """

        identifier = self.get_identifier(identifier)

        with sqlite.ConnectionContext(self._id, get=True) as connection:
            self._execute(connection, 'versions_get', replacements={'$(IDENTIFIER)': identifier})

        return connection.results

    def get_latest_version(self, identifier):
        """
        Returns last version data of the given data
        :param identifier: str
        :return:
        """

        identifier = self.get_identifier(identifier)

        with sqlite.ConnectionContext(self._id, get=True) as connection:
            self._execute(connection, 'version_last_get', replacements={'$(IDENTIFIER)': identifier})

        results = connection.results
        if not results:
            return None

        return results[0][0]

    def rename_version(self, uuid, new_uuid):

        versions_path = self.get_versions_path()
        if not versions_path or not os.path.isdir(versions_path):
            return

        version_folders = folder_utils.get_folders(versions_path)
        for version_folder in version_folders:
            if version_folder == uuid:
                folder_utils.rename_folder(path_utils.join_path(versions_path, version_folder), new_uuid)
                break

    def delete_version(self, uuid):

        uuids = python.force_list(uuid)

        versions_path = self.get_versions_path()
        if not versions_path or not os.path.isdir(versions_path):
            return

        version_folders = folder_utils.get_folders(versions_path)
        for version_folder in version_folders:
            if version_folder in uuids:
                folder_utils.delete_folder(path_utils.join_path(versions_path, version_folder))

    def clean_versions(self):
        versions_path = self.get_versions_path()
        if not versions_path or not os.path.isdir(versions_path):
            return

        all_uuids = self.get_all_uuids()
        version_folders = folder_utils.get_folders(versions_path)
        for version_folder in version_folders:
            if version_folder not in all_uuids:
                folder_utils.delete_folder(path_utils.join_path(versions_path, version_folder))

    # ============================================================================================================
    # THUMBS
    # ============================================================================================================

    def sync_thumbs(self, identifiers):

        all_thumbs = list()

        identifiers = python.force_list(identifiers)

        thumbs_path = self.get_thumbs_path()
        if not thumbs_path or not os.path.isdir(thumbs_path):
            LOGGER.warning(
                'Impossible to sync thumbs because thumbs directory was not found: "{}"'.format(thumbs_path))
            return

        for identifier in identifiers:
            identifier = self.get_identifier(identifier)
            uuid = self.get_uuid(identifier)
            files = fileio.get_files(thumbs_path, uuid)
            if not files:
                continue
            for thumb_file in files:
                thumb_file_path = path_utils.join_path(thumbs_path, thumb_file)
                if not thumb_file_path or not os.path.isfile(thumb_file_path):
                    continue
                all_thumbs.append({'identifier': identifier, 'thumb_name': thumb_file})

        if not all_thumbs:
            return

        for thumb in all_thumbs:
            self.set_thumb(**thumb)

    def get_thumbs_path(self):
        """
        Returns path where thumbnails are stored
        :return: str
        """

        thumbs_path = self.settings().get('thumbs_path')
        if not thumbs_path:
            thumbs_path = path_utils.join_path(self.get_directory(), '.thumbs')
            self.update_settings({'thumbs_path': thumbs_path})
        if not os.path.isdir(thumbs_path):
            os.makedirs(thumbs_path)

        return thumbs_path

    def get_thumb(self, identifier):

        identifier = self.get_identifier(identifier)

        with sqlite.ConnectionContext(self._id, get=True) as connection:
            self._execute(connection, 'thumb_get', replacements={'$(IDENTIFIER)': identifier})

        results = connection.results
        if not results:
            return None

        return results[0][0]

    def set_thumb(self, identifier, thumb_name):

        identifier = self.get_identifier(identifier)

        uuid = self.find_uuid(identifier)

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            self._execute(connection, 'thumb_set', replacements={'$(UUID)': uuid, '$(THUMB)': thumb_name})

    def rename_thumb(self, uuid, new_uuid):
        thumbs_path = self.get_thumbs_path()
        if not thumbs_path or not os.path.isdir(thumbs_path):
            return

        thumb_files = fileio.get_files(thumbs_path)
        for thumb_file in thumb_files:
            thumb_name = os.path.splitext(thumb_file)[0]
            if thumb_name == uuid:
                thumb_extension = os.path.splitext(thumb_file)[-1]
                new_thumb_name = '{}{}'.format(new_uuid, thumb_extension)
                fileio.rename_file(thumb_file, thumbs_path, new_thumb_name)
                with sqlite.ConnectionContext(self._id, commit=True) as connection:
                    self._execute(
                        connection, 'thumb_set', replacements={'$(UUID)': new_uuid, '$(THUMB)': new_thumb_name})
                break

    def delete_thumb(self, uuid):

        uuids = python.force_list(uuid)

        thumbs_path = self.get_thumbs_path()
        if not thumbs_path or not os.path.isdir(thumbs_path):
            return

        thumb_files = fileio.get_files(thumbs_path)
        for thumb_file in thumb_files:
            thumb_name = os.path.splitext(thumb_file)[0]
            if thumb_name in uuids:
                fileio.delete_file(path_utils.join_path(thumbs_path, thumb_file))
                break

    def clean_thumbnails(self):
        thumbs_path = self.get_thumbs_path()
        if not thumbs_path or not os.path.isdir(thumbs_path):
            return

        all_uuids = self.get_all_uuids()
        thumb_files = fileio.get_files(thumbs_path)
        for thumb_file in thumb_files:
            thumb_name = os.path.splitext(thumb_file)[0]
            if thumb_name not in all_uuids:
                fileio.delete_file(path_utils.join_path(thumbs_path, thumb_file))

    # ============================================================================================================
    # METADATA
    # ============================================================================================================

    def sync_metadata(self, identifiers):

        all_metadata = list()

        identifiers = python.force_list(identifiers)

        metadata_path = self.get_metadata_path()
        if not metadata_path or not os.path.isdir(metadata_path):
            LOGGER.warning(
                'Impossible to sync metadata because metadata directory was not found: "{}"'.format(metadata_path))
            return

        for identifier in identifiers:
            identifier = self.get_identifier(identifier)
            uuid = self.get_uuid(identifier)
            files = fileio.get_files(metadata_path, uuid)
            if not files:
                continue
            for metadata_file in files:
                metadata_file_path = path_utils.join_path(metadata_path, metadata_file)
                if not metadata_file_path or not os.path.isfile(metadata_file_path):
                    continue
                split_file = metadata_file.split('.')
                version = split_file[-2]
                metadata = dict()
                try:
                    metadata = jsonio.read_file(metadata_file_path)
                except Exception:
                    pass

                all_metadata.append({'identifier': identifier, 'version': version, 'metadata_dict': metadata})

        if not all_metadata:
            return

        for metadata in all_metadata:
            self.set_metadata(**metadata)

    def get_metadata_path(self):
        """
        Returns path were metadata are stored
        :return: str
        """

        metadata_path = self.settings().get('metadata_path')
        if not metadata_path:
            metadata_path = path_utils.join_path(self.get_directory(), '.meta')
            self.update_settings({'metadata_path': metadata_path})
        if not os.path.isdir(metadata_path):
            os.makedirs(metadata_path)

        return metadata_path

    def get_metadata(self, identifier, version=None):
        """
        Returns item metadata
        :param identifier: str
        :param version: int
        :return:
        """

        identifier = self.get_identifier(identifier)

        metadata_version = version if version is not None else self.get_latest_version(identifier)
        if metadata_version is None:
            LOGGER.warning('Impossible to retrieve metadata because no version found for "{}"'.format(identifier))
            return dict()

        with sqlite.ConnectionContext(self._id, get=True) as connection:
            self._execute(
                connection, 'metadata_get',
                replacements={'$(IDENTIFIER)': identifier, '$(VERSION)': metadata_version})

        result = connection.results
        if not result:
            return dict()

        result_dict = dict()
        result_str = result[0][0]
        try:
            result_dict = json.loads(str(result_str).replace("\'", "\""))
        except Exception as exc:
            LOGGER.warning('Error while parsing file "{}" metadata: "{}"'.format(identifier, exc))

        return result_dict

    def set_metadata(self, identifier, version, metadata_dict):
        """
        Sets item metadata
        :param identifier: str
        :param metadata_dict: dict
        """

        identifier = self.get_identifier(identifier)

        uuid = self.find_uuid(identifier)

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            self._execute(
                connection, 'metadata_set',
                replacements={'$(UUID)': uuid, '$(VERSION)': version, '$(METADATA)': metadata_dict})

    def rename_metadata(self, uuid, new_uuid):
        metadata_path = self.get_metadata_path()
        if not metadata_path or not os.path.isdir(metadata_path):
            return

        meta_files = fileio.get_files(metadata_path)
        for meta_file in meta_files:
            meta_name = os.path.splitext(meta_file)[0].split('.')[0]
            if meta_name == uuid:
                meta_extension = os.path.splitext(meta_file)[-1]
                new_meta_name = '{}{}'.format(new_uuid, meta_extension)
                fileio.rename_file(meta_file, metadata_path, new_meta_name)
                break

    def delete_metadata(self, uuid):

        uuids = python.force_list(uuid)

        metadata_path = self.get_metadata_path()
        if not metadata_path or not os.path.isdir(metadata_path):
            return

        meta_files = fileio.get_files(metadata_path)
        for meta_file in meta_files:
            meta_name = os.path.splitext(meta_file)[0].split('.')[0]
            if meta_name in uuids:
                fileio.delete_file(path_utils.join_path(metadata_path, meta_file))
                break

    def clean_metadata(self):
        metadata_path = self.get_metadata_path()
        if not metadata_path or not os.path.isdir(metadata_path):
            return

        all_uuids = self.get_all_uuids()
        meta_files = fileio.get_files(metadata_path)
        for meta_file in meta_files:
            meta_name = os.path.splitext(meta_file)[0].split('.')[0]
            if meta_name not in all_uuids:
                fileio.delete_file(path_utils.join_path(metadata_path, meta_file))

    # ============================================================================================================
    # DEPENDENCIES
    # ============================================================================================================

    def sync_dependencies(self, identifiers):

        all_dependencies = list()

        identifiers = python.force_list(identifiers)

        dependencies_path = self.get_dependencies_path()
        if not dependencies_path or not os.path.isdir(dependencies_path):
            LOGGER.warning(
                'Impossible to sync dependencies because dependencies directory was not found: "{}"'.format(
                    dependencies_path))
            return

        for identifier in identifiers:
            identifier = self.get_identifier(identifier)
            uuid = self.get_uuid(identifier)
            files = fileio.get_files(dependencies_path, uuid)
            if not files:
                continue
            for dependency_file in files:
                dependency_file_path = path_utils.join_path(dependencies_path, dependency_file)
                if not dependency_file_path or not os.path.isfile(dependency_file_path):
                    continue
                dependency_data = dict()
                try:
                    dependency_data = jsonio.read_file(dependency_file_path)
                except Exception:
                    pass
                if not dependency_data:
                    continue

                for dependency_uuid, dependency_name in dependency_data.items():
                    dependency_identifier = self.find_identifier_from_uuid(dependency_uuid)
                    if not dependency_identifier:
                        continue
                    all_dependencies.append(
                        {'root_identifier': identifier, 'dependency_identifier': dependency_identifier,
                         'name': dependency_name})

        if not all_dependencies:
            return

        for dependency in all_dependencies:
            self.add_dependency(**dependency)

    def get_dependencies_path(self):
        """
        Returns path were dependencies links are stored
        :return: str
        """

        dependencies_path = self.settings().get('dependencies_path')
        if not dependencies_path:
            dependencies_path = path_utils.join_path(self.get_directory(), '.dependencies')
            self.update_settings({'dependencies_path': dependencies_path})
        if not os.path.isdir(dependencies_path):
            os.makedirs(dependencies_path)

        return dependencies_path

    def add_dependency(self, root_identifier, dependency_identifier, name):
        """
        Assigns given tags to the data with the given identifier
        :param root_identifier: str, data identifier
        :param dependency_identifier: str, data identifier
        :param name: str, data identifier
        """

        root_identifier = self.get_identifier(root_identifier)
        dependency_identifier = self.get_identifier(dependency_identifier)

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            self._execute(connection, 'dependency_add', replacements={
                '$(ROOT_IDENTIFIER)': root_identifier, '$(DEPENDENCY_IDENTIFIER)': dependency_identifier,
                '$(NAME)': name})

    def get_dependencies(self, identifier, as_uuid=False):

        identifier = self.get_identifier(identifier)

        if as_uuid:
            with sqlite.ConnectionContext(self._id, get=True) as connection:
                self._execute(connection, 'dependencies_uuid_get', replacements={'$(IDENTIFIER)': identifier})
        else:
            with sqlite.ConnectionContext(self._id, get=True) as connection:
                self._execute(connection, 'dependencies_get', replacements={'$(IDENTIFIER)': identifier})

        result_dict = dict()
        result = connection.results
        if not result:
            return result_dict

        for result in connection.results:
            result_dict[result[0]] = result[1]

        return result_dict

    def rename_dependency(self, uuid, new_uuid, current_dependencies):

        dependencies_path = self.get_dependencies_path()
        if not dependencies_path or not os.path.isdir(dependencies_path):
            return

        dependencies_files = fileio.get_files(dependencies_path)
        for dependency_file in dependencies_files:
            dependency_name = os.path.splitext(dependency_file)[0].split('.')[0]
            if dependency_name == uuid:
                dependency_extension = os.path.splitext(dependency_file)[-1]
                new_dependency_name = '{}{}'.format(new_uuid, dependency_extension)
                fileio.rename_file(dependency_file, dependencies_path, new_dependency_name)
                break

        for dependency_file in dependencies_files:
            dependency_name = os.path.splitext(dependency_file)[0].split('.')[0]
            if dependency_name in current_dependencies:
                dependency_file_path = path_utils.join_path(dependencies_path, dependency_file)
                if not os.path.isfile(dependency_file_path):
                    continue
                dependency_data = jsonio.read_file(dependency_file_path)
                if not dependency_data or uuid not in dependency_data:
                    continue
                dependency_data[new_uuid] = dependency_data[uuid]
                dependency_data.pop(uuid)
                jsonio.write_to_file(dependency_data, dependency_file_path)

    def delete_dependencies(self, uuid, recursive=True):

        uuids = python.force_list(uuid)

        dependencies_path = self.get_dependencies_path()
        if not dependencies_path or not os.path.isdir(dependencies_path):
            return

        dependencies_data = None
        dependencies_files = fileio.get_files(dependencies_path)
        for dependency_file in dependencies_files:
            dependency_name = os.path.splitext(dependency_file)[0].split('.')[0]
            if dependency_name in uuids:
                dependency_file_path = path_utils.join_path(dependencies_path, dependency_file)
                dependencies_data = jsonio.read_file(dependency_file_path)
                fileio.delete_file(dependency_file_path)
                break

        dependencies_files = fileio.get_files(dependencies_path)
        for dependency_file in dependencies_files:
            dependency_file_path = path_utils.join_path(dependencies_path, dependency_file)
            if not os.path.isfile(dependency_file_path):
                continue
            dependency_data = jsonio.read_file(dependency_file_path)
            if not dependency_data:
                continue
            modified = False
            for dependency_uuid in dependency_data.copy():
                if dependency_uuid in uuids:
                    dependency_data.pop(dependency_uuid)
                    modified = True
            if modified:
                jsonio.write_to_file(dependency_data, dependency_file_path)

        if recursive and dependencies_data:
            self.delete_dependencies(list(dependencies_data.keys()), recursive=True)

    def clean_dependencies(self):
        dependencies_path = self.get_dependencies_path()
        if not dependencies_path or not os.path.isdir(dependencies_path):
            return

        all_uuids = self.get_all_uuids()
        dependencies_files = fileio.get_files(dependencies_path)
        for dependency_file in dependencies_files:
            dependency_name = os.path.splitext(dependency_file)[0].split('.')[0]
            if dependency_name not in all_uuids:
                fileio.delete_file(path_utils.join_path(dependencies_path, dependency_file))

        dependencies_files = fileio.get_files(dependencies_path)
        for dependency_file in dependencies_files:
            dependency_file_path = path_utils.join_path(dependencies_path, dependency_file)
            if not os.path.isfile(dependency_file_path):
                continue
            dependency_data = jsonio.read_file(dependency_file_path)
            if not dependency_data:
                continue
            modified = False
            for dependency_uuid in dependency_data:
                if dependency_uuid not in all_uuids:
                    dependency_data.pop(dependency_uuid)
                    modified = True
            if modified:
                jsonio.write_to_file(dependency_data, dependency_file_path)

    # ============================================================================================================
    # SEARCH
    # ============================================================================================================

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

    def sort_by(self):
        """
        Return the list of fields to sorty by
        :return: list(str)
        """

        return self.settings().get('sort_by', list())

    def set_sort_by(self, fields):
        """
        Set the list of fields to group by
        >>> set_sorty_by(['name:asc', 'type:asc'])
        :param fields: list(str)
        """

        settings = self.settings()
        settings['sort_by'] = python.force_list(fields)
        self.save_settings(settings)

    def group_by(self):
        """
        Return the list of fields to group by
        :return: list(str)
        """

        return self.settings().get('group_by', list())

    def set_group_by(self, fields):
        """
        Set the list of fields to group by
        >>> set_group_by(['name:asc', 'type:asc'])
        :param fields: list(str)
        """

        settings = self.settings()
        settings['group_by'] = python.force_list(fields)
        self.save_settings(settings)

    def fields(self):
        """
        Returns all the fields for the library
        :return: list(str)
        """

        with sqlite.ConnectionContext(self._id, get=True) as connection:
            self._execute(connection, 'fields_get')

        fields_list = list()
        for field_list in connection.results:
            fields_list.append({
                'name': field_list[0],
                'sortable': field_list[1],
                'groupable': field_list[2]
            })

        return fields_list

    def field_names(self):
        """
        Returns all field names for the library
        :return: list(str)
        """

        with sqlite.ConnectionContext(self._id, get=True) as connection:
            self._execute(connection, 'field_names_get')

        return [row[0] for row in connection.results]

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

        items_data = self.find_data() or dict()
        for identifier, data in items_data.items():
            value = data.get(field)
            if value is not None:
                results.setdefault(value, {'count': 0, 'name': value})
                match = self.match(data, queries)
                if match:
                    results[value]['count'] += 1

        def sort_key(facet):
            return facet.get(sort_by)

        return sorted(list(results.values()), key=sort_key)

    def search(self, limit=None):
        """
        Runs a search using the queries added to the library data
        """

        if not self.is_search_enabled():
            return

        start_time = time.time()
        LOGGER.debug('Searching items ...')
        self.searchStarted.emit()

        self._results = self.find_items(self.queries(), limit=limit)
        self._grouped_results = self.group_items(self._results, self.group_by())

        self._search_time = time.time() - start_time
        self.searchFinished.emit()
        LOGGER.debug('Search time: {}'.format(self._search_time))

    def find(self, tags, limit=None):
        """
        Returns list of identifiers which match the given paths
        :param tags: list(str)
        :param limit: int, maximum number of hits to return
        :return: list(str)
        """

        self.searchStarted.emit()

        with sqlite.ConnectionContext(self._id, get=True) as connection:
            replacements = {'$(LIMIT)': limit or 9 ** 9}
            tags = python.force_list(tags)
            if tags:
                compare_str = ''
                like_str = ''
                name_str = ''

                for tag in tags:
                    compare_str += "tag='%s' OR " % tag
                    like_str += "identifier LIKE '%" + tag + "%' AND "
                    name_str += "name LIKE '%" + tag + "%' AND "

                compare_str = compare_str[:-4]
                like_str = like_str[:-5]
                name_str = name_str[:-5]

                replacements.update({
                    '$(TAG_COMPARE)': compare_str,
                    '$(LIKE_COMPARE)': like_str,
                    '$(NAME_COMPARE)': name_str,
                    '$(COMPARE_COUNT)': str(len(tags))
                })

                self._execute(connection, 'find', replacements=replacements)
            else:
                self._execute(connection, 'find_all', replacements=replacements)

        # self.searchFinished.emit()

        return [row[1] for row in connection.results]

    def find_data(self, identifier=None):
        """
        Returns a list of dictionaries mapping identifiers with the data stored in the DB
        If no identifier is given, all identifiers data will be return
        :param identifier: str,
        :return: list(dict())
        """

        identifiers = python.force_list(identifier or self.find(None))
        field_names = self.field_names()

        if self._relative_paths:
            identifiers = [self._get_relative_identifier(identifier) for identifier in identifiers]

        data_mapping = dict()
        with sqlite.ConnectionContext(self._id, get=True) as connection:
            self._execute(connection, 'find_fields', replacements={
                '$(IDENTIFIERS)': ','.join(["'{}'".format(identifier) for identifier in identifiers])[1:-1],
                '$(FIELDS)': ','.join(field_names)})

        for result in connection.results:
            identifier = result[0]
            data_mapping.setdefault(identifier, dict())
            data_list = result[1:]
            for i, data_value in enumerate(data_list):
                data_mapping[identifier][field_names[i]] = data_value

            # We store identifier and the its long version
            data_mapping[identifier]['identifier'] = identifier
            data_mapping[identifier]['path'] = self.format_identifier(identifier)

        return data_mapping

    def find_items(self, queries, limit=None):
        """
        Returns list of items which match the given paths
        :param queries: list(str)
        :param limit: int, maximum number of hits to return
        :return: list(str)
        """

        fields = list()
        results = list()

        queries = copy.copy(queries)
        queries.extend(self._global_queries.values())

        items_data = self.find_data()
        if not items_data:
            return results

        for identifier, data in items_data.items():
            match = self.match(data, queries)
            if match:
                item = self.get(identifier)
                results.append(item)
            fields.extend(list(data.keys()))

        return results

    def find_id(self, identifier):
        """
        Returns unique id of the given identifier
        :param identifier: str
        :return: str
        """

        identifier = self.get_identifier(identifier)

        with sqlite.ConnectionContext(self._id, get=True) as connection:
            self._execute(connection, 'find_id', replacements={'$(IDENTIFIER)': identifier})

        results = connection.results
        if not results:
            return None

        return results[0][0]

    def find_identifier_from_uuid(self, uuid):
        """
        Returns identifier from tis UUID
        :param uuid: str
        :return: str
        """

        with sqlite.ConnectionContext(self._id, get=True) as connection:
            self._execute(connection, 'find_from_uuid', replacements={'$(UUID)': uuid})

        results = connection.results
        if not results:
            return None

        return results[0][0]

    def find_uuid(self, identifier):
        """
        Returns UUID of the given identifier
        :param identifier: str
        :return: str
        """

        identifier = self.get_identifier(identifier)

        with sqlite.ConnectionContext(self._id, get=True) as connection:
            self._execute(connection, 'find_uuid', replacements={'$(IDENTIFIER)': identifier})

        results = connection.results
        if not results:
            return None

        return results[0][0]

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

    # ============================================================================================================
    # SETTINGS
    # ============================================================================================================

    def settings(self):
        """
        Will try to return the stored settings. If no settings are available, an empty dictionary will be returned.
        :return: dict
        """

        with sqlite.ConnectionContext(self._id, get=True) as connection:
            self._execute(connection, 'settings_get')

        try:
            return json.loads(connection.results[0][0])
        except IndexError:
            return dict()

    def update_settings(self, settings_dict):
        """
        Updates current db settings with the values of the given settings
        :param settings_dict: dict
        """

        settings = self.settings()
        settings_dict = settings_dict or dict()
        settings.update(settings_dict)

        self.save_settings(settings)

    def save_settings(self, settings_dict):
        """
        Stores given settings dictionary in data base. The given data must be JSON serializable.
        :param settings_dict: dict
        """

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            self._execute(connection, 'settings_set', replacements={'$(SETTINGS)': json.dumps(settings_dict)})

    # ============================================================================================================
    # INTERNAL
    # ============================================================================================================

    def _post_sync(self):
        """
        Internal function that executed once the library items data have been synced
        Override to implement custom functionality
        """

        pass

    def _get_relative_identifier(self, identifier):
        """
        Internal function that returns a relative identifier from the given one
        :param identifier: str
        :return: str
        """

        if os.path.isabs(identifier):
            identifier = path_utils.clean_path(os.path.relpath(identifier, self.get_directory()))

        if identifier == '.' or identifier.startswith('./'):
            return identifier

        return path_utils.clean_path('./{}'.format(identifier))

    def _clean_path(self, data_path):
        """
        Returns a cleaned version of the given path to make sure that it works properly within data base
        :param data_path: str
        :return: str
        """

        return path_utils.clean_path(data_path)

    def _get_commands_dict(self):
        """
        Internal function that generates a dictionary where the key is the SQL command name and the value is the SQL
        data
        :return: dict
        """

        commands_dict = dict()

        for command in os.listdir(self.SQL_COMMANDS_DIR):
            with open(os.path.join(self.SQL_COMMANDS_DIR, command)) as f:
                commands_dict[os.path.splitext(command)[0]] = [
                    statement.strip() for statement in f.read().split(';') if statement.strip()]

        return commands_dict

    def _execute(self, context, command, replacements=None):
        """
        Internal function that all SQL queries should be routed through. This ensures a consistent result and suite
        of reporting.
        :param context: sqlite.ConnectionContext, all calls should be done withing a ConnectionContext to aid
            performance
        :param command: str, SQL command name to run
        :param replacements: dict, any search and replace strings to process on the SQL command
        """

        statements = self._commands[command]

        for single_statement in statements:
            if replacements:
                for k, v in replacements.items():
                    single_statement = single_statement.replace(k, str(v))

            LOGGER.debug('\n' + ('-' * 100))
            LOGGER.debug(single_statement)

            try:
                context.cursor.execute(single_statement)
            except sqlite3.Error:
                LOGGER.error(sys.exc_info())
                LOGGER.info('Unable to execute SQL command : {}'.format(single_statement))
                return list()

    def _sort_data_plugins(self):
        """
        Internal function that makes sure that data plugins list is sort by plugin priority
        """

        self._data_plugins = sorted(self._data_factory.plugins(), key=lambda x: x.PRIORITY, reverse=True)

    def _register_data_plugins_classes_from_config(self):
        """
        Internal function that registers all classes found in tpDcc-libs-datalibrary configuration file
        """

        datalib_config = configs.get_library_config('tpDcc-libs-datalibrary')
        extra_item_classes = datalib_config.get('extra_item_classes')
        if not extra_item_classes:
            return

        for item_class_name in extra_item_classes:
            module_class = modules.resolve_module(item_class_name)
            if not module_class:
                LOGGER.warning('Impossible to register data item class: "{}"'.format(module_class))
                continue

            self.register_data_class(item_class_name, 'tpDcc')

    def _update_fields(self, identifier, scanned_fields):
        """
        Internal function that updates the scanned fields returned by the scan plugin
        :param scanned_fields: dict
        """

        scanned_fields['uuid'] = self.get_uuid(identifier)

        if self._relative_paths:
            # We update the scanned directory to make sure its stored relative to current project path
            scanned_fields['directory'] = self._get_relative_identifier(scanned_fields['directory'])

        item = self.get(identifier)
        if item:
            scanned_fields['type'] = item.type()
