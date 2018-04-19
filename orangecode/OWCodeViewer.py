import sys
import numpy
from orangecode.CodeEditorWidget import CodeEditorWidget

import AnyQt.QtCore
from AnyQt.QtGui import (
    QColor, QBrush, QPalette, QFont, QTextDocument,
    QSyntaxHighlighter, QTextCharFormat, QTextCursor, QKeySequence,
    QTextCursor,QCursor
)
from AnyQt.QtWidgets import (
    QTextEdit,QPushButton
)

import Orange.data
from Orange.widgets.widget import OWWidget, Input, Output
from Orange.widgets import gui
#from repr import repr

from Orange.data import Table,Variable,Domain,ContinuousVariable, DiscreteVariable, StringVariable
from numpy import float64
from numpy import nan

import os, math
import code
import itertools
import re

class OWCodeViewer(OWWidget):
    name = "Code Viewer"
    description = "Display"
    icon = "icons/Code.svg"
    priority = 10
    keywords = ["source", "code", "display" ,"programming"]
    directory = ""

    show_configuration = False

    class Inputs:
        data = Input("Source Code", Orange.data.Table)

    #class Outputs:
    #    sample = Output("Sampled Data", Orange.data.Table)

    want_main_area = False

    def __init__(self):
        super().__init__()

        # GUI
        box = gui.widgetBox(self.controlArea, "Info")
        self.infoLabel = gui.widgetLabel(box, '')

        #self.display_no_source_selected()

        self.code_editor = CodeEditorWidget()
        self.controlArea.layout().addWidget(self.code_editor)

        self.configMoreButton = QPushButton("Configuration")
        self.configMoreButton.setCheckable(True)
        self.configMoreButton.clicked.connect(self.switch_configuration_visibility)
        self.controlArea.layout().addWidget(self.configMoreButton)

        self.configurationBox = gui.widgetBox(self.controlArea, "Configuration")
        gui.lineEdit(self.configurationBox, self, 'directory','Source Directory',callback=self.directory_changed)
        self.refresh_configuration_box()

        #Test data
        #self.directory = "C:\\Code\\samples\\juliet-test-suite\\"
        #self.set_data(Table("orangecode/test.csv"))

    def switch_configuration_visibility(self,e):
        self.show_configuration = not(self.show_configuration)
        self.refresh_configuration_box()

    def refresh_configuration_box(self):
        if(self.show_configuration):
            self.configMoreButton.setText("Configuration <<")
            self.configurationBox.show()
        else:
            self.configMoreButton.setText("Configuration >>")
            self.configurationBox.hide()

    @Inputs.data
    def set_data(self, dataset):
        if dataset is not None:
            if(len(dataset) < 1):
                self.display_no_source_selected()
            else:
                #import code
                #code.interact(local=dict(globals(), **locals()))
                self.process_line(dataset[0])
        else:
            self.display_no_source_selected()

    def directory_changed(self):
        self.code_editor.setPlainText("")
        self.update_source_file()

    def process_line(self,line):
        """
        The extraction is based on values to avoid manual configuration.
        """

        self.source_file = ""
        self.source_line = -1

        #code.interact(local=locals())

        all_attributes_index = []

        #Guessing based on values
        for var in itertools.chain(line.domain.attributes,line.domain.metas):
            i = line.domain.index(var.name)
            #print("{} -> {}".format(var.name,i))
            all_attributes_index.append(i)

        for attribute_index in all_attributes_index:
            try:
                line[attribute_index]
            except IndexError:
                print("More attributes than values on line {}".format(line))
                continue

            if(line[attribute_index] is not None):
                val = line[attribute_index].value
                if type(val) is str:
                    val_parts = val.split(":")
                    if(len(val_parts) == 2):
                        if(val_parts[1].isnumeric()):
                            self.source_file = val_parts[0]
                            self.source_line = int(val_parts[1])

        self.update_source_file()

    def update_source_file(self):
        if(self.source_file != ""):
            #Update highlighter
            filename, extension = os.path.splitext(self.source_file)
            self.code_editor.set_highlighter(extension)

            try:
                with open(self.directory+"/"+self.source_file,'r') as file:
                    code = file.read()
                    self.code_editor.setPlainText(code)

                self.display_source_file()
            except IOError:
                _, err, _ = sys.exc_info()
                self.display_error(str(err))
        else:
            self.display_no_source_selected()
            return
        if(self.source_line != -1):
            #print(self.source_line)
            block = self.code_editor.document().findBlockByLineNumber(self.source_line-1)
            self.code_editor.setTextCursor(QTextCursor(block))
            self.code_editor.moveCursor(QTextCursor.EndOfBlock)

    def is_source_file(self,value):
        #print(value.__class__.__name__)
        if not(isinstance(value, str)):
            return False
        for extension in ['.java','.c','.cpp','.py','.js','.ruby','.jsp']:
            if(value.endswith(extension)):
                return True
        return False

    # Information display
    def display_no_source_selected(self):
        self.infoLabel.setText('No source file selected')

    def display_file_not_found(self):
        self.infoLabel.setText('Source file not found')

    def display_error(self,message):
        self.infoLabel.setText('An error has occured: '+message)

    def display_source_file(self):
        filename = self.source_file.split("/")[-1].split("\\")[-1]
        line = ("" if self.source_line == -1 else " ~ Line: <b>"+str(self.source_line)+"</b>")

        self.infoLabel.setText("Source file: <b>{}</b> {}".format(filename,line))
        

#For quick testing
if __name__ == "__main__":
    from AnyQt.QtWidgets import QApplication
    app = QApplication(sys.argv)
    ow = OWCodeViewer()
    ow.show()
    app.exec_()
    ow.saveSettings()
