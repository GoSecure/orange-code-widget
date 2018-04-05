from AnyQt.QtGui import (
    QColor, QBrush, QPalette, QFont, QTextDocument,
    QSyntaxHighlighter, QTextCharFormat, QTextCursor, QKeySequence,
)
from AnyQt.QtCore import Qt, QRegExp, QByteArray, QItemSelectionModel


class NoneHighlighter(QSyntaxHighlighter):

    def __init__(self, parent):
        QSyntaxHighlighter.__init__(self, parent)

    def highlightBlock(self, text):
        return
