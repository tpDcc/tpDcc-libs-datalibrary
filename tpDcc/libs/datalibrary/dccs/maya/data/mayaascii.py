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

from tpDcc.libs.datalibrary.core import consts, datapart

# NOTE: only import specific DCCs module if we inside Maya
if dcc.is_maya():
    import maya.cmds

logger = logging.getLogger(consts.LIB_ID)


class MayaAsciiData(datapart.DataPart):

    DATA_TYPE = 'maya.ascii'
    MENU_ICON = 'maya'
    MENU_NAME = 'Maya ASCII'
    PRIORITY = 10
    EXTENSION = '.ma'

    _has_trait = re.compile(r'\.ma$', re.I)

    @classmethod
    def can_represent(cls, identifier, only_extension=False):
        if MayaAsciiData._has_trait.search(identifier):
            if only_extension:
                return True
            if os.path.isfile(identifier):
                return True

        return False

    @classmethod
    def supported_dccs(cls):
        return [core_dcc.Dccs.Maya]

    @classmethod
    def metadata_dict(cls):

        # references = utils.get_reference_data(self.metadata().get('objects', list()))

        return {
            # 'references': references,
            'references': list(),
            'mayaVersion': str(dcc.get_version())
        }

    def label(self):
        return os.path.basename(self.identifier())

    def icon(self):
        return 'maya'

    def extension(self):
        return '.ma'

    def type(self):
        return 'maya.ascii'

    def menu_name(self):
        return 'Maya ASCII'

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
            namespaces = list()
            # namespaces = self.metadata().get('namespaces', list())
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

    def functionality(self):
        return dict(
            load=self.load,
            import_data=self.import_data,
            reference_data=self.reference_data,
            export_data=self.export_data,
            save=self.save,
            clean_student_license=self.clean_student_license
        )

    def load(self):
        """
        Loads Maya ASCII file in current DCC scene
        """

        filepath = self.format_identifier()
        if not filepath or not os.path.isfile(filepath):
            logger.warning('Impossible to open Maya ASCII file data from: "{}"'.format(filepath))
            return

        return dcc.open_file(filepath)

    def import_data(self):
        """
        Imports Maya ASCII file into current Maya scene
        """

        filepath = self.format_identifier()
        if not filepath or not os.path.isfile(filepath):
            return

        return dcc.import_file(filepath)

    def reference_data(self):
        """
        References Maya file into curreent Maya scene
        """

        filepath = self.format_identifier()
        if not filepath or not os.path.isfile(filepath):
            return

        dcc.reference_file(filepath)

    def export_data(self, *args, **kwargs):
        return self.save(*args, **kwargs)

    def save(self, *args, **kwargs):
        """
        Saves Maya ASCII file
        """

        filepath = self.format_identifier()
        if not filepath:
            logger.warning('Impossible to save Maya ASCII file because save file path not defined!')
            return

        logger.debug('Saving {} | {}'.format(filepath, kwargs))

        maya_type = 'mayaBinary' if filepath.endswith('.mb') else 'mayaAscii'

        # selection = maya.cmds.ls(sl=True)
        # if selection:
        #     maya.cmds.file(
        #         file_path, type=maya_type, options='v=0;', preserveReferences=True, exportSelected=selection)
        # else:
        maya.cmds.file(rename=filepath)
        result = maya.cmds.file(type=maya_type, options='v=0;', preserveReferences=True, save=True)

        logger.debug('Saved {} successfully!'.format(filepath))

        return result

    def clean_student_license(self):
        file_path = self.format_identifier()
        if not file_path or not os.path.isfile(file_path):
            logger.warning('Impossible to clean student license in invalid data file: {}'.format(file_path))
            return

        if not file_path.endswith('.ma'):
            logger.info('Maya Binary files cannot be cleaned!')
            return False

        changed = False

        if file_path.endswith('.mb'):
            logger.warning('Student License Check is not supported in binary files!')
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
            logger.info('File is already cleaned: no student line found!')
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
                    logger.debug('Updating File: {}% ...'.format(100 / (len(lines) / step_count)))
                    step += step

        if changed:
            os.chmod(file_path, stat.S_IWUSR | stat.S_IREAD)
            shutil.copy2(no_student_filename, file_path)

            try:
                os.remove(no_student_filename)
            except Exception as exc:
                logger.warning('Error while cleanup no student file process files ... >> {}'.format(exc))
                return False

            logger.info('Cleaned student license from file: {}'.format(file_path))
