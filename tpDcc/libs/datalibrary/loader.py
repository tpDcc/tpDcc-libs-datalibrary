#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Initialization module for tpDcc-libs-datalibrary
"""

from tpDcc.libs.datalibrary.managers import data


def init(*args, **kwargs):
    """
    Initializes library
    """

    # Make sure that data classes are initialized during library loading
    data.update_data_classes()
