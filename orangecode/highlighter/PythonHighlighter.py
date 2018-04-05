from AnyQt.QtGui import (
    QColor, QBrush, QPalette, QFont, QTextDocument,
    QSyntaxHighlighter, QTextCharFormat, QTextCursor, QKeySequence,
)
from AnyQt.QtCore import Qt, QRegExp, QByteArray, QItemSelectionModel


class PythonHighlighter(QSyntaxHighlighter):

    def __init__(self, parent):
        QSyntaxHighlighter.__init__(self, parent)

        self.createKeywords()
        self.createOperators()
        self.createClassVariables()
        self.createStrings()
        self.createSingleLineComments()
        self.createAnnotations()

    def createKeywords(self):
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(Qt.darkBlue)
        keywordFormat.setFontWeight(QFont.Bold)

        keywords = [
            '\\band\\b', '\\bdel\\b', '\\bfor\\b', '\\bas\\b',
            '\\bassert\\b', '\\bbreak\\b', '\\bclass\\b',
            '\\bcontinue\\b', '\\bdef\\b', '\\belif\\b', '\\belse\\b',
            '\\bexcept\\b', '\\bexec\\b', '\\bFalse\\b', '\\bfinally\\b',
            '\\bfrom\\b', '\\bglobal\\b', '\\bif\\b', '\\bimport\\b',
            '\\bin\\b', '\\bis\\b', '\\blambda\\b', '\\bNone\\b',
            '\\bnonlocal\\b', '\\bnot\\b', '\bor\b', '\\bpass\\b',
            '\\bprint\\b', '\\braise\\b', '\\breturn\\b', '\\bTrue\\b',
            '\\btry\\b', '\\bwhile\\b', '\\bwith\\b', '\\byield\\b', '<',
            '<=', '>', '>=', '==', '!=']

        self.highlightingRules = [(QRegExp(pattern), keywordFormat)
                                  for pattern in keywords]

    def createOperators(self):
        operatorFormat = QTextCharFormat()
        operatorFormat.setForeground(Qt.blue)

        operators = ['\\+', '-', '/', '\\*', '(', ')', '[', ']', '{', '}']

        self.highlightingRules.extend(
            [(QRegExp(pattern), operatorFormat) for
             pattern in operators])

    def createClassVariables(self):
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor(223, 109, 209))

        keywords = ['self', '__init__']

        self.highlightingRules.extend(
            [(QRegExp(pattern), keywordFormat) for pattern in keywords])

    def createStrings(self):
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(Qt.darkGreen)
        self.highlightingRules.append((QRegExp('\'.*\''), stringFormat))
        self.highlightingRules.append((QRegExp('\".*\"'), stringFormat))

    def createSingleLineComments(self):
        singleLineCommentFormat = QTextCharFormat()
        singleLineCommentFormat.setForeground(Qt.gray)
        self.highlightingRules.append(
            (QRegExp('#[^\n]*'), singleLineCommentFormat))

    def createAnnotations(self):
        annotationFormat = QTextCharFormat()
        annotationFormat.setForeground(QColor(108, 204, 255))
        self.highlightingRules.append(
            (QRegExp('@[^\n]*'), annotationFormat))

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            expression = pattern
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)
        self.setCurrentBlockState(0)
