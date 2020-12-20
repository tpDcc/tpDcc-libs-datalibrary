#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module that contains library data item widget implementation
"""

from __future__ import print_function, division, absolute_import

import os
import logging
import traceback
from functools import partial

from Qt.QtCore import Qt, QUrl
from Qt.QtWidgets import QApplication, QAction, QDialogButtonBox, QFileDialog, QMessageBox
from Qt.QtGui import QIcon

from tpDcc.managers import resources
from tpDcc.libs.python import path as path_utils
from tpDcc.libs.qt.widgets import messagebox

from tpDcc.libs.datalibrary.core import consts, exceptions
from tpDcc.libs.datalibrary.core.views import item

LOGGER = logging.getLogger('tpDcc-libs-datalibrary')


class DataItemView(item.ItemView):

    SAVE_WIDGET_CLASS = None
    LOAD_WIDGET_CLASS = None

    def __init__(self, data_item, library_window=None):
        super(DataItemView, self).__init__(data_item=data_item)

        self._modal = None
        self._library_window = None
        self._read_only = False
        self._ignore_exists_dialog = False

        self._menu_icon_path = resources.get('icons', data_item.ICON_NAME)

        if library_window:
            self.set_library_window(library_window)

        self._item.metaDataChanged.connect(self._on_metadata_updated)
        self._item.pathCopiedToClipboard.connect(self._on_path_copied_to_clipboard)
        self._item.saving.connect(self._on_before_save_item)
        self._item.saved.connect(self._on_item_saved)
        self._item.copied.connect(self._on_item_copied)
        self._item.renamed.connect(self._on_item_renamed)
        self._item.deleted.connect(self._on_item_deleted)

    # ============================================================================================================
    # CLASS FUNCTIONS
    # ============================================================================================================

    @classmethod
    def create_action(cls, item_class, menu, library_window):
        """
        Returns the action to be displayed when the user clicks the "Add New Item" icon
        :param item_class: str
        :param menu: QMenu
        :param library_window: LibraryWindow
        :return: QAction
        """

        if not item_class.MENU_NAME:
            LOGGER.warning('Impossible to show "{}" Create Menu because no menu name defined!'.format(
                item_class.MENU_NAME))
            return

        icon_name = os.path.splitext(item_class.ICON_NAME)[0] if item_class.ICON_NAME else None
        action_icon = resources.icon(icon_name) if icon_name else QIcon()
        callback = partial(cls.show_save_widget, item_class, library_window)
        action = QAction(action_icon, item_class.MENU_NAME, menu)
        action.triggered.connect(callback)
        menu.addAction(action)

        return action

    @classmethod
    def show_save_widget(cls, item_class, library_window, item_view=None):
        """
        Function used to show the create widget of the current item
        :param library_window: LibraryWindow
        :param item_view: LibraryItem or None
        """

        if not cls.SAVE_WIDGET_CLASS:
            LOGGER.warning(
                'Impossible to create new item of type "{}" because no save widget implementation defined!'.format(
                    cls.__name__))
            return

        item_path = library_window.selected_folder_path()
        if not item_view:
            item_view = library_window.factory.create_item(
                item_class, item_path, data=None, library=library_window.library())
        widget = cls.SAVE_WIDGET_CLASS(item=item_view, parent=library_window)
        library_window.set_create_widget(widget)

    # ============================================================================================================
    # OVERRIDES
    # ============================================================================================================

    def thumbnail_path(self):
        """
        Return the thumbnail path for the item on disk
        :return: str
        """

        item_path = self.path()
        if not item_path:
            return self._default_thumbnail_path

        thumbnail_path = os.path.dirname(item_path) if os.path.isfile(item_path) else item_path
        thumbnail_path = path_utils.join_path(thumbnail_path, consts.ITEM_DEFAULT_THUMBNAIL_NAME)
        if os.path.isfile(thumbnail_path):
            return thumbnail_path

        thumbnail_path = thumbnail_path.replace('.jpg', '.png')
        if os.path.isfile(thumbnail_path):
            return thumbnail_path

        return self._default_thumbnail_path

    def mime_text(self):
        """
        Returns the mime text for drag and drop
        :return: str
        """

        # if self.path():
        #     file_path = path_utils.clean_path(os.path.join(self.path(), self.name()))
        #     if not os.path.isfile(file_path):
        #         file_path = self.path()
        #     return file_path

        return self.path()

    def url(self):
        """
        Used by the mime data when dragging/droping the item
        :return: Qurl
        """

        # if self.path():
        #     file_path = path_utils.clean_path(os.path.join(self.path(), self.name()))
        #     if not os.path.isfile(file_path):
        #         file_path = self.path()
        #     return QUrl('file:///{}'.format(file_path))

        return QUrl('file:///{}'.format(self.path()))

    # ============================================================================================================
    # BASE
    # ============================================================================================================

    def id(self):
        """
        Returns the unique id for the item
        :return: str
        """

        return self._item.id

    def name(self):
        """
        Returns name of the item
        :return: str
        """

        return self._item.name

    def path(self):
        """
        Returns the path for the item
        :return: str
        """

        return self._item.path

    def library(self):
        """
        Returns library model for the item
        :return: DataLibrary
        """

        if not self._item.library and self.library_window():
            return self.library_window().library()

        return self._item.library

    def library_window(self):
        """
        Returns the library widget containing the item
        :return: LibraryWindow
        """

        return self._library_window

    def set_library_window(self, library_window):
        """
        Sets the library widget containing the item
        :param library_window: LibraryWindow
        """

        self._library_window = library_window

    def is_locked(self):
        """
        Returns whether or not this item is locked
        :return: bool
        """

        locked = False
        if self.library_window():
            locked = self.library_window().is_locked()

        return locked

    def is_read_only(self):
        """
        Returns whether or not this item is read only
        :return: bool
        """

        if self.is_locked():
            return True

        return self._read_only

    def set_read_only(self, flag):
        """
        Sets whether or not this item is read only
        :param flag: bool
        """

        self._read_only = flag

    def is_deletable(self):
        """
        Returns whether or not this item is deletable
        :return: bool
        """

        if self.is_locked():
            return False

        return self.item.ENABLE_DELETE

    def select_folder(self):
        """
        Select the folder in the library widget
        """

        if not self.library_window():
            return

        item_path = '/'.join(path_utils.normalize_path(self.path()).split('/')[:-1])
        self.library_window().select_folder_path(item_path)

    # ============================================================================================================
    # PREVIEW WIDGET
    # ============================================================================================================

    def preview_widget(self):
        """
        Returns the widget to be shown when the user clicks on the item
        :return: QWidget or None
        """

        widget = None

        if self.LOAD_WIDGET_CLASS:
            widget = self.LOAD_WIDGET_CLASS(item_view=self)

        return widget

    def show_preview_widget(self, library_window):
        """
        Shows the preview widget for the item instance
        :param library_window: LibraryWindow
        """

        widget = self.preview_widget()
        library_window.set_preview_widget(widget)

    # ============================================================================================================
    # DIALOGS
    # ============================================================================================================

    def show_toast_message(self, text):
        """
        Function that shows the toast widget with the given text
        :param text: str
        """

        if self.library_window():
            self.library_window().show_toast_message(text)

    def show_error_dialog(self, title, text):
        """
        Function that shows an error dialog to the user
        :param title: str
        :param text: str
        :return: QMessageBox.StandardButton or None
        """

        if self.library_window():
            self.library_window().show_error_message(text)

        button = None
        if not self._modal:
            self._modal = True
            try:
                button = messagebox.MessageBox.critical(self.library_window(), title, text)
            finally:
                self._modal = False

        return button

    def show_exception_dialog(self, title, error, exception):
        """
        Function that shows a question dialog to the user
        :param title: str
        :param error: str
        :param exception: str
        """

        LOGGER.exception(exception)
        return self.show_error_dialog(title, error)

    def show_question_dialog(self, title, text):
        """
        Function that shows a question dialog to the user
        :param title: str
        :param text: str
        :return: QMessageBox.StandardButton
        """

        return messagebox.MessageBox.question(self.library_window(), title, text)

    def show_rename_dialog(self, parent=None):
        """
        Shows the rename dialog
        :param parent: QWidget
        """

        select = False
        if self.library_window():
            parent = parent or self.library_window()
            select = self.library_window().selected_folder_path() == self.path()

        name, btn = messagebox.MessageBox.input(
            parent, 'Rename item', 'Rename the current item to:', input_text=self.name())
        if btn == QDialogButtonBox.Ok:
            try:
                self.item.rename(name)
                if select:
                    self.library_window().select_folder_path(self.path())
            except Exception as exc:
                self.show_exception_dialog('Rename Error', exc, traceback.format_exc())
                raise

        return btn

    def show_move_dialog(self, parent=None):
        """
        Shows the move to browser dialog
        :param parent: QWidget
        """

        path = os.path.dirname(self.path())
        target = QFileDialog.getExistingDirectory(parent, 'Move To ...', path)
        if target:
            try:
                source = self.item.path if not self.item.TRANSFER_BASENAME or \
                                          not self.item.TRANSFER_CLASS else self.item.get_directory()
                if os.path.isdir(source):
                    target = path_utils.join_path(target, os.path.basename(source))
                self.item.move(target)
            except Exception as exc:
                self.show_exception_dialog('Move Error', exc, traceback.format_exc())
                raise

    def show_delete_dialog(self):
        """
        Shows the delete item dialog
        """

        button = self.show_question_dialog('Delete Item', 'Are you sure you want to delete this item?')
        if button == QDialogButtonBox.Yes:
            try:
                self.item.delete(sync=True)
            except Exception as exc:
                self.show_exception_dialog('Delete Error', exc, traceback.format_exc())
                raise

        self.library_window().set_preview_widget_from_item(None)

    def show_already_existing_dialog(self):
        """
        Shows a warning dialog if the item already exists on save
        """

        if not self.library_window():
            raise exceptions.ItemSaveError('Item already exists!')

        buttons = QDialogButtonBox.Yes | QDialogButtonBox.Cancel
        try:
            QApplication.setOverrideCursor(Qt.ArrowCursor)
            button = self.library_window().show_question_dialog(
                'Item already exists',
                'Would you like to move the existing item "{}" to trash?'.format(os.path.basename(self.path())), buttons
            )
        finally:
            QApplication.restoreOverrideCursor()

        if button == QDialogButtonBox.Yes:
            self._move_to_trash()
        elif button == QMessageBox.Cancel:
            return button
        else:
            raise exceptions.ItemSaveError('You cannot save over an existing item.')

        return button

    # ============================================================================================================
    # CONTEXTUAL MENUS
    # ============================================================================================================

    def context_menu(self, menu, items=None):
        """
        Returns the context menu for the item
        This function MUST be implemented in subclass to return a custom context menu for the item
        :return: QMenu
        """

        pass

    def context_edit_menu(self, menu, items=None):
        """
        This function is called when the user opens context menu
        The given menu is shown as a submenu of the main context menu
        This function can be override to create custom context menus in LibraryItems
        :param menu: QMenu
        :param items: list(LibraryItem)
        """

        rename_action = QAction(resources.icon('rename'), 'Rename', menu)
        rename_action.triggered.connect(self._on_show_rename_dialog)
        menu.addAction(rename_action)

        move_to_action = QAction(resources.icon('move'), 'Move to', menu)
        move_to_action.triggered.connect(self._on_move_dialog)
        menu.addAction(move_to_action)

        copy_path_action = QAction(resources.icon('copy'), 'Copy Path', menu)
        copy_path_action.triggered.connect(self._on_copy_path)
        menu.addAction(copy_path_action)

        if self.library_window():
            select_folder_action = QAction(resources.icon('select'), 'Select Folder', menu)
            select_folder_action.triggered.connect(self._on_select_folder)
            menu.addAction(select_folder_action)

        show_in_folder_action = QAction(resources.icon('folder'), 'Show in Folder', menu)
        show_in_folder_action.triggered.connect(self._on_show_in_folder)
        menu.addAction(show_in_folder_action)

        if self.is_deletable():
            delete_action = QAction(resources.icon('delete'), 'Delete', menu)
            delete_action.triggered.connect(self._on_show_delete_dialog)
            menu.addSeparator()
            menu.addAction(delete_action)

        self.create_overwrite_menu(menu)

    def create_overwrite_menu(self, menu):
        """
        Creates a menu or action to trigger the overwrite functionality
        :param menu: QMenu
        """

        if self.is_read_only():
            return

        menu.addSeparator()
        overwrite_action = QAction(resources.icon('replace'), 'Overwrite', menu)
        overwrite_action.triggered.connect(self._on_overwrite)
        menu.addAction(overwrite_action)

    # ============================================================================================================
    # INTERNAL
    # ============================================================================================================

    def _move_to_trash(self):
        """
        Internal function that moves current item to trash
        """

        path = self.path()
        library = self.library()
        item = DataItemView(path, library=library)
        self.library_window().move_items_to_trash([item])

    # ============================================================================================================
    # CALLBACKS
    # ============================================================================================================

    def _on_show_rename_dialog(self):
        """
        Internal callback function that is triggered when Rename action is executed
        """

        self.show_rename_dialog()

    def _on_move_dialog(self):
        """
        Internal callback function that is triggered when Move action is executed
        """

        self.show_move_dialog()

    def _on_copy_path(self):
        """
        Internal callback function that is triggered when Copy Path action is executed
        """

        self.item.copy_path_to_clipboard()

    def _on_select_folder(self):
        """
        Internal callback function that is called when Select Folder action is clicked
        """

        self.select_folder()

    def _on_show_in_folder(self):
        """
        Internal callback function that is called when Show in Folder action is clicked
        """

        self.item.show_in_explorer()

    def _on_show_delete_dialog(self):
        """
        Internal callback function that is called when Delete action is clicked
        """

        self.show_delete_dialog()

    def _on_overwrite(self):
        """
        Internal callback function that is called when Overwrite action is clicked
        """

        self._ignore_exists_dialog = True
        widget = self.show_save_widget(self.library_window(), item_view=self)

    def _on_metadata_updated(self, metadata_dict):
        """
        Internal callback function that is called when metadata is updated
        :param metadata_dict: dict
        """

        pass

    def _on_path_copied_to_clipboard(self):
        """
        Internal callback function that is called when an item path is copied to clipboard
        """

        if self.library_window():
            self.library_window().show_success_message('Path copied to clipboard successfully!')

    def _on_before_save_item(self, save_path):
        if os.path.exists(save_path):
            if self._ignore_exists_dialog:
                self._move_to_trash()
            else:
                res = self.show_already_existing_dialog()
                if res == QMessageBox.Cancel:
                    self.item.cancel_save()
                    return False

        return True

    def _on_item_saved(self):
        if self.library_window():
            self.library_window().sync()
            self.library_window().select_items([self])

    def _on_item_copied(self):
        if self.library_window():
            self.library_window().refresh()

    def _on_item_renamed(self):
        if self.library_window():
            self.library_window().sync()

    def _on_item_deleted(self):
        if self.library_window():
            self.library_window().sync()
