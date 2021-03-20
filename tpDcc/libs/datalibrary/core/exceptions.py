#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains consts exception used by data library
"""

from __future__ import print_function, division, absolute_import

from tpDcc.libs.python import path


class PathError(IOError, object):
    """
    Exception that supports unicode escape characters
    """

    def __init__(self, msg):
        msg = path.normalize_path(msg)
        super(PathError, self).__init__(msg)
        self._msg = msg

    def __unicode__(self):
        """
        Returns the decoded message using unicode_escape
        :return: str
        """

        msg = path.normalize_path(self._msg).decode('unicode_escape')
        return msg


class MovePathError(PathError):
    """
    Error related with path moving
    """

    pass


class RenamePathError(PathError):
    """
    Error related with path renaming
    """

    pass


class NoObjectFoundError(Exception):
    pass


class ItemError(Exception):
    pass


class ItemSaveError(Exception):
    pass


class ItemLoadError(Exception):
    pass


class AttributeError(Exception):
    pass


class DccUtilsError(Exception):
    pass


class NoMatchFoundError(DccUtilsError):
    pass


class ObjectsError(DccUtilsError):
    pass


class SelectionError(DccUtilsError):
    pass


class MoreThanOneObjectFoundError(DccUtilsError):
    pass


class ModelPanelNotInFocusError(DccUtilsError):
    pass
