#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Initialization module for tpDcc-libs-datalibrary
"""

# import os
#
# from tpDcc import dcc

# def init(*args, **kwargs):
#     """
#     Initializes library
#     """
#
#     utils.register_item_classes_from_config()
#
#     default_items_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
#     default_dcc_items_path = os.path.join(os.path.dirname(default_items_path), 'dccs', dcc.get_name(), 'data')
#
#     for path in [default_items_path, default_dcc_items_path]:
#         data.add_directory(path, 'tpDcc', do_reload=True)
#
#     # Make sure that data classes are initialized during library loading
#     data.update_data_items()
