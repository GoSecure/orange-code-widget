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
    QTextEdit
)

import Orange.data
from Orange.widgets.widget import OWWidget, Input, Output
from Orange.widgets import gui
#from repr import repr

from Orange.data import Table,Variable,Domain,ContinuousVariable, DiscreteVariable, StringVariable
from numpy import float64
from numpy import nan

import os, math

class OWCodeViewer(OWWidget):
    name = "Code Viewer"
    description = "Display"
    icon = "icons/Code.svg"
    priority = 10
    keywords = ["source", "code", "display" ,"programming"]
    directory = ""


    class Inputs:
        data = Input("Source Code", Orange.data.Table)

    #class Outputs:
    #    sample = Output("Sampled Data", Orange.data.Table)

    want_main_area = False

    def __init__(self):
        super().__init__()

        # GUI
        box = gui.widgetBox(self.controlArea, "Info")
        self.infoa = gui.widgetLabel(box, '')
        self.infob = gui.widgetLabel(box, '')
        gui.lineEdit(self.controlArea, self, 'directory','Source Directory',box="Configuration",callback=self.directory_changed)
        #self.display_no_source_selected()

        self.code_editor = CodeEditorWidget()
        self.controlArea.layout().addWidget(self.code_editor)

        #Test data
        #self.directory = "C:\\Code\\samples\\juliet-test-suite\\"
        #self.set_data(Table("orangecode/test.csv"))


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
        The extraction is based on columns name and values to avoid manual configuration.
        It is expected that 
        """

        self.source_file = ""
        self.source_line = -1

        index_file = -1
        index_line = -1

        #Guessing based on values
        for i, var in enumerate(line.domain.variables):
            if var.is_discrete and "file" in var.name.lower():
                index_file = i
            elif "line" in var.name.lower():
                index_line = i

        for i, cell in enumerate(line.values()):
            val = cell.value

            #Using index found previously
            if index_file == i:
                self.source_file = val
            if index_line == i and (isinstance(val, float)) and not(math.isnan(val)):
                self.source_line = int(val)

            #Guessing based on values
            if(self.source_file != "" and self.is_source_file(val)):
                self.source_file = val
            if(self.source_line == -1 and (isinstance(val, float))) and not(math.isnan(val)):
                self.source_line = int(val)

        #print("{}:{}".format(self.source_file,self.source_line))
        if(self.source_file != ""):
            filename, extension = os.path.splitext(self.source_file)
            self.code_editor.set_highlighter(extension)
        self.update_source_file()

    def update_source_file(self):
        if(self.source_file != ""):
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
        self.infoa.setText('No source file selected')
        self.infob.setText("")

    def display_file_not_found(self):
        self.infoa.setText('Source file not found')
        self.infob.setText("")

    def display_error(self,message):
        self.infoa.setText('An error has occured: '+message)
        self.infob.setText("")

    def display_source_file(self):
        self.infoa.setText('Source file: '+self.source_file)
        self.infob.setText(("" if self.source_line == -1 else "Line:"+str(self.source_line)))

#For quick testing
if __name__ == "__main__":
    from AnyQt.QtWidgets import QApplication
    app = QApplication(sys.argv)
    ow = OWCodeViewer()
    ow.show()
    app.exec_()
    ow.saveSettings()
