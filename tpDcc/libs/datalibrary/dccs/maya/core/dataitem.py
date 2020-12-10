#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains library data item implementation for Maya
"""

from __future__ import print_function, division, absolute_import

from tpDcc import dcc
from tpDcc.core import dcc as core_dcc
from tpDcc.libs.datalibrary.core import base


class MayaDataItem(base.BaseDataItem):

    SUPPORTED_DCCS = [core_dcc.Dccs.Maya]

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def load_schema(self):
        """
        Gets the options used to load the item
        :return: list(dict)
        """

        load_schema = super(MayaDataItem, self).load_schema()

        load_schema.extend([
            {
                'name': 'namespaceGroup',
                'title': 'Namespace',
                'type': 'group',
                'order': 10,
            },
            {
                'name': 'namespaceOption',
                'title': '',
                'type': 'radio',
                'value': 'From file',
                'items': ['From file', 'From selection', 'Use custom'],
                'persistent': True,
                'persistentKey': 'BaseItem',
            },
            {
                'name': 'namespaces',
                'title': '',
                'type': 'tags',
                'value': [],
                'items': dcc.client().list_namespaces(),
                'persistent': True,
                'label': {'visible': False},
                'persistentKey': 'BaseItem'
            }
        ])

        return load_schema

    def load_validator(self, **options):
        """
        Validates the current load options
        Called when the load fields change
        :param options: dict
        :return: list(dict)
        """

        namespaces = options.get('namespaces')
        namespace_option = options.get('namespaceOption')

        if namespace_option == 'From file':
            namespaces = self.transfer_object.namespaces()
        elif namespace_option == 'From selection':
            namespaces = dcc.list_namespaces_from_selection() or ['']

        field_changed = options.get('fieldChanged')
        if field_changed == 'namespaces':
            options['namespaceOption'] = 'Use custom'
        else:
            options['namespaceOption'] = namespaces

        self._current_load_values = options

        return [
            {
                "name": "namespaces",
                "value": options.get("namespaces")
            },
            {
                "name": "namespaceOption",
                "value": options.get("namespaceOption")
            },
        ]
