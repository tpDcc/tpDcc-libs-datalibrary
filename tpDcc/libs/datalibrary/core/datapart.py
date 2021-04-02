#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base DataPart class implementation. This is the class all data inherit
and their compositions are used to represent data
"""

from __future__ import print_function, division, absolute_import

import os

from tpDcc.libs.composite.core import composition, decorators
from tpDcc.libs.python import fileio, jsonio, version, folder, path as path_utils


class DataPart(composition.Composition):
    """
    A DataPart is a block of functionality and an interface to a piece of data. A piece of data can be
    represented by multiple DataParts in a composite form
    """

    # Allows define a unique identifier fo the type of data. When querying from data base this will
    # form part of the composition string
    DATA_TYPE = ''

    # Useful when we wwant to reimplement a plugin with the same data type as another plugin. In this
    # way, only the highest version will be used.
    VERSION = 1

    # Priority to determine the order of class composition. Higher values mean the class will be
    # composited first. This can have an effect on methods decorated with composite decorators.
    PRIORITY = 1

    # Default icon used by the item in menus
    MENU_ICON = 'tpDcc'
    MENU_NAME = ''

    # Defines whether or not this item allow deletion and nested hierarchies
    ENABLE_DELETE = True
    ENABLE_NESTED_ITEMS = False

    EXTENSION = None

    def __init__(self, identifier, db=None):
        super(DataPart, self).__init__()

        self._id = identifier
        self._db = db

        if self.extension() and not self._id.endswith(self.extension()):
            self._id = '{}{}'.format(self._id, self.extension())

    def __repr__(self):
        base_repr = super(DataPart, self).__repr__()
        return base_repr.replace('DataPart', 'DataPart: {}'.format(self._id))

    def __eq__(self, other):
        return self.format_identifier() == other.format_identifier()

    # def __ne__(self, other):
    #     return self.format_identifier() != other.format_identifier()

    # ============================================================================================================
    # PROPERTIES
    # ============================================================================================================

    @property
    def library(self):
        return self._db

    # ============================================================================================================
    # ABSTRACT FUNCTIONS
    # ============================================================================================================

    @classmethod
    def can_represent(cls, identifier, only_extension=False):
        """
        Returns whether or not this plugin can represent the given identifier
        :param identifier: str, data identifier. This could be a URL, a file path, a UUID, etc
        :param only_extension: bool, If True, only trait (usually extension) will be checked
        :return: bool
        """

        return False

    @classmethod
    def supported_dccs(cls):
        """
        Returns a list of DCC names this data can be loaded into. In a situation where multiple DataParts are bound
        then the combined results of all the mandatory tags are used.
        :return: list(str) or None
        """

        return list()

    @decorators.first_true
    def type(self):
        """
        Returns type of the file
        :return: str
        """

        return "Data"

    @decorators.first_true
    def label(self):
        """
        Returns the label or name for the DataPart. This would be the pretty or display name and oes not need to be
        unique. If multiple DataParts are bound to represent a piece of information then the first to return a
        non-false return will be taken
        :return: str or None
        """

        return None

    @decorators.first_true
    def icon(self):
        """
        Returns the icon for the DataPart. If multiple data parts are bound to represent a piece of information
        the the first to return a non-false return will be taken.
        :return: str or None
        """

        return False

    @decorators.first_true
    def menu_name(self):
        """
        Defines the display name that should appear in the create data menus. If not given, data part will not appear
        in data creation menus
        :return: str or None
        """

        return None

    @decorators.first_true
    def extension(self):
        """
        Returns data extension
        :return: str
        """

        return None

    @decorators.extend_unique
    def mandatory_tags(self):
        """
        Returns any tags that should always be assigned to this data element. In a situation where multiple DataParts
        are bound then the combined results of all the mandatory tags are used.
        :return: list(str) or None
        """

        return None

    @decorators.update_dictionary_unique
    def functionality(self):
        """
        Exposes per-data functionality in the form of a dictionary where the key is the string accessor, and the value
        is a callable. In a situation where multiple DataParts are bound then a single dictionary with all the entries
        combined is returned.
        :return: dict
        """

        return decorators.Ignore

    @decorators.extend_results
    def load_schema(self):
        """
        Gets the options used to load the item
        :return: list(dict)
        """

        return list()

    @decorators.extend_results
    def save_schema(self):
        """
        Returns the schema used for saving the item
        :return: dict
        """

        return decorators.Ignore

    @decorators.extend_results
    def export_schema(self):
        """
        Returns the schema used for exporting the item
        :return: dict
        """

        return decorators.Ignore

    @decorators.update_dictionary
    def metadata_dict(self):
        """
        Exposes per-metadata functionality in the form of a dictionary
        :return: dict
        """

        return decorators.Ignore

    @decorators.extend_results
    def save_validator(self, **kwargs):
        """
        Validates the given save fields
        Called when an input field has changed
        :param kwargs: dict
        :return: list(dict)
        """

        pass

    @decorators.extend_results
    def load_validator(self, **options):
        """
        Validates the current load options
        Called when the load fields change
        :param options: dict
        :return: list(dict)
        """

        return list()

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def identifier(self):
        """
        Returns the identifier of this data part
        :return: str
        """

        return self._id

    def format_identifier(self):
        """
        Returns an identifier formatted depending on the data library
        :return: str
        """

        return self._db.format_identifier(self.identifier()) if self._db else self.identifier()

    def name(self):
        """
        Returns data name
        :return: str
        """

        return os.path.splitext(os.path.basename(self.format_identifier()))[0]

    def full_name(self):
        """
        Returns data full name
        :return: str
        """

        directory, name, extension = path_utils.split_path(self.format_identifier())
        extension = extension or self.extension()
        if extension:
            return path_utils.clean_path('{}{}'.format(name, extension))

        return name

    def data(self):
        """
        Returns data dictionary.
        :return: dict
        """

        data = self._db.find_data(self._id)
        if not data:
            return dict()

        return list(data.values())[0]

    # ============================================================================================================
    # TAGS
    # ============================================================================================================

    def tags(self):
        """
        Returns al the tags assigned to this DataPart
        :return: list(str)
        """

        return self._db.tags(self._id)

    def tag(self, tags):
        """
        Assigns the given tags to this DataPart
        :param tags: list(str) or str, tag or list of tags we want to add to this DataPart
        """

        return self._db.tag(self._id, tags)

    def untag(self, tags):
        """
        Untags the given tags from this DataPart
        :param tags: list(str) or str, tag or list of tags we want to remove from this DataPart
        :return:
        """

        return self._db.untag(self._id, tags)

    # ============================================================================================================
    # VERSION
    # ============================================================================================================

    def version_path(self):
        """
        Returns the path where data versions are located
        :return: str
        """

        return path_utils.clean_path(self._db.get_version_path(self.format_identifier()))

    def create_version(self, comment):

        version_path = self.version_path()
        if version_path and not os.path.isdir(version_path):
            folder.create_folder(version_path)
        if version_path and os.path.isdir(version_path):
            versions_path = os.path.dirname(version_path)
            version_folder_name = os.path.basename(version_path)
            version_file = version.VersionFile(self.format_identifier())
            version_file.set_version_folder(versions_path)
            version_file.set_version_folder_name(version_folder_name)
            version_file.save(comment or '')
            last_version = version_file.get_latest_version()
        else:
            return False

        if last_version:
            self.create_metadata(os.path.basename(last_version).split('.')[-1])

        return True

    # ============================================================================================================
    # THUMBNAIL
    # ============================================================================================================

    def get_thumb_name(self):

        return self._db.get_thumb(self._id)

    def get_thumb_path(self, thumb_name=None):

        thumb_name = thumb_name or self.get_thumb_name()
        if not thumb_name:
            return

        thumb_path = path_utils.join_path(self._db.get_thumbs_path(), thumb_name)

        return thumb_path

    def store_thumbnail(self, thumbnail_path):
        if not os.path.isfile(thumbnail_path):
            return None
        extension = os.path.splitext(os.path.basename(thumbnail_path))[-1]
        thumb_name = self._db.get_uuid(self._id)
        if not thumb_name.endswith(extension):
            thumb_name = '{}{}'.format(thumb_name, extension)
        thumb_path = self.get_thumb_path(thumb_name)
        fileio.move_file(thumbnail_path, thumb_path)

        self._db.set_thumb(self._id, thumb_name)

        return True

    # ============================================================================================================
    # METADATA
    # ============================================================================================================

    def get_metadata_path(self, version):
        metadata_name = '{}.{}.json'.format(self._db.get_uuid(self._id), version)
        meta_path = path_utils.join_path(self._db.get_metadata_path(), metadata_name)

        return meta_path

    def create_metadata(self, version):

        # We make sure the current item exists and also, we make sure the item has all composition metadata
        item = self._db.get(self._id)
        if not item:
            return

        metadata = item.metadata_dict() or dict()
        metadata_path = self.get_metadata_path(version)
        metadata_dir = os.path.dirname(metadata_path)
        if not os.path.isdir(metadata_dir):
            folder.create_folder(metadata_dir)
        jsonio.write_to_file(metadata, metadata_path)

        self.set_metadata(version, metadata)

    def metadata(self):
        """
        Returns metadata data dictionary.
        :return: dict
        """

        self._db.get_metadata(self.format_identifier())

    def set_metadata(self, version, metadata_dict):
        """
        Sets metadata data dictionary of this item
        :param metadata_dict:
        :return:
        """
        return self._db.set_metadata(self._id, version, metadata_dict)

    # ============================================================================================================
    # DEPENDENCIES
    # ============================================================================================================

    def get_dependencies(self, data_path=None):
        if not self.library:
            return dict()

        data_path = self.library.format_identifier(data_path) if data_path else self.format_identifier()
        deps_dict = self.library.get_dependencies(data_path, as_uuid=False)
        if not deps_dict:
            return dict()

        result = dict()

        for identifier, dependency_name in deps_dict.items():
            item = self.library.get(identifier)
            if not item:
                continue
            if dependency_name in result:
                if not isinstance(result[dependency_name], list):
                    result[dependency_name] = [result[dependency_name]]
                result[dependency_name].append(item.format_identifier())
            else:
                result[dependency_name] = item.format_identifier()

        return result

    def update_dependencies(self, dependencies=None, recursive=True):

        if not dependencies or not isinstance(dependencies, dict):
            dependencies = dict()

        dependency_file_name = '{}.json'.format(self._db.get_uuid(self.format_identifier()))
        dependency_path = path_utils.join_path(self._db.get_dependencies_path(), dependency_file_name)
        if not os.path.isfile(dependency_path):
            fileio.create_file(dependency_path)

        all_dependencies = dict()
        current_dependencies = jsonio.read_file(dependency_path) or dict()
        for dependency_uuid, dependency_name in current_dependencies.items():
            dependency = self._db.find_identifier_from_uuid(dependency_uuid)
            if not dependency:
                continue
            all_dependencies.update({dependency: dependency_name})
        if dependencies:
            all_dependencies.update(dependencies)

        for dependency, dependency_name in all_dependencies.items():
            self._db.add_dependency(self.format_identifier(), dependency, dependency_name)

        dependencies = self._db.get_dependencies(self.format_identifier(), as_uuid=True)
        if not dependencies:
            fileio.delete_file(dependency_path)
            return
        jsonio.write_to_file(dependencies, dependency_path)

        # We update all related dependencies
        if recursive:
            for dependency, dependency_name in all_dependencies.items():
                dependency_item = self._db.get(dependency)
                if not dependency_item:
                    continue
                dependency_item.update_dependencies(
                    dependencies={self.format_identifier(): self.type()}, recursive=False)

    def _get_default_data_library(self):
        from tpDcc.libs.datalibrary.core import datalib
