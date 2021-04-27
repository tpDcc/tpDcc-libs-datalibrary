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

    _has_trait = re.compile(r'\.jpg$', re.I)

    @classmethod
    def can_represent(cls, identifier, only_extension=False):
        if JpgImageData._has_trait.search(identifier):
            if only_extension:
                return True
            if os.path.isfile(identifier):
                return True
        return False

    def type(self):
        return 'image.jpg'

    def icon(self):
        return self.format_identifier()

    def extension(self):
        return '.jpg'

    def functionality(self):
        return dict(show=partial(os.system, self.format_identifier(),))

    def label(self):
        return os.path.basename(self.format_identifier())
