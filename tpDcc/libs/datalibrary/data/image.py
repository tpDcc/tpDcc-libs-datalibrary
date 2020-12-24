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


class ImageData(datapart.DataPart):

    data_type = 'png'
    PRIORITY = 5

    # TODO: Support more image file extensions
    _has_trait = re.compile('\.png$', re.I)

    @classmethod
    def can_represent(cls, identifier):
        if ImageData._has_trait.search(identifier):
            if os.path.exists(identifier):
                return True
        return False

    def icon(self):
        return self.identifier()

    def functionality(self):
        return dict(show=partial(os.system, self.identifier(),))

    def label(self):
        return os.path.basename(self.identifier())
