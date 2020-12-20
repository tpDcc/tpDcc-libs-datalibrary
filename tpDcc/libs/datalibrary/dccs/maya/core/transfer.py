#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains transfer data item  implementation for Maya
"""

from __future__ import print_function, division, absolute_import

import time
import locale
import getpass

from tpDcc import dcc
from tpDcc.libs.datalibrary import __version__
from tpDcc.libs.datalibrary.core import transfer
from tpDcc.libs.datalibrary.dccs.maya.core import utils


class MayaTransferObject(transfer.BaseTransferObject):
    def __init__(self):
        super(MayaTransferObject, self).__init__()

        self._namespaces = None

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def validate(self, **kwargs):
        """
        Validates the given keyword arguments for the current IO object
        :param kwargs: dict
        """

        namespaces = kwargs.get('namespaces')
        if namespaces is not None:
            scene_namespaces = dcc.client().scene_namespaces()
            for namespace in namespaces:
                if namespace and namespace not in scene_namespaces:
                    msg = 'The namespace "{}" does not exists in the scene! ' \
                          'Please choose a namespace which exists.'.format(namespace)
                    raise ValueError(msg)

    def data_to_save(self):
        """
        Returns data to save
        Can be override to store custom data
        :return: dict
        """

        encoding = locale.getpreferredencoding()
        user = getpass.getuser()
        if user:
            try:
                user = user.decode(encoding)
            except AttributeError:
                user = str(user)

        ctime = str(time.time()).split('.')[0]
        references = utils.get_reference_data(self.objects())

        self.set_metadata('user', user)
        self.set_metadata('ctime', ctime)
        self.set_metadata("version", str(__version__.get_version()))
        self.set_metadata('references', references)
        self.set_metadata('mayaVersion', str(dcc.client().get_version()))
        self.set_metadata('mayaSceneFile', dcc.client().scene_name())

        metadata = {'metadata': self.metadata()}
        data = self.dump(metadata)[:-1] + ','

        objects = {'objects': self.objects()}
        data += self.dump(objects)[1:]

        return data

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def namespaces(self):
        """
        Returns the namespaces contained in the transfer object
        :return: list(str)
        """

        if self._namespaces is None:
            group = utils.group_objects(self.objects())
            self._namespaces = group.keys()

        return self._namespaces
