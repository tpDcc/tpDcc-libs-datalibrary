#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Initialization module for tpDcc-libs-datalibrary
"""

from __future__ import print_function, division, absolute_import

import os
import logging.config

from tpDcc.core import library

LIB_ID = 'tpDcc-libs-datalibrary'
LIB_ENV = LIB_ID.replace('-', '_').upper()

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class DataLib(library.DccLibrary, object):
    def __init__(self, *args, **kwargs):
        super(DataLib, self).__init__(*args, **kwargs)

    @classmethod
    def config_dict(cls, file_name=None):
        base_tool_config = library.DccLibrary.config_dict(file_name=file_name)
        tool_config = {
            'name': 'Data Library',
            'id': LIB_ID,
            'supported_dccs': {'maya': ['2017', '2018', '2019', '2020']},
            'tooltip': 'Customizable and easy to use data library.'
        }
        base_tool_config.update(tool_config)

        return base_tool_config


def create_logger(dev=False):
    """
    Creates logger for current tpDcc-libs-datalibrary package
    """

    logger_directory = os.path.normpath(os.path.join(os.path.expanduser('~'), 'tpDcc', 'logs', 'libs'))
    if not os.path.isdir(logger_directory):
        os.makedirs(logger_directory)

    logging_config = os.path.normpath(os.path.join(os.path.dirname(__file__), '__logging__.ini'))

    logging.config.fileConfig(logging_config, disable_existing_loggers=False)
    logger = logging.getLogger('tpDcc-libs-datalibrary')
    dev = os.getenv('TPDCC_DEV', dev)
    if dev:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)

    return logger


create_logger()
