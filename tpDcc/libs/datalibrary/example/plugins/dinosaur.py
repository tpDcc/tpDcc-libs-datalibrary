import os
import re
from functools import partial

from tpDcc.libs.datalibrary.core import datapart


class DinosaurTrait(datapart.DataPart):

    DATA_TYPE = 'dinosaur'
    _split = re.compile('/|\.|,|-|:|_', re.I)
    _has_trait = re.compile('dinosaur.*\.', re.I)

    @classmethod
    def can_represent(cls, identifier):
        if DinosaurTrait._has_trait.search(identifier):
            return True

        return False

    def functionality(self):
        return dict(feed_meat=partial(DinosaurTrait.is_dead, self._id))

    def label(self):
        return os.path.basename(self.identifier())

    def mandatory_tags(self):
        return ['dinosaur']

    @staticmethod
    def is_dead(file_path):
        return True
