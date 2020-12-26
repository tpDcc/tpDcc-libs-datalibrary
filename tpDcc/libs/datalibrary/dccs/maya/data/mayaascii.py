#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Maya ascii data part implementation
"""

from __future__ import print_function, division, absolute_import

import os
import re
import stat
import shutil
import logging

from tpDcc import dcc
from tpDcc.core import dcc as core_dcc

from tpDcc.libs.datalibrary.core import datapart
from tpDcc.libs.datalibrary.dccs.maya.core import utils

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class MayaAsciiData(datapart.DataPart):

    DATA_TYPE = 'maya.ascii'
    MENU_ICON = 'maya'
    PRIORITY = 10
    EXTENSION = '.ma'

    _has_trait = re.compile('\.ma$', re.I)

    @classmethod
    def can_represent(cls, identifier):
        if MayaAsciiData._has_trait.search(identifier):
            if os.path.isfile(identifier):
                return True

        return False

    @classmethod
    def supported_dccs(cls):
        return [core_dcc.Dccs.Maya]

    @classmethod
    def menu_name(cls):
        return 'Maya ASCII'

    def label(self):
        return os.path.basename(self.identifier())

    def icon(self):
        return 'maya'

    def type(self):
        return 'Maya ASCII'

    def save_schema(self):
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
                "name": "name",
                "type": "string",
                "layout": "vertical"
            },
            {
                "name": "objects",
                "type": "objects",
                "layout": "vertical"
            }
        ]

    def load_schema(self):

        return [
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
                'persistentKey': 'MayaAsciiData',
            },
            {
                'name': 'namespaces',
                'title': '',
                'type': 'tags',
                'value': [],
                'items': dcc.client().list_namespaces(),
                'persistent': True,
                'label': {'visible': False},
                'persistentKey': 'MayaAsciiData'
            }
        ]

    def load_validator(self, **options):
        namespaces = options.get('namespaces')
        namespace_option = options.get('namespaceOption')

        if namespace_option == 'From file':
            namespaces = self.metadata().get('namespaces', list())
        elif namespace_option == 'From selection':
            namespaces = dcc.client().list_namespaces_from_selection() or ['']

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
            }
        ]

    def metadata_dict(self):

        references = utils.get_reference_data(self.metadata().get('objects', list()))

        return {
            'references': references,
            'mayaVersion': str(dcc.client().get_version())
        }

    def functionality(self):
        return dict(
            load=self.load,
            save=self.save,
            clean_student_license=self.clean_student_license
        )

    def load(self):
        """
        Opens OS explorer where data is located
        """

        filepath = self.format_identifier()
        if not filepath.endswith(MayaAsciiData.EXTENSION):
            filepath = '{}{}'.format(filepath, MayaAsciiData.EXTENSION)

        if not filepath or not os.path.isfile(filepath):
            return

        dcc.client().open_file(filepath)

    def save(self):
        """
        Opens OS explorer where data is located
        """

        filepath = self.format_identifier()
        if not filepath.endswith(MayaAsciiData.EXTENSION):
            filepath = '{}{}'.format(filepath, MayaAsciiData.EXTENSION)

        if not filepath or os.path.isfile(filepath):
            return

        return dcc.client().save_dcc_file(filepath)

    def clean_student_license(self):
        file_path = self.format_identifier()
        if not file_path or not os.path.isfile(file_path):
            LOGGER.warning('Impossible to clean student license in invalid data file: {}'.format(file_path))
            return

        if not file_path.endswith('.ma'):
            LOGGER.info('Maya Binary files cannot be cleaned!')
            return False

        changed = False

        if file_path.endswith('.mb'):
            LOGGER.warning('Student License Check is not supported in binary files!')
            return True

        with open(file_path, 'r') as f:
            lines = f.readlines()

        has_student_license = False
        for line in lines:
            if 'createNode' in line:
                break
            if 'fileInfo' in line and 'student' in line:
                has_student_license = True
                break
        if not has_student_license:
            LOGGER.info('File is already cleaned: no student line found!')
            return False

        with open(file_path, 'r') as f:
            lines = f.readlines()
        step = len(lines) / 4

        no_student_filename = file_path[:-3] + '.no_student.ma'
        with open(no_student_filename, 'w') as f:
            step_count = 0
            for line in lines:
                step_count += 1
                if 'fileInfo' in line:
                    if 'student' in line:
                        changed = True
                        continue
                f.write(line)
                if step_count > step:
                    LOGGER.debug('Updating File: {}% ...'.format(100 / (len(lines) / step_count)))
                    step += step

        if changed:
            os.chmod(file_path, stat.S_IWUSR | stat.S_IREAD)
            shutil.copy2(no_student_filename, file_path)

            try:
                os.remove(no_student_filename)
            except Exception as exc:
                LOGGER.warning('Error while cleanup no student file process files ... >> {}'.format(exc))
                return False

            LOGGER.info('Cleaned student license from file: {}'.format(file_path))
