#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base DataPart class implementation. This is the class all data inherit
and their compositions are used to represent data
"""

from __future__ import print_function, division, absolute_import

from tpDcc.libs.python import decorators, composite


class DataPart(composite.Composition):
    """
    A DataPart is a block of functionality and an interface to a piece of data. A piece of data can be
    represented by multiple DataParts in a composite form
    """

    # Allows to define a unique identifier fo the type of data. When querying from data base this will
    # form part of the composition string
    data_type = ''

    # Useful when we wwant to reimplement a plugin with the same data type as another plugin. In this
    # way, only the highest version will be used.
    version = 1

    # Priority to determine the order of class composition. Higher values mean the class will be
    # composited first. This can have an effect on methods decorated with composite decorators.
    priority = 1

    def __init__(self, identifier, db):
        super(DataPart, self).__init__()

        self._id = identifier
        self._db = db

    def __repr__(self):
        base_repr = super(DataPart, self).__repr__()
        return base_repr.replace('DataPart', 'DataPart: {}'.format(self._id))

    @classmethod
    @decorators.abstractmethod
    def can_represent(cls, identifier):
        """
        Returns whether or not this plugin can represent the given identifier
        :param identifier: str, data identifier. This could be a URL, a file path, a UUID, etc
        :return: bool
        """

        return False

    @composite.first_true
    @decorators.abstractmethod
    def icon(self):
        """
        Returns the icon for the DataPart. If multiple data parts are bound to represent a piece of information
        the the first to return a non-false return will be taken.
        :return: str or None
        """

        return None

    @composite.first_true
    @decorators.abstractmethod
    def label(self):
        """
        Returns the label or name for the DataPart. This would be the pretty or display name and oes not need to be
        unique. If multiple DataParts are bound to represent a piece of information then the first to return a
        non-false return will be taken
        :return: str or None
        """

        return None

    @composite.extend_unique
    @decorators.abstractmethod
    def mandatory_tags(self):
        """
        Returns any tags that should always be assigned to this data element. In a situation where multiple DataParts
        are bound then the combined results of all the mandatory tags are used.
        :return: list(str) or None
        """

        return None

    @composite.update_dictionary
    @decorators.abstractmethod
    def functionality(self):
        """
        Exposes per-data functionality in the form of a dictionary where the key is the string accessor, and the value
        is a callable. In a situation where multiple DataParts are bound then a single dictionary with all the entries
        combined is returned.
        :return: dict
        """

        return composite.Ignore

    def identifier(self):
        """
        Returns the identifier of this data part
        :return: str
        """

        return self._id

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
