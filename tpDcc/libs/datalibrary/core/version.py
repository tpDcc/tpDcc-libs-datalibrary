#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains base version control implementation
"""

from __future__ import print_function, division, absolute_import

import os
import logging
from collections import OrderedDict

from tpDcc.libs.datalibrary.core import consts

LOGGER = logging.getLogger(consts.LIB_ID)

GIT_AVAILABLE = True
try:
    from git import Repo
except Exception as exc:
    LOGGER.warning(
        'Impossible to import GitPython library:\n\t{}\nGit related functionality will not be available!'.format(exc))
    GIT_AVAILABLE = False

from tpDcc.libs.python import decorators
from tpDcc.libs.qt.core import base
from tpDcc.libs.qt.widgets import directory


class VersionControl(object):

    @staticmethod
    @decorators.abstractmethod
    def get_commits_that_modified_a_file(file_path):
        """
        Returns a dictionary containing all the commits that modified a specific file
        :param file_path: str
        :return: dict
        """

        pass

    @staticmethod
    @decorators.abstractmethod
    def sync_file(file_path, commit_id):
        """
        Synchronizes the file status for a specific commit
        :param file_path: str
        :param commit_id: str
        :return:
        """

        pass


class VersionWidget(base.BaseWidget):
    def __init__(self, version_object, parent=None):
        super(VersionWidget, self).__init__(parent=parent)

        self._git = version_object

    def ui(self):
        super(VersionWidget, self).ui()

        self._repo_line = directory.SelectFolder(label_text='Repo Folder', parent=self)
        self.main_layout.addWidget(self._repo_line)
        self.main_layout.addStretch()

    def get_repository_path(self):
        return self._repo_line.get_directory() or ''

    def set_repository_path(self, repository_path):
        repository_path = repository_path or ''
        if not os.path.isdir(repository_path):
            repository_path = ''

        self._repo_line.set_directory(repository_path)


class GitVersionControl(VersionControl):

    @staticmethod
    def is_valid_repository_directory(repository_path):
        """
        Returns whether or not given path contains a valid repository
        :param repository_path: str
        :return: bool
        """

        if not GIT_AVAILABLE:
            return False

        repo = GitVersionControl._get_repo(repository_path)
        if not repo:
            return False

        return True

    @staticmethod
    def get_commits_that_modified_a_file(repository_path, file_path):
        """
        Returns a dictionary containing all the commits that modified a specific file
        :param file_path: str
        :return: dict
        """

        commits = OrderedDict()
        if not GIT_AVAILABLE:
            return commits
        repo = GitVersionControl._get_repo(repository_path)
        if not repo:
            return commits
        comits_str = repo.git.log(file_path, follow=True)
        if not comits_str:
            return commits

        commits = GitVersionControl._parse_data(comits_str)

        return commits

    @staticmethod
    def get_commit_data(repository_path, file_path):
        commit = OrderedDict()
        if not GIT_AVAILABLE:
            return commit
        repo = GitVersionControl._get_repo(repository_path)
        if not repo:
            return commit
        comit_str = repo.git.log(file_path, n=1)
        if not comit_str:
            return commit

        commit = GitVersionControl._parse_data(comit_str)

        return commit

    @staticmethod
    def sync_file(repository_path, file_path, commit_id):
        """
        Synchronizes the file status for a specific commit
        :param file_path: str
        :param commit_id: str
        :return:
        """

        if not GIT_AVAILABLE:
            return

        repo = GitVersionControl._get_repo(repository_path)
        if not repo:
            return

        return repo.git.checkout(commit_id, file_path)

    @staticmethod
    def sync_files(repository_path, commit_id):
        """
        Synchronizes all the files for a specific commit
        :param repository_path: str
        :param commit_id: str
        :return:
        """

        if not GIT_AVAILABLE:
            return

        repo = GitVersionControl._get_repo(repository_path)
        if not repo:
            return

        return repo.git.checkout(commit_id)

    @staticmethod
    def sync_commit(repository_path, commit_id):
        """
        Synchronizes the commit with given id
        :param repository_path: str
        :param commit_id: str
        :return:
        """

        if not GIT_AVAILABLE:
            return

        repo = GitVersionControl._get_repo(repository_path)
        if not repo:
            return

        return repo.git.checkout(commit_id)

    @staticmethod
    def get_files_in_commit(repository_path, commit_id):
        """
        Returns a list with all files in a specific commit
        :param repository_path: str
        :param commit_id: str
        :return: list(str)
        """

        if not GIT_AVAILABLE:
            return list()

        repo = GitVersionControl._get_repo(repository_path)
        if not repo:
            return list()

        commit = repo.commit(commit_id)
        if not commit:
            return list()

        return commit.tree

    @staticmethod
    def _get_repo(repository_path):
        """
        Internal function that safely returns a valid repository
        :param repository_path: str
        :return: git.Repo or None
        """

        if not GIT_AVAILABLE or not os.path.isdir(repository_path):
            return False

        try:
            repo = Repo(repository_path)
            return repo
        except Exception:
            pass

        return None

    @staticmethod
    def _parse_data(commit_data):
        commits = OrderedDict()
        current_commit = None
        lines = commit_data.split('\n')
        for line in lines:
            if not line:
                continue
            if line.startswith('commit'):
                current_commit = line.split(' ')[-1]
                commits[current_commit] = dict()
            if line.startswith('Author:'):
                commit_author = line.replace('Author:', '').lstrip()
                commit_author_split = commit_author.split('<')
                commits[current_commit]['author'] = commit_author_split[0].rstrip()
                commits[current_commit]['email'] = commit_author_split[-1].split('>')[0]
            elif line.startswith('Date:'):
                commit_date = line.replace('Date:', '').lstrip()
                commits[current_commit]['date'] = commit_date
            else:
                commits[current_commit]['message'] = line.lstrip()

        return commits


class GitVersionWigdet(VersionWidget):
    def __init__(self, parent=None):
        super(GitVersionWigdet, self).__init__(version_object=GitVersionControl(), parent=parent)
