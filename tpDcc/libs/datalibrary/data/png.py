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


class PngImageData(datapart.DataPart):

    DATA_TYPE = 'image.png'
    PRIORITY = 5
    EXTENSION = '.png'

    _has_trait = re.compile(r'\.png$', re.I)

    @classmethod
    def can_represent(cls, identifier, only_extension=False):
        if PngImageData._has_trait.search(identifier):
            if only_extension:
                return True
            if os.path.isfile(identifier):
                return True
        return False

    def type(self):
        return 'image.png'

    def icon(self):
        return self.identifier()

    def extension(self):
        return '.png'

    def functionality(self):
        return dict(show=partial(os.system, self.identifier(),))

    def label(self):
        return os.path.basename(self.identifier())
