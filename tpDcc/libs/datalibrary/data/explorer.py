#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains explorer data part implementation
"""

from __future__ import print_function, division, absolute_import

import os
from functools import partial

from Qt.QtWidgets import QApplication

from tpDcc.libs.python import timedate, folder as folder_utils

from tpDcc.libs.datalibrary.core import datapart


class ExplorerData(datapart.DataPart):

    DATA_TYPE = 'explorer'
    PRIORITY = 1

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    @classmethod
    def can_represent(cls, identifier, only_extension=False):

        if only_extension:
            return True

        try:
            if os.path.exists(identifier):
                return True
        except Exception:
            pass

        return False

    def functionality(self):
        return dict(
            show_in_explorer=partial(ExplorerData.show_in_explorer, self.format_identifier()),
            copy_path_to_clipboard=partial(ExplorerData.copy_path_to_clipboard, self.format_identifier())
        )

    def label(self):
        return os.path.basename(self.identifier())

    def mandatory_tags(self):
        return ['*']

    def load_schema(self):

        modified = self.data().get('ctime')
        if modified:
            modified = timedate.time_ago(modified)

        # count = self.transfer_object.object_count()
        count = 0
        plural = 's' if count > 1 else ''
        contains = '{} Object{}'.format(count, plural)

        return [
            {
                'name': 'infoGroup',
                'title': 'Info',
                'type': 'group',
                'order': 1
            },
            {
                "name": "name",
                "value": self.name(),
            },
            {
                "name": "owner",
                # "value": self.transfer_object.owner(),
                "value": 'tomi'
            },
            {
                "name": "created",
                "value": modified,
            },
            {
                "name": "contains",
                "value": contains,
            },
            {
                "name": "comment",
                # "value": self.transfer_object.description() or "No comment",
                "value": ''
            }
        ]

    # ============================================================================================================
    # STATIC FUNCTIONS
    # ============================================================================================================

    @staticmethod
    def show_in_explorer(filepath):
        """
        Opens OS explorer where data is located
        """

        if os.path.isdir(filepath):
            folder_utils.open_folder(filepath)
        elif os.path.isfile(filepath):
            folder_utils.open_folder(os.path.dirname(filepath))

    @staticmethod
    def copy_path_to_clipboard(filepath):
        """
        Copies the item path to the system clipboard
        """

        clipboard = QApplication.clipboard()
        clipboard.clear(mode=clipboard.Clipboard)
        clipboard.setText(filepath, mode=clipboard.Clipboard)
