import os
import re
from functools import partial

from tpDcc.libs.datalibrary.core import datapart


class FileData(datapart.DataPart):

    DATA_TYPE = 'file'
    _split = re.compile('/|\.|,|-|:|_', re.I)

    @classmethod
    def can_represent(cls, identifier):
        try:
            if os.path.isfile(identifier):
                return True
        except Exception:
            pass

        return False

    def functionality(self):
        return dict(open=partial(FileData.open, self._id))

    def label(self):
        return os.path.basename(self.identifier())

    def mandatory_tags(self):
        tags = [part.lower() for part in self._split.split(self._id) if 2 < len(part) < 20]
        tags.append('*')
        return tags

    @staticmethod
    def open(file_path):
        print('Opening File : %s' % file_path)
