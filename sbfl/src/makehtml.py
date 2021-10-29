import os
import os.path as path
import html
import webbrowser
import re
import json
from testselector.extract import extract_testcase_line_number

class SuspiciousHtmlMaker:

    def __init__(self, javacode_path, evosuite_path, ochiai:dict, actually:dict, stdout:dict, passfail:dict, judgereport:dict):
        with open(javacode_path, mode='r') as f:
            javacode = [line.rstrip(os.linesep) for line in f.readlines()]
            maxline_digit = len(str(len(javacode)))
        max_suspicious = self.max_suspicious(ochiai)
        self.html_buf = "<!DOCTYPE html>\n<html lang=\"en\">\n"
        self.html_buf += f"<head><title>{path.basename(javacode_path)} - AutoSBFL Report</title></head>\n"
        self.html_buf += "<style>\n"
        for linename, suspicious in ochiai.items():
            self.html_buf += "code#" + linename + " {\n"
            self.html_buf += "background-color: #" + self.color_code(suspicious, max_suspicious, (255, 0, 0), (255, 255, 255)) + ";\n"
            self.html_buf += "}\n"
        self.html_buf += """
            @font-face {
                font-family: 'MyFont';
                src: local('consolas');
            }
            .prettyprint ol.linenums > li {
                list-style-type: decimal;
            }
            .wrapper {
                position: relative;
                height: 100vh
            }
            .section- {
                position: absolute;
                top: 0;
                width: 100%;
            }
            .section-radio {
                display: none;
            }
            .section-name {
                position: relative;
                z-index: 10;
                background-color: #FFFFFF;
                font-family: 'MyFont'
            }
            .section-two {
                margin-left: 66px;
            }
            .section-three {
                margin-left: 132px;
            }
            .section-radio:checked + .section-name {
                background-color: #FF0000;
            }
            .section-content {
                display: none;
            }

            .section-radio:checked ~ .section-content {
                display: block;
            }
        """
        self.html_buf += f"</style><script src=\"https://cdn.rawgit.com/google/code-prettify/master/loader/run_prettify.js\"></script>\n<body bgcolor=\"#FFFFFF\" text=\"#1C1B22\"><h1>{path.basename(javacode_path)} - AutoSBFL Report</h1><div class=\"wrapper\">\n"

        #suspicious code tab
        self.html_buf += "<div class=\"section-\"><input class=\"section-radio\" id=\"tab1\" name=\"tab\" type=\"radio\" checked><label class=\"section-name section-one\" for=\"tab1\">SUSP</label><div class=\"section-content\"><pre class=\"prettyprint linenums\">\n"
        for i, javaline in enumerate(javacode):
            linenum = i + 1
            linenum_str = "{:0" + str(maxline_digit) + "}"
            suspicious = 0.0
            if "line" + str(linenum) in ochiai:
                suspicious = ochiai["line" + str(linenum)]
                code_str = "<code id=\"" + "line" + str(linenum) + "\">"
            else:
                code_str = "<code>"
            if suspicious > 0:
                susp_str = "<i><small>{:.3f}</small></i>".format(suspicious)
            else:
                susp_str = ""
            self.html_buf += code_str + html.escape(javaline) + "</code>" + susp_str + "\n"
        self.html_buf += "</pre></div></div>\n"

        #testcase tab
        self.html_buf += "<div class=\"section-\"><input class=\"section-radio\" id=\"tab2\" name=\"tab\" type=\"radio\"><label class=\"section-name section-two\" for=\"tab2\">TEST</label><div class=\"section-content\">\n"
        testcase_line_numbers = extract_testcase_line_number(evosuite_path)
        with open(evosuite_path) as fp:
            testcase_lines = fp.readlines()
        testname_pattern = re.compile(r"public void (\w+)\(\)")
        for testcase_line_number in testcase_line_numbers:
            testcase_str = "".join(testcase_lines[testcase_line_number[0]:testcase_line_number[1]])
            testcase_name = testname_pattern.search(testcase_str).group(1)
            self.html_buf += f"<h2>{testcase_name}</h2><p>Status:<font color=\"#{'008000' if passfail[testcase_name] else 'FF0000'}\">{'passed' if passfail[testcase_name] else 'failed'}</font></p>Code:<pre class=\"prettyprint linenums\">{testcase_str}</pre>"
            json.dumps(actually[testcase_name]['finallyObjectState'], indent=2)
            self.html_buf += f"Finally Attributes:<pre class='prettyprint'>{self.make_compare_json(actually[testcase_name]['finallyObjectState'], judgereport[testcase_name])[0]}</pre>"
        self.html_buf += "</div></div>\n"

        self.html_buf += "</div></body>\n</html>"

    def write_html(self, out_dir=""):
        with open(path.join(out_dir, "outSuspicious.html"), mode='w') as f:
            f.write(self.html_buf)
        webbrowser.open("file:///" + path.abspath(path.join(out_dir, "outSuspicious.html")))

    def max_suspicious(self, ochiai) -> float:
        suspicious_max = 0.0
        for _, suspicious in ochiai.items():
            if suspicious > suspicious_max:
                suspicious_max = suspicious
        return suspicious_max

    def color_code(self, suspicious:float, sus_max:float, maxcol:tuple, mincol:tuple) -> str:
        if sus_max == 0.0:
            sus_rate = 0.0
        else:
            sus_rate = suspicious / sus_max
        color = [0, 0, 0]
        for i in range(3):
            color[i] = maxcol[i] * sus_rate + mincol[i] * (1.0 - sus_rate)
        return "{:02x}{:02x}{:02x}".format(int(color[0]), int(color[1]), int(color[2]))

    def make_compare_json(self, actually, report:dict, indent=0) -> tuple:
        json_str = ""
        correct = True
        if isinstance(actually, dict):
            for variable, value in actually.items():
                if variable in report.keys():
                    if isinstance(value, dict):
                        s, correct = self.make_compare_json(value, report[variable], indent + 2)
                        if correct:
                            json_str += " " * indent + f"<span style='background-color:#00FF00;'>\"{variable}\": {{</span>\n{s}" + " " * indent + "}\n"
                        else:
                            json_str += " " * indent + f"<span style='background-color:#FF6347;'>\"{variable}\": {{</span>\n{s}" + " " * indent + "}\n"
                    elif isinstance(value, list):
                        s, correct = self.make_compare_json(value, report[variable], indent + 2)
                        if correct:
                            json_str += " " * indent + f"<span style='background-color:#00FF00;'>\"{variable}\": [</span>\n{s}" + " " * indent + "]\n"
                        else:
                            json_str += " " * indent + f"<span style='background-color:#FF6347;'>\"{variable}\": [</span>\n{s}" + " " * indent + "]\n"
                    else:
                        if report[variable][0]:
                            correct = True
                            json_str += " " * indent + f"<span style='background-color:#00FF00;'>\"{variable}\": {value if value != None else 'null'},</span>\n"
                        else:
                            correct = False
                            json_str += " " * indent + f"<span style='background-color:#FF6347;'>\"{variable}\": {value if value != None else 'null'},</span><small>{report[variable][1]}</small>\n"
                else:
                    if isinstance(value, dict):
                        json_str += " " * indent + f"{variable}: " + json.dumps(value, indent=2).split('\n')[0] + "\n"
                        json_str += "\n".join([" " * indent + s for s in json.dumps(value, indent=2).split('\n')[1:]]) + ',\n'
                    elif isinstance(value, list):
                        json_str += " " * indent + f"{variable}: " + json.dumps(value, indent=2).split('\n')[0] + "\n"
                        json_str += "\n".join([" " * indent + s for s in json.dumps(value, indent=2).split('\n')[1:]]) + ',\n'
                    else:
                        json_str += " " * indent + f"\"{variable}\": {value if value != None else 'null'},\n"
        elif isinstance(actually, list):
            correct = True
            for i, entry in enumerate(actually):
                if isinstance(entry, dict):
                    s, correct = self.make_compare_json(entry, report[i], indent + 2)
                    if correct:
                        json_str += " " * indent + f"<span style='background-color:#00FF00;'>{{</span>\n{s}" + " " * indent + "}\n"
                    else:
                        correct = False
                        json_str += " " * indent + f"<span style='background-color:#FF6347;'>{{</span>\n{{\n{s}" + " " * indent + "}\n"
                elif isinstance(entry, list):
                    s, correct = self.make_compare_json(entry, report[i], indent + 2)
                    if correct:
                        json_str += " " * indent + f"<span style='background-color:#00FF00;'>[</span>\n{s}" + " " * indent + "]\n"
                    else:
                        correct = False
                        json_str += " " * indent + f"<span style='background-color:#FF6347;'>[</span>\n{{\n{s}" + " " * indent + "]\n"
                else:
                    if report[i][list(report[i].keys())[0]][0]:
                        json_str += " " * indent + f"<span style='background-color:#00FF00;'>{entry if entry != None else 'null'},</span>\n"
                    else:
                        correct = False
                        json_str += " " * indent + f"<span style='background-color:#FF6347;'>{entry if entry != None else 'null'},</span><small>{report[i][list(report[i].keys())[0]][1]}</small>\n"
        return json_str, correct