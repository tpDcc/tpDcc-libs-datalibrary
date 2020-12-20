#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Maya ascii item view implementation
"""

from __future__ import print_function, division, absolute_import

from Qt.QtWidgets import QAction

from tpDcc.managers import resources

from tpDcc.libs.datalibrary.dccs.maya.core.views import dataitem


class MayaAsciiItemView(dataitem.MayaDataItemView):

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def context_menu(self, menu, items=None):
        """
        Returns the context menu for the item
        :return: QMenu
        """

        self._clean_student_license = QAction(resources.icon('student'), 'Clean Student License', menu)
        self._clean_student_license.triggered.connect(self.item.clean_student_license)
        menu.addAction(self._clean_student_license)
        menu.addSeparator()

        super(MayaAsciiItemView, self).context_menu(menu, items=items)
