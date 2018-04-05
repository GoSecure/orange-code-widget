import sys
import logging
from warnings import catch_warnings

import numpy as np
from Orange.widgets.utils.filedialogs import RecentPathsWComboMixin


from AnyQt.QtWidgets import (
    QTextEdit,QGridLayout,QSizePolicy,QStyle, QMessageBox, QFileDialog, QFileIconProvider, QComboBox
)

from Orange.widgets.widget import OWWidget, Input, Output
from Orange.widgets import widget, gui


from Orange.data import Table,Variable

from Orange.widgets.utils.domaineditor import DomainEditor

from Orange.widgets.settings import Setting, ContextSetting, \
    PerfectDomainContextHandler, SettingProvider

import os

from orangecode.reader.SpotbugsReader import SpotbugsReader


log = logging.getLogger(__name__)

def add_origin(examples, filename):
    """
    Adds attribute with file location to each string variable
    Used for relative filenames stored in string variables (e.g. pictures)
    TODO: we should consider a cleaner solution (special variable type, ...)
    """
    if not filename:
        return
    vars = examples.domain.variables + examples.domain.metas
    strings = [var for var in vars if var.is_string]
    dir_name, _ = os.path.split(filename)
    for var in strings:
        if "type" in var.attributes and "origin" not in var.attributes:
            var.attributes["origin"] = dir_name

def format_filter(writer):
    return '{} (*{})'.format(writer.DESCRIPTION, ' *'.join(writer.EXTENSIONS))

# Stolen from : /Orange/widgets/utils/filedialogs.py
def open_filename_dialog(start_dir, start_filter, file_formats,
                         add_all=True, title="Open...", dialog=None):
    """
    Open file dialog with file formats.
    Function also returns the format and filter to cover the case where the
    same extension appears in multiple filters.
    Args:
        start_dir (str): initial directory, optionally including the filename
        start_filter (str): initial filter
        file_formats (a list of Orange.data.io.FileFormat): file formats
        add_all (bool): add a filter for all supported extensions
        title (str): title of the dialog
        dialog: a function that creates a QT dialog
    Returns:
        (filename, file_format, filter), or `(None, None, None)` on cancel
    """
    file_formats = sorted(set(file_formats), key=lambda w: (w.PRIORITY, w.DESCRIPTION))
    filters = [format_filter(f) for f in file_formats]

    # add all readable files option
    if add_all:
        all_extensions = set()
        for f in file_formats:
            all_extensions.update(f.EXTENSIONS)
        file_formats.insert(0, None)
        filters.insert(0, "All readable files (*{})".format(
            ' *'.join(sorted(all_extensions))))

    if start_filter not in filters:
        start_filter = filters[0]

    if dialog is None:
        dialog = QFileDialog.getOpenFileName
    filename, filter = dialog(
        None, title, start_dir, ';;'.join(filters), start_filter)
    if not filename:
        return None, None, None

    file_format = file_formats[filters.index(filter)]
    return filename, file_format, filter

class OWSastFile(OWWidget,RecentPathsWComboMixin):
    name = "SAST File"
    id = "gosecure.widgets.data.sastfile"
    description = "Read bug report from various Static Analysis Scanning Tool (SAST)"
    icon = "icons/Bug.svg"
    priority = 10
    category = "Code"
    keywords = ["data", "file", "load", "read", "code", "source", "spotbugs"]

    class Outputs:
        data = Output("Data", Table, doc="Network packet")


    want_main_area = False


    settingsHandler = PerfectDomainContextHandler(
        match_values=PerfectDomainContextHandler.MATCH_VALUES_ALL
    )

    variables = ContextSetting([])
    domain_editor = SettingProvider(DomainEditor)

    class Warning(widget.OWWidget.Warning):
        file_too_big = widget.Msg("The file is too large to load automatically."
                                  " Press Reload to load.")
        load_warning = widget.Msg("Read warning:\n{}")

    class Error(widget.OWWidget.Error):
        file_not_found = widget.Msg("File not found.")
        missing_reader = widget.Msg("Missing reader.")
        sheet_error = widget.Msg("Error listing available sheets.")
        unknown = widget.Msg("Read error:\n{}")

    def __init__(self):
        super().__init__()
        RecentPathsWComboMixin.__init__(self)

        layout = QGridLayout()
        gui.widgetBox(self.controlArea, margin=0, orientation=layout)

        box = gui.hBox(None, addToLayout=False, margin=0)
        box.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.file_combo.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.file_combo.activated[int].connect(self.select_file)
        box.layout().addWidget(self.file_combo)
        layout.addWidget(box, 0, 1)

        file_button = gui.button(None, self, '...', callback=self.browse_file, autoDefault=False)
        file_button.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        file_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        layout.addWidget(file_button, 0, 2)


        reload_button = gui.button(
            None, self, "Reload", callback=self.load_data, autoDefault=False)
        reload_button.setIcon(self.style().standardIcon(
            QStyle.SP_BrowserReload))
        reload_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout.addWidget(reload_button, 0, 3)

        self.sheet_box = gui.hBox(None, addToLayout=False, margin=0)

        box = gui.vBox(self.controlArea, "Info")
        self.info = gui.widgetLabel(box, 'No data loaded.')
        self.warnings = gui.widgetLabel(box, '')

        #Domain editor
        box = gui.widgetBox(self.controlArea, "Columns (Double click to edit)")
        self.domain_editor = DomainEditor(self)
        self.editor_model = self.domain_editor.model()
        box.layout().addWidget(self.domain_editor)

        #Bottom
        box = gui.hBox(self.controlArea)
        # gui.button(
        #     box, self, "Browse documentation data sets",
        #     callback=lambda: self.browse_file(True), autoDefault=False)
        gui.rubber(box)

        self.apply_button = gui.button(
            box, self, "Apply", callback=self.apply_domain_edit)
        self.apply_button.setEnabled(False)
        self.apply_button.setFixedWidth(170)
        self.editor_model.dataChanged.connect(
            lambda: self.apply_button.setEnabled(True))


    def browse_file(self):
        start_file = self.last_path() or os.path.expanduser("~/")

        #readers = [f for f in FileFormat.formats
        #           if getattr(f, 'read', None) and getattr(f, "EXTENSIONS", None)]
        readers = [SpotbugsReader]
        print(readers)
        filename, reader, _ = open_filename_dialog(start_file, None, readers)
        if not filename:
            return
        self.add_path(filename)
        self.load_data()

    def load_data(self):
        self.closeContext()
        self.domain_editor.set_domain(None)
        self.apply_button.setEnabled(False)
        self.clear_messages()
        self.set_file_list()

        error = self._try_load()
        if error:
            error()
            self.data = None
            self.sheet_box.hide()
            self.Outputs.data.send(None)
            self.info.setText("No data.")

    def _get_reader(self):
        path = self.last_path()
        return SpotbugsReader(path)

    def _update_sheet_combo(self):
        if len(self.reader.sheets) < 2:
            self.sheet_box.hide()
            self.reader.select_sheet(None)
            return

        self.sheet_combo.clear()
        self.sheet_combo.addItems(self.reader.sheets)
        self._select_active_sheet()
        self.sheet_box.show()

    def _try_load(self):
        
        if self.last_path() and not os.path.exists(self.last_path()):
            return self.Error.file_not_found

        print(self.last_path())

        try:
            self.reader = self._get_reader()
            assert self.reader is not None
        except Exception:
            return self.Error.missing_reader

        try:
            self._update_sheet_combo()
        except Exception:
            return self.Error.sheet_error

        with catch_warnings(record=True) as warnings:
            try:
                data = self.reader.read()
            except Exception as ex:
                log.exception(ex)
                return lambda x=ex: self.Error.unknown(str(x))
            if warnings:
                self.Warning.load_warning(warnings[-1].message.args[0])

        self.info.setText(self._describe(data))

        self.loaded_file = self.last_path()
        add_origin(data, self.loaded_file)
        self.data = data
        self.openContext(data.domain)
        self.apply_domain_edit()  # sends data


    def _describe(self, table):
        domain = table.domain
        text = ""

        attrs = getattr(table, "attributes", {})
        descs = [attrs[desc]
                 for desc in ("Name", "Description") if desc in attrs]
        if len(descs) == 2:
            descs[0] = "<b>{}</b>".format(descs[0])
        if descs:
            text += "<p>{}</p>".format("<br/>".join(descs))

        text += "<p>{} bugs(s), {} feature(s), {} meta attribute(s)".\
            format(len(table), len(domain.attributes), len(domain.metas))
        if domain.has_continuous_class:
            text += "<br/>Regression; numerical class."
        elif domain.has_discrete_class:
            text += "<br/>Classification; categorical class with {} values.".\
                format(len(domain.class_var.values))
        elif table.domain.class_vars:
            text += "<br/>Multi-target; {} target variables.".format(
                len(table.domain.class_vars))
        else:
            text += "<br/>Data has no target variable."
        text += "</p>"

        if 'Timestamp' in table.domain:
            # Google Forms uses this header to timestamp responses
            text += '<p>First entry: {}<br/>Last entry: {}</p>'.format(
                table[0, 'Timestamp'], table[-1, 'Timestamp'])
        return text

    def select_file(self):
        pass

    def apply_domain_edit(self):
        if self.data is None:
            table = None
        else:
            domain, cols = self.domain_editor.get_domain(self.data.domain, self.data)
            if not (domain.variables or domain.metas):
                table = None
            else:
                X, y, m = cols
                table = Table.from_numpy(domain, X, y, m, self.data.W)
                table.name = self.data.name
                table.ids = np.array(self.data.ids)
                table.attributes = getattr(self.data, 'attributes', {})

        self.Outputs.data.send(table)
        self.apply_button.setEnabled(False)


#For quick testing
if __name__ == "__main__":
    from AnyQt.QtWidgets import QApplication
    app = QApplication(sys.argv)
    ow = OWSastFile()
    ow.show()
    app.exec_()
    ow.saveSettings()
