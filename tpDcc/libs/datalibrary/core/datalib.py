import os
import re
import sys
import json
import sqlite3
import logging

from tpDcc.libs.python import python, signal, sqlite, plugin, path as path_utils

from tpDcc.libs.datalibrary.core import scanner, datapart

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class DataLib(object):

    SQL_COMMANDS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sql')

    def __init__(self, identifier):

        self.scanned = signal.Signal()
        self.scanCompleted = signal.Signal()

        self._id = identifier
        self._commands = self._get_commands_dict()

        plugin_locations = list()
        if os.path.exists(identifier):
            plugin_locations = self.plugin_locations()
        plugin_locations.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'plugins'))

        self._scan_factory = plugin.PluginFactory(scanner.BaseScanner, paths=plugin_locations, plugin_id='scan_type')
        self._data_factory = plugin.PluginFactory(datapart.DataPart, paths=plugin_locations, plugin_id='data_type')

        self._sort_data_plugins()

    # ============================================================================================================
    # PROPERTIES
    # ============================================================================================================

    @property
    def identifier(self):
        return self._id

    # ============================================================================================================
    # CLASS METHODS
    # ============================================================================================================

    @classmethod
    def create(cls, path, plugin_paths):
        if not path.endswith('db'):
            path += '.db'

        data_lib = cls(path)
        data_lib.init()

        for plugin_path in plugin_paths:
            if not os.path.isdir(plugin_path):
                continue
            data_lib.register_plugin_path(plugin_path)

        return data_lib

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def init(self):
        """
        Initializes and creates data source
        """

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            self._execute(connection, 'create')

            return True

    def add(self, identifier):
        """
        Adds data identifier into data base
        :param identifier: str, data identifier
        """

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            self._execute(connection, 'add', replacements={'$(IDENTIFIER)': identifier})

    def remove(self, identifier):
        """
        Removes data from data base
        :param identifier: str, dta identifier
        """

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            self._execute(connection, 'remove', replacements={'$(IDENTIFIER)': identifier})

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

    def save_settings(self, settings_dict):
        """
        Stores given settings dictionary in data base. The given data must be JSON serializable.
        :param settings_dict: dict
        """

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            self._execute(connection, 'settings_set', replacements={'$(SETTINGS)': json.dumps(settings_dict)})

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

        settings = self.settings()
        key = 'scan_locations'
        settings[key] = settings.get(key, list()) + [self._clean_path(location)]
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

    def plugin_locations(self):
        """
        Returns all the places this data library is currently loading plugins from
        :return: list(str)
        """

        return self.settings().get('plugin_locations', list()) or list()

    def register_plugin_path(self, location):
        """
        Adds the given location to the list of locations being searched for when looking for plugins. This data is
        persistent between sessions and will invoke a reload of plugins
        :param location: str, plugins directory to add
        """

        settings = self.settings()

        key = 'plugin_locations'
        settings[key] = settings.get(key, list()) + [self._clean_path(location)]
        self.save_settings(settings)

        self._scan_factory.register_path(location)
        self._data_factory.register_path(location)

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

        return [str(result[0] for result in connection.results)]

    def sync(self, locations=None, recursive=True, full=True):
        """
        This function cycles over all the search locations stored in the data base and attempts to populate it with
        data data if that data has been changed or is new
        :param locations: list(str)
        :param recursive: bool
        :param full: bool
        """

        LOGGER.info('Starting Sync : {}'.format(locations))

        skip_regex = None
        patterns = self.skip_regexes()
        if patterns:
            skip_regex = re.compile('(' + ')|('.join(patterns) + ')')

        locations = python.force_list(locations or self.scan_locations())

        scanned_identifiers = list()

        with sqlite.ConnectionContext(self._id, commit=True) as connection:
            for location in locations:
                for scan_plugin in self._scan_factory.plugins():
                    if not scan_plugin.can_represent(location):
                        continue
                    for identifier in scan_plugin.identifiers(location, skip_regex, recursive=recursive):
                        self._execute(connection, 'add', replacements={'$(IDENTIFIER)': identifier})
                        self.scanned.emit(identifier)
                        scanned_identifiers.append(identifier)

        if full:
            all_tags = list()
            mapped_tags = dict()

            for scanned_identifier in scanned_identifiers:
                data = self.get(scanned_identifier)
                if not data:
                    continue

                # Get tags for this data
                expected_tags = data.mandatory_tags()
                all_tags.extend(expected_tags)
                mapped_tags[scanned_identifier] = expected_tags

            with sqlite.ConnectionContext(self._id, commit=True) as connection:
                for tag in set(all_tags):
                    self._execute(connection, 'tag_insert', replacements={'$(TAG)': tag})

            with sqlite.ConnectionContext(self._id, commit=True) as connection:
                for scanned_identifier in scanned_identifiers:
                    for tag in mapped_tags[scanned_identifier]:
                        try:
                            self._execute(connection, 'tag_connect',
                                          replacements={'$(IDENTIFIER)': scanned_identifier, '$(TAG)': tag})
                        except sqlite3.IntegrityError:
                            pass

            # If data cleanup is allowed, we do it
            for identifier in self.find(None):
                for scan_plugin in self._scan_factory.plugins():
                    if scan_plugin.check(identifier) == scan_plugin.ScanStatus.NOT_VALID:
                        self.remove(identifier)
                        break

        self.scanCompleted.emit()

        LOGGER.info('Sync Completed : {}'.format(locations))

        return scanned_identifiers

    def get(self, identifier):
        """
        Returns a composite binding of a DataPart plugin, bringing together all the plugins which can viably
        represent this data
        :param identifier: data identifier to be passed to the DataPart
        :return: DataPart composite
        """

        template = None

        for data_plugin in self._data_plugins:
            if data_plugin.can_represent(identifier):
                template = template or datapart.DataPart(identifier, db=self)
                template.bind(data_plugin(identifier, self))

        LOGGER.info('Compounded {} to {}'.format(identifier, template))

        return template

    def find(self, tags, limit=None):
        """
        Returns list of identifiers which match the given paths
        :param tags: list(str)
        :param limit: int, maximum number of hits to return
        :return: list(str)
        """

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

        return [row[1] for row in connection.results]

    def explore(self, location):
        """
        Returns the above and below locations for the given one
        :param location: str, location path
        :return: list(str), list(str)
        """

        for plugin in self._scan_factory.plugins():
            if plugin.can_represent(location):
                return plugin.above(location), plugin.below(location)

    # ============================================================================================================
    # INTERNAL
    # ============================================================================================================

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

        self._data_plugins = sorted(self._data_factory.plugins(), key=lambda x: x.priority, reverse=True)
