#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base class to define data transfer objects for Maya
"""

from tpDcc import dcc

from tpDcc.dccs.maya.core import namespace, reference

from tpDcc.libs.datalibrary.core import transfer


class MayaDataTransferObject(transfer.BaseDataTransferObject):

    # =================================================================================================================
    # OVERRIDES
    # =================================================================================================================

    def validate(self, **kwargs):
        """
        Validates the given keyword arguments for the current data transfer object
        :param kwargs: dict
        :return: bool
        """

        namespaces = kwargs.get('namespaces', None)
        if namespaces is not None:
            scene_namespaces = namespace.get_all_namespaces() + [':']
            for ns in namespaces:
                if ns and ns not in scene_namespaces:
                    raise ValueError('Namespace "{}" does not exist in current scene!'.format(ns))

        return True

    def _set_metadata(self):
        """
        Internal function that sets the metadata of the data transfer object
        Called before saving the data
        """

        super(MayaDataTransferObject, self)._set_metadata()

        references = reference.get_reference_data(list(self.objects().keys()))

        self.set_metadata('references', references)
        self.set_metadata('maya_version', dcc.get_version())
        self.set_metadata('maya_scene_file', dcc.scene_name())

    # =================================================================================================================
    # BASE
    # =================================================================================================================

    def namespaces(self):
        """
        Returns the namespaces contained in the transfer object
        :return: list(str)
        """

        if self._namespaces is None:
            group_namespaces = dict()
            for name in self.objects():
                node_namespace = namespace.get_namespace(name)
                if not node_namespace:
                    continue
                group_namespaces.setdefault(dcc.node_short_name(name), list())
                group_namespaces[node_namespace].append(name)
            self._namespaces = list(group_namespaces.keys())

        return self._namespaces
