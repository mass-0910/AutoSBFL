import os
import os.path as path
import html

class SuspiciousHtmlMaker:

    def __init__(self, javacode_path, ochiai:dict):
        with open(javacode_path, mode='r') as f:
            javacode = [line.rstrip(os.linesep) for line in f.readlines()]
            maxline_digit = len(str(len(javacode)))
        max_suspicious = self._max_suspicious(ochiai)
        self.html_buf = "<!DOCTYPE html>\n<html lang=\"en\">\n"
        self.html_buf += "<head><title>Suspicious Value of " + path.basename(javacode_path) + "</title></head>\n"
        self.html_buf += "<style>\n"
        for linename, suspicious in ochiai.items():
            self.html_buf += "code#" + linename + " {\n"
            self.html_buf += "color: #" + self._colorCode(suspicious, max_suspicious, (255, 0, 0), (255, 255, 255)) + ";\n"
            self.html_buf += "}\n"
        self.html_buf += "</style>\n<body bgcolor=\"#333333\" text=\"#ffffff\">\n<pre>\n"
        for i, javaline in enumerate(javacode):
            linenum = i + 1
            linenum_str = "{:0" + str(maxline_digit) + "}"
            suspicious = 0.0
            if "line" + str(linenum) in ochiai:
                suspicious = ochiai["line" + str(linenum)]
                code_str = "<code id=\"" + "line" + str(linenum) + "\">"
            else:
                code_str = "<code>"
            self.html_buf += linenum_str.format(linenum) + " | {:.3f} |".format(suspicious) + code_str + html.escape(javaline) + "</code>\n"
        self.html_buf += "</pre>\n</body>\n</html>"
    
    def write_html(self, outDir=""):
        with open(outDir + "outSuspicious.html", mode='w') as f:
            f.write(self.html_buf)
    
    def _max_suspicious(self, ochiai) -> float:
        suspicious_max = 0.0
        for _, suspicious in ochiai.items():
            if suspicious > suspicious_max:
                suspicious_max = suspicious
        return suspicious_max
    
    def _colorCode(self, suspicious:float, sus_max:float, maxcol:tuple, mincol:tuple) -> str:
        if sus_max == 0.0:
            sus_rate = 0.0
        else:
            sus_rate = suspicious / sus_max
        color = [0, 0, 0]
        for i in range(3):
            color[i] = maxcol[i] * sus_rate + mincol[i] * (1.0 - sus_rate)
        return "{:02x}{:02x}{:02x}".format(int(color[0]), int(color[1]), int(color[2]))
