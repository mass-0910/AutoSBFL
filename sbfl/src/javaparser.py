from antlr4 import FileStream, CommonTokenStream, ParseTreeWalker

from ant.Java8ParserListener import Java8ParserListener
from ant.Java8Parser import Java8Parser
from ant.Java8Lexer import Java8Lexer
import re

class JavaParser(Java8ParserListener):

    def __init__(self, parse_java_file_path):
        super().__init__()
        self.javafile_path = parse_java_file_path
        self.parser = Java8Parser(CommonTokenStream(Java8Lexer(FileStream(parse_java_file_path, encoding="utf-8"))))
        self.insert_points = []
        self.insert_tokens = []
        self.testname_re = re.compile(r"test[0-9]+")
        
    def startInsert(self):
        self.insert_points = []
        self.insert_tokens = []
        walker = ParseTreeWalker()
        walker.walk(self, self.parser.compilationUnit())
        print(self.insert_points)
        self._insert()
    
    def startExtractTestFunc(self, testfunc_file):
        self.testfunc_copyarea = []
        self.testheader_copyarea = []
        walker = ParseTreeWalker()
        walker.walk(self, self.parser.compilationUnit())
        with open(self.javafile_path, mode='r') as srcf, open(testfunc_file, mode='w') as destf:
            coping = False
            srcf_lines = srcf.readlines()
            for i, line in enumerate(srcf_lines):
                linenum = i + 1
                for start, stop in self.testheader_copyarea:
                    if linenum >= start and linenum <= stop:
                        destf.write(line)
                        break
            destf.write()
            for i, line in enumerate(srcf_lines):
                linenum = i + 1
                for start, stop in self.testfunc_copyarea:
                    if linenum >= start and linenum <= stop:
                        destf.write(line)
                        break
    
    def _testfuncClassHeader(self) -> str:
        chassheader = "public class " + self.class_name + "_ExtXML{"
        mainfunc = ""
        
    def _insert(self):
        inserted = ""
        with open(self.javafile_path, mode="r+") as f:
            for i, line in enumerate(f.readlines()):
                linenum = i + 1
                outputline_sentence = "System.out.println(\"line[" + str(linenum) + "]\");"
                for j, char in enumerate(line):
                    column = j
                    for insert_elm in self.insert_tokens:
                        if insert_elm["line"] == linenum and insert_elm["column"] == column:
                            inserted += insert_elm["token"]
                    for insert_elm in self.insert_points:
                        if insert_elm["line"] == linenum and insert_elm["column"] == column:
                            inserted += outputline_sentence
                    inserted += char
            print(inserted)
            f.seek(0, 0)
            f.write(inserted)

    def enterNormalClassDeclaration(self, ctx):
        self.class_name = ctx.Identifier().getText()

    # def enterPackageDeclaration(self, ctx):
    #     self.testheader_copyarea.append((ctx.start.line, ctx.stop.line))
    
    # def enterImportDeclaration(self, ctx):
    #     self.testheader_copyarea.append((ctx.start.line, ctx.stop.line))

    # def enterMethodDeclaration(self, ctx):
    #     funcname_ctx = ctx.methodHeader().methodDeclarator().Identifier()
    #     if self.testname_re.fullmatch(funcname_ctx.getText()):
    #         self.testfunc_copyarea.append((ctx.methodHeader().start.line, ctx.stop.line))

    def enterExpressionStatement(self, ctx:Java8Parser.ExpressionStatementContext):
        self._recordInsertPoint(ctx.start.line, ctx.start.column)
    
    def enterAssertStatement(self, ctx:Java8Parser.AssertStatementContext):
        self._recordInsertPoint(ctx.start.line, ctx.start.column)
    
    def enterSwitchStatement(self, ctx:Java8Parser.SwitchStatementContext):
        self._recordInsertPoint(ctx.start.line, ctx.start.column)
    
    def enterDoStatement(self, ctx):
        self._recordInsertPoint(ctx.start.line, ctx.start.column)

    def enterBreakStatement(self, ctx):
        self._recordInsertPoint(ctx.start.line, ctx.start.column)
    
    def enterContinueStatement(self, ctx):
        self._recordInsertPoint(ctx.start.line, ctx.start.column)

    def enterReturnStatement(self, ctx):
        self._recordInsertPoint(ctx.start.line, ctx.start.column)
    
    def enterSynchronizedStatement(self, ctx):
        self._recordInsertPoint(ctx.start.line, ctx.start.column)
    
    def enterThrowStatement(self, ctx):
        self._recordInsertPoint(ctx.start.line, ctx.start.column)
    
    def enterTryStatement(self, ctx):
        self._recordInsertPoint(ctx.start.line, ctx.start.column)
    
    def _blockStatementCommon(self, ctx, isNoShortIf):
        self._recordInsertPoint(ctx.start.line, ctx.start.column)
        if isNoShortIf:
            block_statement = ctx.statementNoShortIf()
        else:
            block_statement = ctx.statement()
        if block_statement.getText()[0] != '{' or block_statement.getText()[-1] != '}':
            self._recordInsertTokenPoint(block_statement.start.line, block_statement.start.column, '{')
            self._recordInsertTokenPoint(block_statement.stop.line, block_statement.stop.column + 1, '}')
    
    def enterBasicForStatement(self, ctx):
        print("in for")
        self._blockStatementCommon(ctx, False)

    def enterEnhancedForStatement(self, ctx):
        print("in for")
        self._blockStatementCommon(ctx, False)
    
    def enterBasicForStatementNoShortIf(self, ctx):
        self._blockStatementCommon(ctx, True)

    def enterEnhancedForStatementNoShortIf(self, ctx):
        self._blockStatementCommon(ctx, True)

    def enterWhileStatement(self, ctx):
        self._blockStatementCommon(ctx, False)
    
    def enterWhileStatementNoShortIf(self, ctx):
        self._blockStatementCommon(ctx, True)
    
    def enterDoStatement(self, ctx):
        self._blockStatementCommon(ctx, False)
    
    def _ifStatementCommon(self, ctx, statement_ctx):
        self._recordInsertPoint(ctx.start.line, ctx.start.column)
        if statement_ctx.getText()[0] != '{' or statement_ctx.getText()[-1] != '}':
            self._recordInsertTokenPoint(statement_ctx.start.line, statement_ctx.start.column, '{')
            self._recordInsertTokenPoint(statement_ctx.stop.line, statement_ctx.stop.column + 1, '}')
    
    def enterIfThenStatement(self, ctx):
        self._ifStatementCommon(ctx, ctx.getChild(4))
    
    def enterIfThenElseStatement(self, ctx):
        self._ifStatementCommon(ctx, ctx.getChild(4))
        self._ifStatementCommon(ctx, ctx.getChild(6))
    
    def enterIfThenElseStatementNoShortIf(self, ctx):
        self._ifStatementCommon(ctx, ctx.getChild(4))
        self._ifStatementCommon(ctx, ctx.getChild(6))
    
    def enterLocalVariableDeclarationStatement(self, ctx):
        self._recordInsertPoint(ctx.start.line, ctx.start.column)
    
    def _recordInsertPoint(self, line, column):
        self.insert_points.append(
            {
                "line": line,
                "column": column
            }
        )
    
    def _recordInsertTokenPoint(self, line, column, token):
        self.insert_tokens.append(
            {
                "line": line,
                "column": column,
                "token": token
            }
        )
