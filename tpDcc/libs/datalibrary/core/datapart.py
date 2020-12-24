#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base DataPart class implementation. This is the class all data inherit
and their compositions are used to represent data
"""

from __future__ import print_function, division, absolute_import

import os

from tpDcc.libs.python import composite


class DataPart(composite.Composition):
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

    # Defines whether or not this item allow deletion and nested hierarchies
    ENABLE_DELETE = True
    ENABLE_NESTED_ITEMS = False

    def __init__(self, identifier, db):
        super(DataPart, self).__init__()

        self._id = identifier
        self._db = db

    def __repr__(self):
        base_repr = super(DataPart, self).__repr__()
        return base_repr.replace('DataPart', 'DataPart: {}'.format(self._id))

    # ============================================================================================================
    # ABSTRACT FUNCTIONS
    # ============================================================================================================

    @classmethod
    def can_represent(cls, identifier):
        """
        Returns whether or not this plugin can represent the given identifier
        :param identifier: str, data identifier. This could be a URL, a file path, a UUID, etc
        :return: bool
        """

        return False

    @classmethod
    def menu_name(cls):
        """
        Defines the display name that should appear in the create data menus. If not given, data part will not appear
        in data creation menus
        :return: str or None
        """

        return None

    @classmethod
    def save_schema(cls):
        """
        Returns the schema used for saving the item
        :return: dict
        """

        return [
            {
                'name': 'folder',
                'type': 'path',
                'layout': 'vertical',
                'visible': False
            },
            {
                'name': 'name',
                'type': 'string',
                'layout': 'vertical'
            },
            {
                'name': 'comment',
                'type': 'text',
                'layout': 'vertical'
            }
        ]

    @composite.first_true
    def type(self):
        """
        Returns type of the file
        :return: str
        """

        return "Data"

    @composite.first_true
    def label(self):
        """
        Returns the label or name for the DataPart. This would be the pretty or display name and oes not need to be
        unique. If multiple DataParts are bound to represent a piece of information then the first to return a
        non-false return will be taken
        :return: str or None
        """

        return None

    @composite.first_true
    def icon(self):
        """
        Returns the icon for the DataPart. If multiple data parts are bound to represent a piece of information
        the the first to return a non-false return will be taken.
        :return: str or None
        """

        return False

    @composite.extend_unique
    def mandatory_tags(self):
        """
        Returns any tags that should always be assigned to this data element. In a situation where multiple DataParts
        are bound then the combined results of all the mandatory tags are used.
        :return: list(str) or None
        """

        return None

    @composite.update_dictionary
    def functionality(self):
        """
        Exposes per-data functionality in the form of a dictionary where the key is the string accessor, and the value
        is a callable. In a situation where multiple DataParts are bound then a single dictionary with all the entries
        combined is returned.
        :return: dict
        """

        return composite.Ignore

    @composite.update_dictionary
    def metadata_dict(self):
        """
        Exposes per-metadata functionality in the form of a dictionary where the key is the string accessor, and the value
        is a callable. In a situation where multiple DataParts are bound then a single dictionary with all the entries
        combined is returned.
        :return: dict
        """

        return composite.Ignore

    @composite.extend_unique
    def supported_dccs(self):
        """
        Returns a list of DCC names this data can be loaded into. In a situation where multiple DataParts are bound
        then the combined results of all the mandatory tags are used.
        :return: list(str) or None
        """

        return None

    @composite.extend_results
    def load_schema(self):
        """
        Gets the options used to load the item
        :return: list(dict)
        """

        return list()

    @composite.extend_results
    def save_validator(self, **fields):
        """
        Validates the given save fields
        Called when an input field has changed
        :param fields: dict
        :return: list(dict)
        """

        pass

    @composite.extend_results
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

        return self._db.format_identifier(self.identifier())

    def name(self):
        """
        Returns data name
        :return: str
        """

        return os.path.splitext(os.path.basename(self.identifier()))[0]

    def data(self):
        """
        Returns data dictionary.
        :return: dict
        """

        data = self._db.find_data(self._id)
        if not data:
            return dict()

        return list(data.values())[0]

    def metadata(self):
        """
        Returns metadata data dictionary.
        :return: dict
        """

        return self.data().get('metadata' or dict())

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
        :param tag: list(str) or str, tag or list of tags we want to remove from this DataPart
        :return:
        """

        return self._db.untag(self._id, tags)
