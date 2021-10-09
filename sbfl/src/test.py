from tooltest import ToolEval
from main import Tool
import xml.etree.ElementTree as ET
import json
import subprocess
import glob
import re
import os

v = """
<a>
    <b>a</b>
    <c>bb</c>
    <f>
        <g>g</g>
        <h>a</h>
    </f>
</a>
"""

e = """
<a>
    <b>a</b>
    <f>
        <g>gg</g>
        <h>a</h>
    </f>
    <e>a</e>
</a>
"""

# t = ToolEval()

# v = ET.fromstring(v)
# e = ET.fromstring(e)

# print(json.dumps(t.makeDictFromXml(v), indent=2))
# print(json.dumps(t.makeDictFromXml(e), indent=2))
# # t.removeNonValidAttr(t.valid_statexml, ET.fromstring(e))
# # ET.dump(t.valid_statexml)

# subprocess.run(['echo', "aaa"], input='hello', text=True)

# def func():
#     try:
#         raise Exception
#     except Exception as e:
#         print("error")


# c = []
# with open("eval/sstubs/sstubs.json") as f:
#     a = json.load(f)
# for b in a:
#     if not b['bugType'] in c:
#         c.append(b['bugType'])
# for d in c:
#     print(d)

# a = {
#     "a": None,
#     "b": {
#         "c": {},
#         "e": {}
#     },
#     "d": {}
# }


# ToolEval.deleteEmptyAttr(a)
# print(a)

loglist = glob.glob('/home/mass/selkit/Research/project/outTest/**/*.log', recursive=True)
htmllist = glob.glob('/home/mass/selkit/Research/project/outTest/**/*.html', recursive=True)
alldirlist = glob.glob('/home/mass/selkit/Research/project/outTest/outEachToolOutput/*/*')
pattern1 = re.compile(r'On running id ([0-9]+)')
pattern2 = re.compile(r'MavenError:')
pattern3 = re.compile(r'CompileEvoSuiteError:')
pattern4 = re.compile(r'(\w+Error|Exception):')
# evocompilep = re.compile(r'CompileEvoSuiteError:')
allnum = 0
mavenerror = 0
evosuiteerror = 0
success = 0
error_list = {}
for logpath in loglist:
    with open(logpath) as f:
        lines = f.read()
    p1_list = pattern1.findall(lines)
    p2_list = pattern2.findall(lines)
    p3_list = pattern3.findall(lines)
    p4_list = pattern4.findall(lines)
    log_len = len(p1_list)
    maven_len = len(p2_list)
    # print(f"{os.path.basename(os.path.dirname(logpath)):<40} {maven_len:>3}/{log_len:<3} {maven_len/log_len * 100:.1f}%")
    p1_max = max([int(e) for e in p1_list])
    p2_len = len(p2_list)
    p3_len = len(p3_list)
    for e in p4_list:
        if not e in error_list:
            error_list[e] = 0
    for e in error_list:
        error_list[e] += p4_list.count(e)
    mavenerror += p2_len
    evosuiteerror += p3_len
allnum = len(alldirlist)
success = allnum - len(loglist)
    
othererror = allnum - mavenerror - evosuiteerror
print(f"all_num={allnum}, MavenError={mavenerror}, EvoSuiteError={evosuiteerror}, otherError={othererror}, success={success}")
print(f"MavenError rate = {mavenerror / allnum * 100:.1f}%")
print(f"EvoSuiteError rate = {evosuiteerror / allnum * 100:.1f}%")
print(f"OtherError rate = {othererror / allnum * 100:.1f}%")
print(f"Success rate = {success / allnum * 100:.2f}%")
print(error_list)

projectoutlist = glob.glob('/home/mass/selkit/Research/project/outTest/outEachToolOutput/*')
for project in projectoutlist:
    mavenerror_num = 0
    project_name = os.path.basename(project)
    loglist = glob.glob(os.path.join(project, "**/*.log"), recursive=True)
    for log in loglist:
        with open(log) as f:
            file_ = f.read()
        if pattern2.findall(file_):
            mavenerror_num += 1
    projectelmnum = len(glob.glob(os.path.join(project, "*")))
    print(f"{project_name:<40} {mavenerror_num:>3}/{len(loglist):<3}  {projectelmnum - len(loglist)}")
    if projectelmnum - len(loglist) > 0:
        htmllist = glob.glob(os.path.join(project, "**/*.html"), recursive=True)
        for html_ in htmllist:
            with open(html_) as f:
                buf = f.read()
            for match in re.findall(r'color: #([\w\d]+?);', buf):
                if match != 'ffffff':
                    print(html_)
                    break


# classfiles = glob.glob('/media/mass/0612390E12390469/eval/**/*.class', recursive=True)
# for c in classfiles:
#     if not "classes" in c and not "ESTest" in c:
#         print(c)

# outpath = '/home/mass/selkit/Research/project/outTest/outEachToolOutput'
# for p in os.listdir(outpath):
#     path_ = os.path.join(outpath, p)
#     if len(os.listdir(path_)) == 0:
#         try:
#             os.rmdir(path_)
#             print(f"{path_} removed")
#         except:
#             print(f"{path_} cannot remove")

# outpath = '/home/mass/selkit/Research/project/outTest/outEachToolOutput'
# all = 0
# count = 0
# html_c = 0
# both = 0
# for p in os.listdir(outpath):
#     path_ = os.path.join(outpath, p)
#     flag1 = flag2 = False
#     if "out2" in os.listdir(path_):
#         all += 1
#         out2path_ = os.path.join(path_, "out2")
#         with open(out2path_) as f:
#             r = f.read()
#         if "test timed out after 4000 milliseconds" in r:
#             count += 1
#             flag1 = True
#     if "outSuspicious.html" in os.listdir(path_):
#         html_c += 1
#         flag2 = True
#     if flag1 and flag2:
#         both += 1
# print(f"all_out2={all}")
# print(f"timeout={count}")
# print(f"html_num={html_c}")
# print(f"timeout&html={both}")

# estest = glob.glob('/media/mass/0612390E12390469/eval/**/*_ESTest.java', recursive=True)
# print(estest)
# assertlist = []
# assertpattern = re.compile(r'\n.*?assert\w*.*?\n')
# with open('/home/mass/selkit/Research/project/outTest/outEachToolOutput/Bukkit.Bukkit/Bukkit.Bukkit_29/Lever_ESTest.java') as f:
#     print(assertpattern.sub(r'\n', f.read()))
# for p in estest:
#     with open(p) as f:
#         file_ = f.read()
#     for a in assertpattern.findall(file_):
#         if not a in assertlist:
#             assertlist.append(a)
# for e in assertlist:
#     print(e)
# print(assertlist)

# t = Tool()
# t.mavenproject_path = "/media/mass/0612390E12390469/eval/nanohttpd"
# t.javasource_path = "/media/mass/0612390E12390469/eval/nanohttpd/webserver/src/main/java/fi/iki/elonen/SimpleWebServer.java"
# t._collectAllClassPath()

# allclass_buf = {}
# print(t.allclass)
# allclass = t.allclass.split(':')
# for classpath in allclass:
#     print("classpath", classpath)
#     allclass_rem = []
#     classfiles = [p.replace(classpath, '') for p in glob.glob(os.path.join(classpath, "**/*.class"), recursive=True)]
#     for buf_classpath, buf_classfiles in allclass_buf.items():
#         print("buf_classpath", buf_classpath)
#         for e_classfiles in classfiles:
#             if e_classfiles in buf_classfiles:
#                 print(f"match {os.path.join(classpath, e_classfiles[1:])} {os.path.join(buf_classpath, e_classfiles[1:])}")
#                 if Tool._pathDistance(t.javasource_path, classpath) < Tool._pathDistance(t.javasource_path, buf_classpath):
#                     allclass_rem.append(buf_classpath)
#                 else:
#                     allclass_rem.append(classpath)
#                 break
#     allclass_buf[classpath] = classfiles
#     for rem_classpath in allclass_rem:
#         if rem_classpath in allclass_buf:
#             del allclass_buf[rem_classpath]
#             print("remove", rem_classpath)
# allclass = list(allclass_buf.keys())
# print(allclass)

    # for classlist in allclass_buf:
    #     for class_ in classlist:
    #         classname = os.path.basename(class_)
    #         for 
    #         if os.path.basename(class_) in [os.path.basename(name) for name in classfiles]:
    #             if Tool._pathDistance(t.javasource_path, class_) > Tool._pathDistance(t.javasource_path, class)
    # allclass_buf.append(classfiles)
        
# print(t.allclass)

# func()
