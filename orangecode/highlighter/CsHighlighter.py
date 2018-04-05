from AnyQt.QtGui import (
    QColor, QBrush, QPalette, QFont, QTextDocument,
    QSyntaxHighlighter, QTextCharFormat, QTextCursor, QKeySequence,
)
from AnyQt.QtCore import Qt, QRegExp, QByteArray, QItemSelectionModel


class CsHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        QSyntaxHighlighter.__init__(self, parent)

        self._multiLineCommentFormat = QTextCharFormat()
        self._multiLineCommentFormat.setForeground(Qt.lightGray)

        self._commentStartExpression = QRegExp("/\\*")
        self._commentEndExpression = QRegExp("\\*/")

        self.createKeywords()
        self.createOperators()
        self.createStrings()
        self.createArrows()
        self.createComments()

    def createKeywords(self):
        keywordFormat = QTextCharFormat()
        keywordFormat.setForeground(QColor(64, 155, 11))

        keywords = [
            '\\babstract\\b', '\\bas\\b', '\\bbase\\b', '\\bbool\\b',
            '\\bbreak\\b', '\\bbyte\\b', '\\bcase\\b', '\\bcatch\\b',
            '\\bchar\\b', '\\bchecked\\b', '\\bclass\\b', '\\bconst\\b',
            '\\bcontinue\\b', '\\bdecimal\\b', '\\bdefault\\b',
            '\\bdelegate\\b', '\\bif\\b', '\\bimplicit\\b', '\\bin\\b',
            '\\bdo\\b', '\\bdouble\\b', '\\bint\\b', '\\binterface\\b',
            '\\belse\\b', '\\benum\\b', '\\bevent\\b', '\\bexplicit\\b',
            '\\bextern\\b', '\\bfalse\\b', '\\btrue\\b', '\\binternal\\b',
            '\\bfinally\\b', '\\bfixed\\b', '\\bfloat\\b', '\\bfor\\b',
            '\\bforeach\\b', '\\bgoto\\b', '\\bis\\b', '\\block\\b',
            '\\blong\\b', '\\bnamepsace\\b', '\\bnew\\b', '\\bnull\\b',
            '\\bobject\\b', '\\boperator\\b', '\\bout\\b', '\\boverride\\b',
            '\\bparams\\b', '\\bprivate\\b', '\\bprotected\\b', '\\bpublic\\b',
            '\\breadonly\\b', '\\bref\\b', '\\breturn\\b', '\\bsbyte\\b',
            '\\bsealed\\b', '\\bshort\\b', '\\bsizeof\\b', '\\bstackalloc\\b',
            '\\bstatic\\b', '\\bstring\\b', '\\bstruct\\b', '\\bswitch\\b',
            '\\bthis\\b', '\\bthrow\\b', '\\btry\\b', '\\btypeof\\b',
            '\\buint\\b', '\\bulong\\b', '\\bunchecked\\b', '\\bunsafe\\b',
            '\\bushort\\b', '\\busing\\b', '\\bvirtual\\b', '\\bvoid\\b',
            '\\bvolatile\\b', '\\bwhile\\b'
        ]

        self.highlightingRules = [(QRegExp(pattern), keywordFormat)
                                  for pattern in keywords]

    def createOperators(self):
        operatorFormat = QTextCharFormat()
        operatorFormat.setForeground(QColor(148, 99, 233))
        operatorFormat.setFontWeight(QFont.Bold)

        operators = ['\\+', '-', '/', '\\*',
                     '=', '==', '!=', '<=', '>=', '<', '>']

        self.highlightingRules.extend(
            [(QRegExp(pattern), operatorFormat) for
             pattern in operators])

    def createStrings(self):
        stringFormat = QTextCharFormat()
        stringFormat.setForeground(Qt.darkGray)
        self.highlightingRules.append((QRegExp('\".*\"'), stringFormat))
        self.highlightingRules.append((QRegExp('\'.*\''), stringFormat))

    def createArrows(self):
        arrowFormat = QTextCharFormat()
        arrowFormat.setForeground(Qt.red)
        arrows = ['<-', '->']
        self.highlightingRules.extend(
            [(QRegExp(pattern), arrowFormat) for pattern in arrows])

    def createComments(self):
        singleLineCommentFormat = QTextCharFormat()
        singleLineCommentFormat.setForeground(Qt.gray)
        self.highlightingRules.append(
            (QRegExp('//[^\n]*'), singleLineCommentFormat))

    def highlightBlock(self, text):
        for pattern, format in self.highlightingRules:
            expression = pattern
            index = expression.indexIn(text)

            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, format)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)

        startIndex = 0

        if self.previousBlockState() != 1:
            startIndex = self._commentStartExpression.indexIn(text)

        while startIndex >= 0:
            endIndex = self._commentEndExpression.indexIn(text, startIndex)

            if endIndex == -1:
                self.setCurrentBlockState(1)
                commentLength = len(text) - startIndex
            else:
                commentLength = endIndex - startIndex + \
                                self._commentEndExpression.matchedLength()

            self.setFormat(
                startIndex, commentLength, self._multiLineCommentFormat)
            startIndex = self._commentStartExpression.indexIn(
                text, startIndex + commentLength)
