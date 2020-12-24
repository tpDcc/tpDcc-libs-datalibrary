import os
import re
from functools import partial

from tpDcc.libs.datalibrary.core import datapart


class CarnivoreTrait(datapart.DataPart):

    DATA_TYPE = 'carnivore'
    _split = re.compile('/|\.|,|-|:|_', re.I)
    _has_trait = re.compile('(carnivore|omnivore).*\.', re.I)

    @classmethod
    def can_represent(cls, identifier):
        if CarnivoreTrait._has_trait.search(identifier):
            return True

        return False

    def functionality(self):
        return dict(feed_meat=partial(CarnivoreTrait.feed_meat, self._id))

    def label(self):
        return os.path.basename(self.identifier())

    def mandatory_tags(self):
        return ['carnivore', 'meat', 'hunter']

    @staticmethod
    def feed_meat(file_path):
        print('Would feed this creature some meat...')
