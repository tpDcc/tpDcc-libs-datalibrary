#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains image data part implementation
"""

from __future__ import print_function, division, absolute_import

import os
import re
from functools import partial

from tpDcc.libs.datalibrary.core import datapart


class JpgImageData(datapart.DataPart):

    DATA_TYPE = 'image.jpg'
    PRIORITY = 5
    EXTENSION = '.jpg'

    _has_trait = re.compile('\.jpg$', re.I)

    @classmethod
    def can_represent(cls, identifier):
        if JpgImageData._has_trait.search(identifier):
            if os.path.isfile(identifier):
                return True
        return False

    def type(self):
        return 'image.jpg'

    def icon(self):
        return self.identifier()

    def functionality(self):
        return dict(show=partial(os.system, self.identifier(),))

    def label(self):
        return os.path.basename(self.identifier())
