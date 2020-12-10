#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains Maya ASCII file item implementation
"""

from __future__ import print_function, division, absolute_import

from tpDcc.libs.datalibrary.dccs.maya.data import mayaascii


class MayaBinaryData(mayaascii.MayaAsciiData):

    EXTENSION = '.mb'

    MENU_NAME = 'Maya Binary'

    def _transfer_name(self):
        """
        Internal function that returns the transfer name that should be used
        :return: str
        """

        return 'mayabinary'
