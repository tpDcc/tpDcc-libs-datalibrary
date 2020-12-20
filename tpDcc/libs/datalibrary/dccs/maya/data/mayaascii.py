#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Maya ASCII file item implementation
"""

from __future__ import print_function, division, absolute_import

import os
import stat
import shutil
import logging

from tpDcc import dcc
from tpDcc.libs.python import path as path_utils

from tpDcc.libs.datalibrary.dccs.maya.core import dataitem
from tpDcc.libs.datalibrary.dccs.maya.core import transfer

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class MayaAsciiData(dataitem.MayaDataItem):

    EXTENSION = '.ma'

    ICON_NAME = 'maya'
    MENU_NAME = 'Maya ASCII'

    TRANSFER_CLASS = transfer.MayaTransferObject

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

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

    def load(self, *args, **kwargs):
        """
        Loads the data from the transfer object
        :param args: list
        :param kwargs: dict
        """

        LOGGER.debug('Loading: {} | {}'.format(self.path, kwargs))

        result = dcc.client().open_file(file_path=self.path)
        dcc.client().fit_view(animation=True)

        LOGGER.debug('Loaded: {} | {}'.format(self.path, kwargs))

        return result

    def import_data(self, *args, **kwargs):
        """
        Imports data to current DCC
        :param args: list
        :param kwargs: dict
        """

        LOGGER.debug('Importing: {} | {}'.format(self.path, kwargs))

        result = dcc.client().import_file(file_path=self.path)

        LOGGER.debug('Imported: {} | {}'.format(self.path, kwargs))

        return result

    def reference_data(self, *args, **kwargs):
        """
        References data to current DCC
        :param args: list
        :param kwargs: dict
        """

        LOGGER.debug('Referencing: {} | {}'.format(self.path, kwargs))

        result = dcc.client().reference_file(file_path=self.path)

        LOGGER.debug('Referenced: {} | {}'.format(self.path, kwargs))

        return result

    def save(self, thumbnail='', **kwargs):
        """
        Saves all the given data to the item path on disk
        :param thumbnail: str
        :param kwargs: dict
        """

        LOGGER.debug('Saving {} | {}'.format(self.path, kwargs))

        super(MayaAsciiData, self).save(thumbnail=thumbnail, **kwargs)

        item_name = kwargs.get('name', 'mayaascii')
        save_path = self.path + '/{}{}'.format(item_name, self.EXTENSION)

        # self.transfer_object(save=True).save(self.transfer_path())
        dcc.client().save_dcc_file(save_path)

        LOGGER.debug('Saved {} | {}'.format(self.path, kwargs))

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def clean_student_license(self):
        """
        Cleans student license from Maya ASCII file
        """

        filename = self.path
        if not path_utils.is_file(filename):
            LOGGER.warning('Impossible to reference invalid data file: {}'.format(filename))
            return

        changed = False

        if not os.path.exists(filename):
            LOGGER.error('File "{}" does not exists!'.format(filename))
            return False

        if not self.has_student_line(filename):
            LOGGER.info('File is already cleaned: no student line found!')
            return False

        if not filename.endswith('.ma'):
            LOGGER.info('Maya Binary files cannot be cleaned!')
            return False

        with open(filename, 'r') as f:
            lines = f.readlines()
        step = len(lines) / 4

        no_student_filename = filename[:-3] + '.no_student.ma'
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
            os.chmod(filename, stat.S_IWUSR | stat.S_IREAD)
            shutil.copy2(no_student_filename, filename)

            try:
                os.remove(no_student_filename)
            except Exception as exc:
                LOGGER.warning('Error while cleanup no student file process files ... >> {}'.format(exc))
                return False

            LOGGER.info('Student file cleaned successfully from file: "{}"!'.format(filename))

        return True

    def has_student_line(self, filename):
        """
        Returns True if the given Maya file has a student license on it
        :param filename: str
        :return: bool
        """

        if not os.path.exists(filename):
            LOGGER.error('File "{}" does not exists!'.format(filename))
            return False

        if filename.endswith('.mb'):
            LOGGER.warning('Student License Check is not supported in binary files!')
            return True

        with open(filename, 'r') as f:
            lines = f.readlines()

        for line in lines:
            if 'createNode' in line:
                return False
            if 'fileInfo' in line and 'student' in line:
                return True

        return False
