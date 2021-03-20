#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains data library tests for tpDcc-libs-datalibrary
"""

from __future__ import print_function, division, absolute_import


from tpDcc.libs.unittests.core import unittestcase

from tpDcc.libs.datalibrary.core import datalib


class TestData(unittestcase.UnitTestCase()):
    def __init__(self, *args, **kwargs):
        super(TestData, self).__init__(*args, **kwargs)

    def data(self):
        data = list()
        data.append({'name': 'square', 'index': 3})
        data.append({'name': 'circle', 'index': 1})
        data.append({'name': 'box', 'index': 2})

        return data

    def data_dict(self, name, index):
        return {'name': name, 'index': index}


class TestSort(TestData):
    def __init__(self, *args, **kwargs):
        super(TestSort, self).__init__(*args, **kwargs)

    def test_sort_ascendant(self):
        sort_by = ['index:asc', 'name']
        data = self.data()
        ordered_data = datalib.DataLibrary.sorted(data, sort_by)

        self.assertEqual(ordered_data[0].get('index'), 1)
        self.assertEqual(ordered_data[1].get('index'), 2)
        self.assertEqual(ordered_data[2].get('index'), 3)

    def test_sort_descendant(self):
        sort_by = ['index:dsc', 'name']
        data = self.data()
        ordered_data = datalib.DataLibrary.sorted(data, sort_by)

        self.assertEqual(ordered_data[0].get('index'), 3)
        self.assertEqual(ordered_data[1].get('index'), 2)
        self.assertEqual(ordered_data[2].get('index'), 1)


class TestFilters(TestData):
    def __init__(self, *args, **kwargs):
        super(TestFilters, self).__init__(*args, **kwargs)

    def test_is(self):
        data1 = self.data_dict('circle', 3)
        data2 = self.data_dict('triangle', 3)
        queries = [{'filters': [('name', 'is', 'circle')]}]

        self.assertTrue(datalib.DataLibrary.match(data1, queries))
        self.assertFalse(datalib.DataLibrary.match(data2, queries))

    def test_startswith(self):
        data = self.data_dict('circle', 3)
        query1 = [{'filters': [('name', 'startswith', 'cir')]}]
        query2 = [{'filters': [('name', 'startswith', 'tri')]}]

        self.assertTrue(datalib.DataLibrary.match(data, query1))
        self.assertFalse(datalib.DataLibrary.match(data, query2))

    def test_operators(self):
        data = self.data_dict('circle', 3)
        query1 = [{'operator': 'or', 'filters': [('name', 'is', 'square'), ('name', 'is', 'circle')]}]
        query2 = [{'operator': 'and', 'filters': [('name', 'is', 'square'), ('name', 'is', 'circle')]}]
        query3 = [{'operator': 'and', 'filters': [('name', 'is', 'circle'), ('index', 'is', 3)]}]
        query4 = [{'operator': 'and', 'filters': [('name', 'is', 'circle'), ('index', 'is', '3')]}]

        self.assertTrue(datalib.DataLibrary.match(data, query1))
        self.assertFalse(datalib.DataLibrary.match(data, query2))
        self.assertTrue(datalib.DataLibrary.match(data, query3))
        self.assertFalse(datalib.DataLibrary.match(data, query4))
