#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains library animation pose item widget implementation
"""

from __future__ import print_function, division, absolute_import


from tpDcc.libs.datalibrary.core.views import base


class PoseItemViewView(base.BaseDataItemView):

    MENU_NAME = 'Pose'
    EXTENSION = '.pose'

    def __init__(self, *args, **kwargs):
        super(PoseItemViewView, self).__init__(*args, **kwargs)

        self._options = None
        self._batch_mode = False
