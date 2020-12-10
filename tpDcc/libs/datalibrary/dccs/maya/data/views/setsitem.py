#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Maya sets item view implementation
"""

from __future__ import print_function, division, absolute_import

from tpDcc.libs.datalibrary.dccs.maya.core.views import dataitem


class SetsItemView(dataitem.MayaDataItemView):

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def load_from_current_values(self):
        """
        Loads the values from current selected objects
        """

        self.load(namespaces=self.namespaces())
