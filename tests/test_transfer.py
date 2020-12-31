#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains transfer objects tests for tpDcc-libs-datalibrary
"""

from __future__ import print_function, division, absolute_import

import os
import shutil

from tpDcc.libs.unittests.core import unittestcase

# from tpDcc.libs.datalibrary.core import transfer
#
#
# class TestTransfer(unittestcase.UnitTestCase()):
#     def __init__(self, *args, **kwargs):
#         super(TestTransfer, self).__init__(*args, **kwargs)
#
#     def setUp(self):
#         super(TestTransfer, self).setUp()
#
#         self._data_folder = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'tests_data')
#         if not os.path.isdir(self._data_folder):
#             os.makedirs(self._data_folder)
#
#     def tearDown(self):
#         super(TestTransfer, self).tearDown()
#
#         if os.path.isdir(self._data_folder):
#             shutil.rmtree(self._data_folder)


"""
import mutils

t = mutils.TransferObject.fromPath("/tmp/pose.json")
t = mutils.TransferObject.fromObjects(["object1", "object2"])

t.load(selection=True)
t.load(objects=["obj1", "obj2"])
t.load(namespaces=["namespace1", "namespace2"])

t.save("/tmp/pose.json")
t.read("/tmp/pose.json")
"""
