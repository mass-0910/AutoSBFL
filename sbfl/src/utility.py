import os

class Util:

    symbol = ['//', '/*', '*/', '\'', ',', '.', '+', '-', '*', '/', '%', '++', '--', '&', '|', '~', '<<', '>>', '>>>', '{', '}', '[', ']', '(', ')', ';', ':', '=', '>', '<', '!', '?', '==', '&&', '||', '+=', '-=', '*=', '/=', '<=', '>=', '&=', '|=', '^=', '<<=', '>>=', '>>>=', '@']
    space = [' ', '\t', '\n', '\r']
    keywords = [
                    "abstract", "assert", "break", "byte", "case", "catch", "class", "const", \
                    "continue", "default", "do", "else", "enum", "extends", "final", "finally", \
                    "for", "goto", "if", "implements", "import", "instanceof", "interface", "native", \
                    "new", "package", "private", "protected", "public", "return", "static", "strictfp", "super", \
                    "switch", "synchrnized", "this", "throw", "throws", "transient", "try", "volatile", "while", \
                    "false", "true", "null"\
                ]
    class_modifier = ["abstract", "final", "strictfp"]
    all_type = []

    @staticmethod
    def get_all_class():
        with open(os.path.join(os.path.dirname(__file__), "java-classname.txt")) as fp:
            Util.all_type = fp.readlines()
        for i, classname in enumerate(Util.all_type):
            Util.all_type[i] = classname.strip()

    @staticmethod
    def split_token(sentence) -> list[str]:
        retval = []
        buf = ""
        mode = 0 #name
        escape = False
        for character in sentence:
            if mode == 0: #name
                if character in Util.symbol:
                    if buf:
                        retval.append(buf)
                    buf = character
                    mode = 1 #symbol
                elif character in Util.space:
                    if buf:
                        retval.append(buf)
                        buf = ""
                elif character == "\"":
                    if buf:
                        retval.append(buf)
                    buf = "\""
                    mode = 2 #string
                else:
                    buf += character
            elif mode == 1: #symbol
                if buf + character in Util.symbol:
                    buf += character
                elif character == "\"":
                    if buf:
                        retval.append(buf)
                    buf = "\""
                    mode = 2 #string
                elif character in Util.space:
                    if buf:
                        retval.append(buf)
                    buf = ""
                    mode = 0 #name
                else:
                    if buf:
                        retval.append(buf)
                    buf = character
                    if not character in Util.symbol:
                        mode = 0 #name
            elif mode == 2: #string
                buf += character
                if character == "\"" and not escape:
                    retval.append(buf)
                    buf = ""
                    mode = 0 #name
                elif character == "\\":
                    escape = True
                elif escape:
                    escape = False

        if buf:
            retval.append(buf)
            buf = ""
        return retval

    @staticmethod
    def is_identifier(token):
        if not token in Util.symbol and not token in Util.keywords and not Util.is_string(token):
            return True
        else:
            return False

    @staticmethod
    def is_string(token):
        if token[0] == "\"" and token[-1] == "\"":
            return True
        else:
            return False
