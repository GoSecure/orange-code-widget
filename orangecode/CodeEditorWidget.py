from AnyQt.QtWidgets import (
    QPlainTextEdit, QListView, QSizePolicy, QMenu, QSplitter, QLineEdit,
    QAction, QToolButton, QFileDialog, QStyledItemDelegate,
    QStyleOptionViewItem, QPlainTextDocumentLayout, QWidget, QTextEdit
)
from AnyQt.QtGui import (
    QColor, QBrush, QPalette, QFont, QTextDocument,
    QSyntaxHighlighter, QTextCharFormat, QTextCursor, QKeySequence, QTextOption, 
    QTextFormat, QPainter
)
from AnyQt.QtCore import (
    Qt, QRegExp, QByteArray, QItemSelectionModel, Signal, QObject, QRect
)
#from orangecode.PythonSyntaxHighlighter import PythonSyntaxHighlighter
#from orangecode.PythonSyntaxHighlighter import colorize
import math
from orangecode.highlighter.PythonHighlighter import PythonHighlighter
from orangecode.highlighter.CsHighlighter import CsHighlighter
from orangecode.highlighter.CppHighlighter import CppHighlighter
from orangecode.highlighter.NoneHighlighter import NoneHighlighter

def colorize(c1, c1_strength, c2, c2_strength):
    """Convenience method for making a color from 2 existing colors.
    :param c1: QtGui.QColor 1
    :param c1_strength: int factor of the strength of this color
    :param c2: QtGui.QColor 2
    :param c2_strength: int factor of the strength of this color
    This is primarily used to prevent hardcoding of colors that don't work in
    other color palettes. The idea is that you can provide a color from the
    current widget palette and shift it toward another color. For example,
    you could get a red-shifted text color by supplying the windowText color
    for a widget as color 1, and the full red as color 2. Then use the strength
    args to weight the resulting color more toward the windowText or full red.
    It's still important to test the resulting colors in multiple color schemes.
    """

    total = c1_strength + c2_strength

    r = ((c1.red() * c1_strength) + (c2.red() * c2_strength)) / total
    g = ((c1.green() * c1_strength) + (c2.green() * c2_strength)) / total
    b = ((c1.blue() * c1_strength) + (c2.blue() * c2_strength)) / total

    return QColor(r, g, b)

class CodeEditorWidget(QPlainTextEdit):
    """A simple python editor widget.
    :signal: ``input(str)`` - emits the input input text when submitted
    :signal: ``output(str)`` - emits the output when eval'd/exec'd
    :signal: ``results(str)`` - emits the returned results as a ``str`` after eval/exec
    :signal: ``error(str)`` - emits any error as a ``str`` after eval/exec
    :signal: ``cursor_column_changed(int)`` - emits the current column as the cursor changes
    """

    # signals.
    input = Signal(str)
    output = Signal(str)
    results = Signal(str)
    error = Signal(str)
    cursor_column_changed = Signal(int)

    def __init__(self, parent=None):
        """Initialize the input widget.
        :param echo: bool, echo input if True.
        :param parent: The parent widget.
        """

        super(CodeEditorWidget, self).__init__(parent)

        # local symbol table for this input widget.
        self._locals = {}
        self._echo = True
        self._show_line_numbers = True

        # helps prevent unnecessary redraws of the line number area later.
        # See the Qt docs example for line numbers in text edit widgets:
        # http://doc.qt.io/qt-4.8/qt-widgets-codeeditor-example.html
        self._count_cache = {
            "blocks": None,
            "cursor_blocks": None
        }

        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setWordWrapMode(QTextOption.NoWrap)

        self.set_highlighter(".py")

        self._line_number_area = _LineNumberArea(self)

        # ---- connect signals/slots

        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.cursorPositionChanged.connect(
            lambda: self.cursor_column_changed.emit(
                self.textCursor().columnNumber() + 1
            )
        )

        # keep line numbers updated
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)

        # ---- initialize the state

        # go ahead and highlight the current line
        self.highlight_current_line()

        # initialize the line number area
        self._update_line_number_area_width(0)


        self.setReadOnly(True)

    def set_highlighter(self,language):
        print("Changing language view to "+language)
        if language == ".py":
            self._syntax_highlighter = PythonHighlighter(self.document())
        elif language == ".cs":
            self._syntax_highlighter = CsHighlighter(self.document())
        elif language == ".java":
            self._syntax_highlighter = CsHighlighter(self.document())
        elif language == ".cpp":
            self._syntax_highlighter = CsHighlighter(self.document())
        else:
            self._syntax_highlighter = NoneHighlighter(self.document())

        #self._syntax_highlighter.setDocument(self.document())

    def add_globals(self, new_globals):
        """
        Updates ``globals()`` with the supplied values.
        """

        globals_dict = globals()
        globals_dict.update(new_globals)


    def highlight_current_line(self):
        """Highlight the current line of the input widget."""

        extra_selection = QTextEdit.ExtraSelection()
        extra_selection.format.setBackground(QBrush(self._current_line_color()))
        extra_selection.format.setProperty(QTextFormat.FullWidthSelection, True)
        extra_selection.cursor = self.textCursor()
        extra_selection.cursor.clearSelection()

        self.setExtraSelections([extra_selection])

    def keyPressEvent(self, event):
        """Intercept any key events for special casing.
        :param event: key press event object.
        """

        if (event.modifiers() & Qt.ShiftModifier and
            event.key() in [Qt.Key_Enter, Qt.Key_Return]):
                self.insertPlainText("\n")
                event.accept()
        elif event.key() == Qt.Key_Tab:
            # intercept the tab key and insert 4 spaces
            self.insertPlainText("    ")
            event.accept()
        else:
            super(CodeEditorWidget, self).keyPressEvent(event)

    def line_number_area_width(self):
        """Calculate the width of the line number area."""

        if self._show_line_numbers:
            digits = math.floor(math.log10(self.blockCount())) + 1
            return 6 + self.fontMetrics().width('8') * digits
        else:
            return 0

    def paint_line_numbers(self, event):
        """Paint the line numbers for the input widget.
        :param event:  paint event object.
        """

        if not self._show_line_numbers:
            return

        # paint on the line number area
        painter = QPainter(self._line_number_area)

        line_num_rect = event.rect()

        # fill it with the line number base color
        painter.fillRect(
            line_num_rect,
            self._line_number_area_base_color()
        )

        painter.setPen(self.palette().base().color())
        painter.drawLine(line_num_rect.topLeft(), line_num_rect.bottomLeft())
        painter.drawLine(line_num_rect.topLeft(), line_num_rect.topRight())
        painter.drawLine(line_num_rect.bottomLeft(), line_num_rect.bottomRight())

        # ---- process the visible blocks

        block = self.firstVisibleBlock()
        block_num = block.blockNumber()

        top = int(
            self.blockBoundingGeometry(block).translated(
                self.contentOffset()
            ).top()
        )

        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= line_num_rect.bottom():

            if block.isVisible() and bottom >= line_num_rect.top():

                num = str(block_num + 1)
                painter.setPen(self._line_number_color())
                painter.drawText(
                    -2, top,
                    self._line_number_area.width(),
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    num
                )

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_num += 1

    def resizeEvent(self, event):
        """Make sure line number area is updated on resize.
        :param event: resize event object
        """

        super(CodeEditorWidget, self).resizeEvent(event)

        contents_rect = self.contentsRect()
        line_number_area_rect = QRect(
            contents_rect.left(),
            contents_rect.top(),
            self.line_number_area_width(),
            contents_rect.height()
        )
        self._line_number_area.setGeometry(line_number_area_rect)

    def echoing_output(self):
        # returns ``True`` if echoing python commands/statements to the output window
        return self._echo

    def showing_line_numbers(self):
        # returns ``True`` if line numbers are being shown, ``False`` otherwise.
        return self._show_line_numbers

    def toggle_echo(self, echo):
        """Toggles the echo'ing of the input.
        NOTE: This does not update the UI.
        :param echo: bool, if True, forward the input to the signal.
        """
        self._echo = echo

    def toggle_line_numbers(self, line_numbers):
        """
        Toggles line numbers on/off based on the supplied value.
        """
        self._show_line_numbers = line_numbers

        # redraw the whole thing to get it to update immediately
        self._update_line_number_area(self.rect(), 0)

    def wheelEvent(self, event):
        """
        Handles zoom in/out of the text.
        """

        if event.modifiers() & Qt.ControlModifier:

            delta = event.angleDelta().y()
            if delta < 0:
                self.zoom_out()
            elif delta > 0:
                self.zoom_in()

            #return True

        super(CodeEditorWidget, self).wheelEvent(event)

    def zoom(self, direction):
        """
        Zoom in on the text.
        """

        font = self.font()
        size = font.pointSize()
        if size == -1:
            size = font.pixelSize()

        size += direction

        if size < 7:
            size = 7
        if size > 50:
            return

        style = """
        QWidget {
            font-size: %spt;
        }
        """ % (size,)
        self.setStyleSheet(style)

    def zoom_in(self):
        """
        Zoom in on the text.
        """
        self.zoom(1)

    def zoom_out(self):
        """
        Zoom out on the text.
        """
        self.zoom(-1)

    def _current_line_color(self):
        """Returns a line color for the current line highlighting.
        5 parts base color, 1 part highlight.
        """

        if not hasattr(self, "_cur_line_color"):

            palette = self.palette()
            base_color = palette.base().color()
            highlight_color = palette.highlight().color()

            self._cur_line_color = colorize(
                base_color, 2,
                highlight_color, 1,
            )

        return self._cur_line_color

    def _format_exc(self):
        """Get the latest stack trace and format it for display."""
        tb = sys.exc_info()[2]
        return traceback.format_exc(tb)

    def _line_number_area_base_color(self):
        """Get a line number base color."""

        if not hasattr(self, '_line_num_base_color'):
            palette = self.palette()
            base_color = palette.base().color()
            window_color = palette.window().color()

            self._line_num_base_color = colorize(
                base_color, 1,
                window_color, 1,
            )

        return self._line_num_base_color

    def _line_number_color(self):
        """Get a line number color."""

        if not hasattr(self, '_line_num_color'):

            palette = self.palette()
            base_color = palette.base().color()
            highlight_color = palette.highlight().color()

            self._line_num_color = colorize(
                base_color, 1,
                highlight_color, 2,
            )

        return self._line_num_color

    def _readline(self):
        """
        Reads a line of input text from the user.
        :return: a string for the user input.
        """
        dialog = QInputDialog(
            parent=self,
            flags=Qt.FramelessWindowHint
        )
        dialog.setLabelText("Python is requesting input")
        dialog.adjustSize()

        dialog.resize(self.width() - 2, dialog.height())
        dialog.move(
            self.mapToGlobal(self.rect().topLeft()).x(),
            self.mapToGlobal(self.rect().bottomLeft()).y() - dialog.height()
        )

        try:
            if dialog.exec_() == QDialog.Accepted:
                return str(dialog.textValue()) + "\n"
            else:
                return ""
        finally:
            self.setFocus()

    def _update_line_number_area(self, rect, dy):
        """Update the contents of the line number area.
        :param rect: The line number are rect.
        :param dy: The horizontal scrolled difference.
        """

        if (dy):
            self._line_number_area.scroll(0, dy)
        elif (self._count_cache["blocks"] != self.blockCount() or
              self._count_cache["cursor_blocks"] != self.textCursor().block().lineCount()):
            self._line_number_area.update(
                0,
                rect.y(),
                self._line_number_area.width(),
                rect.height()
            )
            self._count_cache = {
                "blocks": self.blockCount(),
                "cursor_blocks": self.textCursor().block().lineCount()
            }

        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width(0)

    def _update_line_number_area_width(self, count):
        """Update the display of the line number area.
        :param count: block count. unused, but comes from connected singal.
        """
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)


class _LineNumberArea(QWidget):
    """Display line numbers for an input widget."""

    def __init__(self, editor):
        """Initialize the line number area.
        :param editor: The editor widget where line numbers will be displayed.
        """

        super(_LineNumberArea, self).__init__(parent=editor)
        self._editor = editor

    def paintEvent(self, event):
        """Paint line numbers on the editor.
        :param event: paint event object.
        """
        self._editor.paint_line_numbers(event)
