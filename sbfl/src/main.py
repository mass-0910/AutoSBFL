import sys
import os.path as path
sys.path.append(path.join(path.dirname(__file__), "testselector"))
import os
import glob
import subprocess
import traceback
import argparse
import json
import re
import math
import shutil
from copy import deepcopy
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element
from testselector.core import start_test_selection
from testselector.extract import extract_testcase_line_number
from testselector.maketest import make_alone_test
from testselector.coverage import measure_coverage
from testselector.analyze import get_package_name
from utility import Util
from makehtml import SuspiciousHtmlMaker

class CompileEvoSuiteError(Exception):
    pass

class MavenError(Exception):
    pass

class MakeEvoSuiteError(Exception):
    pass

class ExpectFileError(Exception):
    pass

class TempDirExistError(Exception):
    pass

class Tool:

    def __init__(self):
        self.mavenproject_path = ""
        self.javasource_path = ""
        self.javaclass_path = ""
        self.exist_code_number = []
        self.exist_test_number = []
        self.testcase_coverage = {}
        self.output_dir = "out"
        self.evacuration_buf = {}
        self.allclass = None
        self.temp_dir = "temp"
        if os.name == "nt":
            self.javapath_split_char = ";"
        else:
            self.javapath_split_char = ":"

    def set_path(self, mavenproject_path, javasource_path, expectedvaluefile_path=None):
        self.mavenproject_path = path.abspath(mavenproject_path)
        self.javasource_path = path.abspath(javasource_path)
        self.expectedjson_path = path.abspath(expectedvaluefile_path)
        if not path.exists(mavenproject_path):
            raise FileNotFoundError(mavenproject_path + " doesn't exist.")
        if not path.exists(javasource_path):
            raise FileNotFoundError(javasource_path + " doesn't exist.")
        if expectedvaluefile_path:
            if not path.exists(expectedvaluefile_path):
                raise FileNotFoundError(expectedvaluefile_path + " doesn't exist.")
            with open(expectedvaluefile_path, mode='r') as f:
                try:
                    json.load(f)
                except:
                    raise

    def phase1(self):
        print("AutoSBFL Phase1")
        try:
            self.compile_maven_project()
            self.source2ClassPath()
            self.make_evosuite_test()
            self.modify_evosuite_test(self.get_evosuite_test_path())
            self.modify_scaffolding(self.get_evosuite_test_scaffolding_path())
            start_test_selection(
                self.get_evosuite_test_path(),
                self.javasource_path,
                self.collect_all_class_path(),
                self.collect_all_source_path(),
                [self.get_evosuite_test_scaffolding_path()]
            )
        except:
            raise

    def phase2(self):
        print("AutoSBFL Phase2")
        try:
            self.make_temp_dir()
            self.make_out_dir()
        except:
            raise
        self.backup_testcase()
        try:
            self.source2ClassPath()
            self.compile_maven_project()
            self.add_infomation_output_to_evosuite_test(self.get_selected_evosuite_test_path())
            self.compile_evosuite_test()
            self.exec_evosuite_test()
            self.collect_coverage()
            self.collect_object_state_xml()
            self.collect_stdout()
            self.judge_test()
            self.calculate_ochiai()
            self.make_coverage_csv()
            self.make_suspicious_value_html()
        except:
            raise
        finally:
            self.recover_testcase()
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            pass

    def make_temp_dir(self):
        if not path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        else:
            raise TempDirExistError("Temporary directory has already existed")

    def make_out_dir(self):
        if not path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def backup_testcase(self):
        shutil.copy(self.get_selected_evosuite_test_path(), self.temp_dir)

    def recover_testcase(self):
        shutil.copy(path.join(self.temp_dir, path.basename(self.get_selected_evosuite_test_path())), self.get_selected_evosuite_test_path())

    def source2ClassPath(self):
        classnames = get_class_name(self.javasource_path)
        packagename = get_package_name(self.javasource_path)
        if not classnames:
            print("%s has no class" % self.javasource_path)
            return
        for classname in classnames:
            parent = path.dirname(self.javasource_path)
            end = False
            before_dir = ""
            while parent != path.dirname(self.mavenproject_path):
                glob_list = []
                for dir_ in os.listdir(parent):
                    if path.isdir(path.join(parent, dir_)) and dir_ != before_dir:
                        glob_list.append(path.join(parent, dir_))
                classfile_pathes = []
                for globdir in glob_list:
                    classfile_pathes += glob.glob(path.join(globdir, "**/*.class"), recursive=True)
                # print(classfile_pathes)
                for classfile in classfile_pathes:
                    # print(classfile)
                    if path.basename(classfile) == classname + ".class" and packagename.replace('.', path.sep) in classfile:
                        classfile_packagename = packagename.replace('.', path.sep) + path.sep + classname + ".class"
                        self.javaclass_path = classfile.replace(classfile_packagename, "")
                        # print("a = " + packagename)
                        self.javaclass_name = packagename + "." + classname
                        end = True
                        break
                if end: break
                before_dir = path.basename(parent)
                parent = path.dirname(parent)

    def file_copy_and_make_line_list(self, filepath, temppath) -> list:
        with open(filepath, mode="r+") as f:
            # with open(temppath, mode="w") as tmpf:
            #     tmpf.write(f.read())
            self.evacuration_buf[temppath] = f.read()
            f.seek(0, 0)
            source_lines = [line.rstrip(os.linesep) for line in f.readlines()]
        return source_lines

    def remove_comment(self, source_lines) -> list:
        in_comment = False
        for i, line in enumerate(source_lines):
            buf = ""
            next = False
            for character in line:
                if not in_comment:
                    if character == "/" and not next:
                        next = True
                        continue
                    if next:
                        next = False
                        if character == "*":
                            in_comment = True
                            continue
                        elif character == "/":
                            break
                        else:
                            buf += "/"
                            continue

                if in_comment:
                    if character == "*" and not next:
                        next = True
                        continue
                    if next:
                        next = False
                        if character == "/":
                            in_comment = False
                    continue

                buf += character

            # print(buf)
            source_lines[i] = buf
        return source_lines

    def undo_add_line_num(self):
        self.undo_copy(self.javasource_path, "temp1")

    def copy(self, src_path, copy_path):
        # with open(src_path, mode="r") as rf, open(copy_path, mode="w") as wf:
        #     wf.write(rf.read())
        with open(src_path, mode="r") as rf:
            self.evacuration_buf[copy_path] = rf.read()

    def undo_copy(self, src_path, copy_path):
        # with open(copy_path, mode="r") as rf, open(src_path, mode="w") as wf:
        #     wf.write(rf.read())
        with open(src_path, mode="w") as wf:
            wf.write(self.evacuration_buf[copy_path])

    def compile_maven_project(self):
        #print(self.mavenproject_path)
        print("compiling target project...", end="")
        result0 = subprocess.run("mvn clean", cwd=self.mavenproject_path, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result0.returncode != 0:
            raise MavenError("Maven clean finished with Error!")
        result1 = subprocess.run("mvn compile", cwd=self.mavenproject_path, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result1.returncode != 0:
            raise MavenError("Maven compile finished with Error!")
        # result2 = subprocess.run(["mvn", "test-compile"], cwd=self.mavenproject_path)
        # if result2.returncode != 0:
        #     raise MavenError("Maven test-compile finished with Error!")
        print("done")

    def get_this_project_path(self) -> str:
        return path.dirname(path.dirname(path.dirname(path.abspath(__file__))))

    def collect_all_source_path(self) -> str:
        src_dir_list = glob.glob(path.join(self.mavenproject_path, "**/src/main/java"), recursive=True)
        return self.javapath_split_char.join(src_dir_list)

    def collect_all_class_path(self) -> str:
        if self.allclass == None:
            path_includes_classes = glob.glob(path.join(self.mavenproject_path, "**/*classes*"), recursive=True)
            self.allclass = self.javapath_split_char.join(self.delete_same_class_path(path_includes_classes))
        return self.allclass

    def delete_same_class_path(self, class_list:list) -> list:
        allclass_buf = {}
        for classpath in class_list:
            allclass_rem = []
            classfiles = [p.replace(classpath, '') for p in glob.glob(os.path.join(classpath, "**/*.class"), recursive=True)]
            for buf_classpath, buf_classfiles in allclass_buf.items():
                for e_classfiles in classfiles:
                    if e_classfiles in buf_classfiles:
                        if Tool.path_distance(self.javasource_path, classpath) < Tool.path_distance(self.javasource_path, buf_classpath):
                            allclass_rem.append(buf_classpath)
                        else:
                            allclass_rem.append(classpath)
                        break
            allclass_buf[classpath] = classfiles
            for rem_classpath in allclass_rem:
                if rem_classpath in allclass_buf:
                    del allclass_buf[rem_classpath]
                    #print("remove", rem_classpath)
        return list(allclass_buf.keys())

    def make_evosuite_test(self) -> str:
        #print("make_evosuite_test start")
        evosuite_command = ["java", "-jar", path.join(self.get_this_project_path(), "ext-modules", "evosuite-1.1.0.jar"), "-class", self.javaclass_name, "-projectCP", self.collect_all_class_path()]
        # raise Exception(str(evosuite_command))
        #print(f"execute: {' '.join(evosuite_command)}")
        result = subprocess.run(evosuite_command, cwd=self.mavenproject_path)
        if result.returncode != 0:
            raise MakeEvoSuiteError("Some exception has occured in Making EvoSuite Test!")


    def get_java_environment(self) -> dict:
        #print("path = " + self.get_this_project_path())
        evosuite_compile_classpath = self.javapath_split_char.join([
            self.collect_all_class_path(),
            path.join(self.get_this_project_path(), "ext-modules", "evosuite-standalone-runtime-1.1.0.jar"),
            "evosuite-tests",
            path.join(self.get_this_project_path(), "ext-modules", "junit-4.12.jar"),
            path.join(self.get_this_project_path(), "ext-modules", "hamcrest-2.2.jar"),
            path.join(self.get_this_project_path(), "ext-modules", "xstream", "xstream-1.4.18", "lib", "xstream-1.4.18.jar"),
            path.join(self.get_this_project_path(), "ext-modules", "xstream", "xstream-1.4.18", "lib", "xstream", "*")
        ])
        java_environ = os.environ
        java_environ["CLASSPATH"] = evosuite_compile_classpath
        return java_environ

    def get_evosuite_test_path(self) -> str:
        javafiles = glob.glob(path.join(self.mavenproject_path, "evosuite-tests/**/*.java"), recursive=True)
        for esfile in javafiles:
            if get_class_name(self.javasource_path)[0] + "_ESTest.java" in esfile:
                testcase_file = esfile
                break
        try:
            return testcase_file
        except:
            raise Exception("javafile: " + str(javafiles) + "\nclassname: " + str(get_class_name(self.javasource_path)[0]))

    def get_selected_evosuite_test_path(self) -> str:
        javafiles = glob.glob(path.join(self.mavenproject_path, "evosuite-tests/**/*.java"), recursive=True)
        for esfile in javafiles:
            if get_class_name(self.javasource_path)[0] + "_ESTest_selected.java" in esfile:
                testcase_file = esfile
                break
        try:
            return testcase_file
        except:
            raise Exception("javafile: " + str(javafiles) + "\nclassname: " + str(get_class_name(self.javasource_path)[0]))

    def get_evosuite_test_scaffolding_path(self) -> str:
        javafiles = glob.glob(path.join(self.mavenproject_path, "evosuite-tests/**/*.java"), recursive=True)
        for esfile in javafiles:
            if get_class_name(self.javasource_path)[0] + "_ESTest_scaffolding.java" in esfile:
                testcase_file = esfile
                break
        return testcase_file

    def compile_evosuite_test(self):
        print("compiling evosuite test...", end="")
        javafiles = [self.get_selected_evosuite_test_path(), self.get_evosuite_test_scaffolding_path()]
        try:
            testcase_file = self.get_selected_evosuite_test_path()
        except:
            raise
        scaffolding_file = self.get_evosuite_test_scaffolding_path()
        try:
            self.modify_evosuite_test(testcase_file)
        except:
            self.undo_copy(testcase_file, "temp2")
            raise
        try:
            self.modify_scaffolding(scaffolding_file)
        except:
            self.undo_copy(scaffolding_file, "temp3")
            raise
        # if self.output_dir:
        #     shutil.copy(testcase_file, self.output_dir)
        try:
            command = ["javac", "-g"] + javafiles
            #print(' '.join(command))
            result = subprocess.run(command, env=self.get_java_environment(), cwd=self.mavenproject_path)
            if result.returncode != 0:
                raise CompileEvoSuiteError("Some exception has occured in Compiling EvoSuite Test!")
            self.undo_copy(testcase_file, "temp2")
            self.undo_copy(scaffolding_file, "temp3")
        except:
            #print("m")
            self.undo_copy(testcase_file, "temp2")
            self.undo_copy(scaffolding_file, "temp3")
            raise
        print("done")

    def modify_evosuite_test(self, evosuite_test_path):
        #print("modify_evosuite_test start")
        virtual_jvm_pattern = re.compile(r'mockJVMNonDeterminism = true')
        separate_class_loader_pattern = re.compile(r'separateClassLoader = true')
        timeout_pattern = re.compile(r'@Test\(timeout = [0-9]+\)')
        try:
            source_lines = self.file_copy_and_make_line_list(evosuite_test_path, "temp2")
            with open(evosuite_test_path, mode='w') as f:
                imported = False
                for line in source_lines:
                    tokenized_line = Util.split_token(line)
                    if not imported and "import" in tokenized_line:
                        print("import com.thoughtworks.xstream.XStream;", file=f)
                        imported = True
                    line_replaced = timeout_pattern.sub("@Test", separate_class_loader_pattern.sub(r'separateClassLoader = false', virtual_jvm_pattern.sub(r"mockJVMNonDeterminism = false", line)))
                    print(line_replaced, file=f)
        except:
            raise

    def modify_scaffolding(self, scaffoldinf_path):
        #print("modify_scaffolding start")
        try:
            source_lines = self.file_copy_and_make_line_list(scaffoldinf_path, "temp3")
            with open(scaffoldinf_path, mode='w') as f:
                for line in source_lines:
                    if "org.evosuite.runtime.RuntimeSettings.maxNumberOfIterationsPerLoop = 10000;" in line:
                        print(line.replace("10000", "1000000"), file=f)
                    else:
                        print(line, file=f)
        except:
            raise

    def add_infomation_output_to_evosuite_test(self, evosuite_test_path):
        #print("add_infomation_output start")
        try:
            source_lines = self.file_copy_and_make_line_list(evosuite_test_path, "temp3")
            with open(evosuite_test_path, mode='w') as f:
                func_dive = 0
                in_func = False
                objectname = []
                for line in source_lines:
                    tokenized_line = Util.split_token(line)
                    if len(tokenized_line) >= 3:
                        if tokenized_line[0] == "public" and tokenized_line[1] == "void" and "test" in tokenized_line[2]:
                            test_number = tokenized_line[2].replace("test", "")
                            print(line, file=f)
                            print("System.out.println(\"ESTest_test[" + test_number + "]\");", file=f)
                            func_dive = 1
                            in_func = True
                            continue
                    if in_func:
                        func_dive += tokenized_line.count('{')
                        func_dive -= tokenized_line.count('}')
                        if len(tokenized_line) >= 2:
                            if get_class_name(self.javasource_path)[0] == tokenized_line[0] and Util.is_identifier(tokenized_line[1]):
                                objectname.append(tokenized_line[1])
                        if func_dive == 0:
                            in_func = False
                            for o in objectname:
                                print("System.out.println(\"FinallyObjectAttributes_start[" + o + "]\");", file=f)
                                print("try{System.out.println(new XStream().toXML(" + o + "));}catch(Exception e){e.printStackTrace();}", file=f)
                                print("System.out.println(\"FinallyObjectAttributes_end[" + o + "]\");", file=f)
                            objectname = []
                    print(line, file=f)
        except:
            raise

    def exec_evosuite_test(self):
        print("executing evosuite test...", end="")
        command = ["java", "org.junit.runner.JUnitCore", get_package_name(self.javasource_path) + "." + get_class_name(self.javasource_path)[0] + "_ESTest_selected"]
        #print("execevosuite: " + " ".join(command))
        result = subprocess.run(command, env=self.get_java_environment(), cwd=self.mavenproject_path, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.output = result.stdout.replace(b"\x0D\x0A", b"\x0A").decode("utf-8")
        self.output_list = self.output.split("\n")
        with open(path.join(self.output_dir, "EvoSuiteTestOutput"), mode='w') as f:
            for l in self.output_list:
                print(l, file=f)
        print("done")

    def collect_coverage(self):
        print("collecting coverage...")
        # measure coverage
        testcase_line_numbers = extract_testcase_line_number(self.get_selected_evosuite_test_path())
        testcase_count = len(testcase_line_numbers)
        alone_test_path_list = []
        for i in range(testcase_count):
            alone_test_path = make_alone_test(self.get_selected_evosuite_test_path(), i, testcase_line_numbers, self.temp_dir)
            alone_test_path_list.append(alone_test_path)
        coverage_list = measure_coverage(
            alone_test_path_list,
            self.get_selected_evosuite_test_path(),
            self.javasource_path,
            self.collect_all_class_path().split(self.javapath_split_char),
            self.collect_all_source_path().split(self.javapath_split_char),
            get_package_name(self.get_selected_evosuite_test_path()) + "." + path.basename(self.get_selected_evosuite_test_path()).replace(".java", ""),
            path.join(self.temp_dir, "classes"),
            path.join(self.temp_dir, "dumps"),
            path.join(self.temp_dir, "reports"),
            [self.get_evosuite_test_scaffolding_path()]
        )
        # exist code number
        allcov = None
        for cov in coverage_list:
            if allcov == None:
                allcov = cov
            else:
                allcov = allcov.merged(cov)
        self.exist_code_number = sorted(allcov.passed_line)
        #exist test number
        testname_list = self.get_testcase_name_list(self.get_selected_evosuite_test_path())
        for testname in testname_list:
            self.exist_test_number.append(int(re.match("test([0-9]+)", testname).group(1)))
        # extract coverage
        for i, testname in enumerate(testname_list):
            self.testcase_coverage[testname] = {}
            for line_num in self.exist_code_number:
                if line_num in coverage_list[i].passed_line:
                    self.testcase_coverage[testname]["line" + str(line_num)] = 1
                else:
                    self.testcase_coverage[testname]["line" + str(line_num)] = 0
        print("done")

    def get_testcase_name_list(self, junit_testsuite_path) -> list[str]:
        retval = []
        with open(junit_testsuite_path, mode='r') as f:
            source_lines = f.read().split("\n")
            #print(source_lines)
            func_dive = 0
            in_func = False
            for line in source_lines:
                tokenized_line = Util.split_token(line)
                if len(tokenized_line) >= 3:
                    if tokenized_line[0] == "public" and tokenized_line[1] == "void" and "test" in tokenized_line[2]:
                        retval.append(tokenized_line[2])
                        func_dive = 1
                        in_func = True
                        continue
                if in_func:
                    func_dive += tokenized_line.count('{')
                    func_dive -= tokenized_line.count('}')
                    if func_dive == 0:
                        in_func = False
        #print("alltest: " + str(retval))
        return retval

    def collect_object_state_xml(self):
        print("collecting actually status of object from test result...", end="")
        final_state = {}
        testnum_str = "ESTest_test["
        xml_start_str = "FinallyObjectAttributes_start["
        xml_end_str = "FinallyObjectAttributes_end["
        in_xml = False
        for line in self.output_list:
            if testnum_str in line:
                testnumber = 0
                i = line.find(testnum_str) + len(testnum_str)
                while i < len(line) and line[i].isdigit() and line[i] != ']':
                    testnumber = int(line[i]) + testnumber * 10
                    i += 1
                final_state["test" + str(testnumber)] = {}
                continue
            if xml_start_str in line:
                i = line.find(xml_start_str) + len(xml_start_str)
                buf = ""
                while i < len(line) and line[i].isalnum() and line[i] != ']':
                    buf += line[i]
                    i += 1
                xmlobject_name = buf
                final_state["test" + str(testnumber)][xmlobject_name] = ""
                in_xml = True
                continue
            if xml_end_str in line:
                in_xml = False
                continue
            if in_xml:
                final_state["test" + str(testnumber)][xmlobject_name] += line + "\n"
        # with open(path.join(self.output_dir, "out_attrs.json"), mode='w') as f:
        #     json.dump(final_state, fp=f, indent=4)
        self.convert_state_xml_to_element_tree(final_state)
        self.dict_testcase_state = deepcopy(self.testcase_finalstate)
        for testcase in self.dict_testcase_state.keys():
            for object in self.dict_testcase_state[str(testcase)].keys():
                self.dict_testcase_state[str(testcase)] = {
                    "finalObjectState": {
                        object: self.make_dict_from_xml(self.dict_testcase_state[str(testcase)][str(object)])
                    }
                }
        with open(path.join(self.output_dir, "out_attrs.json"), mode='w') as f:
            json.dump(self.dict_testcase_state, fp=f, indent=4)
        print("done")

    def make_dict_from_xml(self, xml_tree:Element):
        if len(xml_tree) == 0:
            if xml_tree.text == None: return None
            if re.match(r"^[+-]?\d+$", xml_tree.text):
                return int(xml_tree.text)
            elif re.match(r"^[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$", xml_tree.text):
                return float(xml_tree.text)
            else:
                return xml_tree.text
        # select mode
        name_list = []
        mode = 0 # object mode
        for elm in xml_tree:
            if elm.tag in name_list or elm.tag == "null":
                mode = 1 # list mode
                break
            else:
                name_list.append(elm.tag)
        # on mode
        if mode == 0 : entity = {}
        if mode == 1 : entity = []
        for xml_elm in xml_tree:
            if mode == 0:
                entity[xml_elm.tag.replace("__", "_")] = self.make_dict_from_xml(xml_elm)
            elif mode == 1:
                entity.append(self.make_dict_from_xml(xml_elm))
        return entity

    def collect_stdout(self):
        print("collecting stdout string from test result...", end="")
        self.testcase_stdout = {}
        test_re = re.compile(r"\.ESTest_test\[[0-9]+?\]\n")
        testnum_re = re.compile(r"\.ESTest_test\[([0-9]+?)\]\n")
        xml_re = re.compile(r"FinallyObjectAttributes_start\[\w+\].+?FinallyObjectAttributes_end\[\w+\]\n", re.MULTILINE | re.DOTALL)
        last_re = re.compile(r"\nTime: [0-9]+\.[0-9]+\n\nOK \([0-9]+ tests\)\n\n", re.MULTILINE | re.DOTALL)
        stdout_all = last_re.sub("", xml_re.sub("", self.output))
        testcase_stdout_list = test_re.split(stdout_all)
        del testcase_stdout_list[0]
        testcase_order = testnum_re.findall(stdout_all)
        for i, testnum in enumerate(testcase_order):
            self.testcase_stdout["test" + testnum] = testcase_stdout_list[i]
        with open(path.join(self.output_dir, "outstdout.json"), mode='w') as f:
            json.dump(self.testcase_stdout, f, indent=4)
        print("done")

    def convert_state_xml_to_element_tree(self, finalstate):
        pattern = re.compile(u'&#x[0-9]+;')
        self.testcase_finalstate = {}
        for testname, state_XMLs in finalstate.items():
            self.testcase_finalstate[testname] = {}
            for objectname, state_XML in state_XMLs.items():
                self.testcase_finalstate[testname][objectname] = ET.fromstring(pattern.sub(u'',state_XML))

    def judge_test(self):
        print("verifying expected values with actually values...")
        self.testcase_passfail = {}
        self.judge_report = {}
        with open(self.expectedjson_path, mode='r') as f:
            expected_dict:dict = json.load(f)
        for testname, finally_status_dict in expected_dict.items():
            if "result" in finally_status_dict:
                if finally_status_dict["result"] == "pass":
                    self.testcase_passfail[testname] = True
                elif finally_status_dict["result"] == "fail":
                    self.testcase_passfail[testname] = False
                else:
                    raise ExpectFileError("'result' cannot take a value '" + finally_status_dict["result"] + "' (pass/fail only)")
                continue
            if "finalObjectState" in finally_status_dict:
                self.judge_report[testname] = {}
                state = finally_status_dict["finalObjectState"]
                try:
                    for objectname, status in state.items():
                        self.judge_report[testname][objectname] = {}
                        #print(self.testcase_finalstate)
                        if self.is_satisfied_state(self.testcase_finalstate[testname][objectname], expected_dict=status, judge_report=self.judge_report[testname][objectname]):
                            self.testcase_passfail[testname] = True
                        else:
                            self.testcase_passfail[testname] = False
                except:
                    raise
            if "stdout" in finally_status_dict:
                if not self.testcase_stdout[testname] == finally_status_dict["stdout"]:
                    self.testcase_passfail[testname] = False
        #print(self.testcase_passfail)
        with open(path.join(self.output_dir, "passfail.json"), mode='w') as f:
            json.dump(self.testcase_passfail, f, indent=4)
        with open(path.join(self.output_dir, "judgereport.json"), mode='w') as f:
            json.dump(self.judge_report, f, indent=4)
        if all(pf[1] for pf in self.testcase_passfail.items()):
            print("* all tests passed!")
        else:
            failedtest = []
            for pf in self.testcase_passfail.items():
                if not pf[1]:
                    failedtest.append(pf[0])
            print(f"* {','.join(failedtest)} failed!")

    def calculate_ochiai(self):
        print("calculating suspicious values...", end="")
        self.ochiai = {}
        line_pfnum = {}
        total_fail = 0
        for linenum in self.exist_code_number:
            line_pfnum["line" + str(linenum)] = {
                'pass': 0,
                'fail': 0
            }
        for testname, is_pass in self.testcase_passfail.items():
            if not is_pass:
                total_fail += 1
            for linename, executed_num in self.testcase_coverage[testname].items():
                if executed_num > 0:
                    if is_pass:
                        line_pfnum[linename]['pass'] += 1
                    else:
                        line_pfnum[linename]['fail'] += 1
        for linename, pfnum in line_pfnum.items():
            if math.sqrt(total_fail * (pfnum['fail'] + pfnum['pass'])) == 0:
                self.ochiai[linename] = 0.0
                continue
            self.ochiai[linename] = pfnum['fail'] / math.sqrt(total_fail * (pfnum['fail'] + pfnum['pass']))
        print("done")

    def make_suspicious_value_html(self):
        try:
            html_maker = SuspiciousHtmlMaker(self.javasource_path, path.join(self.temp_dir, path.basename(self.get_selected_evosuite_test_path())), self.ochiai, self.dict_testcase_state, self.testcase_stdout, self.testcase_passfail, self.judge_report)
            html_maker.write_html(self.output_dir, path.join(self.get_this_project_path(), "ext-modules", "google-code-prettify"))
        except:
            raise

    def is_satisfied_state(self, tree:ET.Element, expected_dict:dict=None, expected_list:list=None, judge_report:dict=None) -> bool:
        passed = True
        if expected_dict == None and expected_list == None: raise Exception("is_satisfied_state(): no expected values was given.")
        if expected_dict != None and expected_list != None: raise Exception("is_satisfied_state(): both dict and list was given.")
        if expected_dict != None and expected_list == None:
            for attr_name, exp_value in expected_dict.items():
                attr_tree = tree.find(attr_name.replace("_", "__"))
                if attr_tree != None:
                    if self.is_satisfied_state_loop_element(attr_tree, exp_value, judge_report):
                        continue
                    else:
                        passed = False
                        continue
                else:
                    if self.is_satisfied_value("null", exp_value):
                        continue
                    else:
                        passed = False
                        continue
        elif expected_dict == None and expected_list != None:
            if len(tree) != len(expected_list):
                passed = False
                judge_report[tree.tag.replace("__", "_")] = (False, "incollect array length")
            else:
                judge_report[tree.tag.replace("__", "_")] = []
                for i, exp_value in enumerate(expected_list):
                    judge_report[tree.tag.replace("__", "_")].append({})
                    if not self.is_satisfied_state_loop_element(tree[i], exp_value, judge_report[tree.tag.replace("__", "_")][i]):
                        passed = False
        return passed

    def is_satisfied_state_loop_element(self, attr_tree, exp_elm, judge_report:dict=None) -> bool:
        if isinstance(exp_elm, dict): #if exp_elm is object
            if attr_tree.text != "":
                judge_report[attr_tree.tag.replace("__", "_")] = {}
                return self.is_satisfied_state(attr_tree, expected_dict=exp_elm, judge_report=judge_report[attr_tree.tag.replace("__", "_")])
            else:
                return False
        elif isinstance(exp_elm, list): #if exp_elm is array
            if attr_tree.text != "":
                return self.is_satisfied_state(attr_tree, expected_list=exp_elm, judge_report=judge_report)
            else:
                return False
        else: #if exp_elm is primitive or string
            if attr_tree.tag == "null":
                xml_elm = "null"
            else:
                xml_elm = attr_tree.text
            if exp_elm == None:
                exp_elm = "null"
            # print(attr_tree.tag + " " + str(attr_tree.text) + " " + xml_elm + " " + str(exp_elm))
            if self.is_satisfied_value(xml_elm, str(exp_elm)):
                judge_report[attr_tree.tag.replace("__", "_")] = (True, "")
                return True
            else:
                judge_report[attr_tree.tag.replace("__", "_")] = (False, "expected:" + str(exp_elm))
                return False

    def is_satisfied_value(self, xml_elm_str, exp_elm_str) -> bool:
        if xml_elm_str == "null":
            if exp_elm_str == "null" or exp_elm_str == "any":
                return True
            else:
                return False
        else:
            if exp_elm_str == "any":
                return True
            if xml_elm_str == exp_elm_str:
                return True
            else:
                return False

    def make_coverage_csv(self):
        #print("make_coverage_csv start")
        with open(path.join(self.output_dir, "output.csv"), mode="w") as f:
            print(",", file=f, end="")
            for linenum in self.exist_code_number:
                print("line-" + str(linenum) + ",", file=f, end="")
            print("", file=f)
            self.exist_test_number.sort()
            # for testname, val in self.testcase_coverage.items():
            for testnumber in self.exist_test_number:
                print("test" + str(testnumber) + ",", file=f, end="")
                for linenum in self.exist_code_number:
                    print(str(self.testcase_coverage["test" + str(testnumber)]["line" + str(linenum)]) + ",", file=f, end="")
                print("", file=f)

    @staticmethod
    def path_distance(path1:str, path2:str) -> int:
        path1_split = path1.split(path.sep)
        path2_split = path2.split(path.sep)
        count = 0
        for path1_part, path2_part in zip(path1_split, path2_split):
            if path1_part != path2_part:
                break
            count += 1
        return len(path1_split[count:]) + len(path2_split[count:])


def get_class_name(filename:str) -> list:
    retval = []
    with open(filename) as f:
        in_comment = False
        for line in f.readlines():
            tokenized = Util.split_token(line)
            if tokenized:
                if tokenized[0] == "//": continue
                for i, token in enumerate(tokenized):
                    if token == "//" and not in_comment: break
                    if token == "/*" and not in_comment:
                        in_comment = True
                        continue
                    elif token == "*/" and in_comment:
                        in_comment = False
                        continue
                    if token == "class" and not in_comment:
                        try:
                            if not tokenized[i + 1] in Util.symbol:
                                retval.append(tokenized[i + 1])
                        except IndexError as e:
                            pass
                            #print("Error line: " + line.rstrip(os.linesep))
    return retval

def get_package_name(filename:str) -> str:
    retval = ""
    with open(filename) as f:
        in_comment = False
        for line in f.readlines():
            if retval: break
            tokenized = Util.split_token(line)
            if tokenized:
                for i, token in enumerate(tokenized):
                    if token == "//" and not in_comment: break
                    if token == "/*" and not in_comment:
                        in_comment = True
                        continue
                    elif token == "*/" and in_comment:
                        in_comment = False
                        continue
                    if token == "package" and not in_comment:
                        try:
                            buf = ""
                            token = tokenized[i+1]
                            j = i + 1
                            while token != ";":
                                buf += token
                                j += 1
                                token = tokenized[j]
                            retval = buf
                            break
                        except IndexError as e:
                            pass
                            #print("Error line: " + line.rstrip(os.linesep))
    return retval

class Argument(argparse.ArgumentParser):

    def __init__(self, phase1_func, phase2_func):
        super().__init__(description="Auto SBFL debugging tool")
        self.sub_parser = self.add_subparsers(parser_class=argparse.ArgumentParser)
        phase1_parser = self.sub_parser.add_parser("phase1", help="Execute EvoSuite and create a test suite.")
        phase1_parser.add_argument("mavenproject_path", help="Root path of Maven project containing javasource_path")
        phase1_parser.add_argument("javasource_path", help="The java source path you want to debug")
        phase1_parser.set_defaults(handler=phase1_func)
        phase2_parser = self.sub_parser.add_parser("phase2", help="Calculate suspicious score")
        phase2_parser.add_argument("mavenproject_path", help="Root path of Maven project containing javasource_path")
        phase2_parser.add_argument("javasource_path", help="The java source path you want to debug")
        phase2_parser.add_argument("expectedvaluefile_path", help="The path of the file that describes the final state of the object in each test of the displayed test case")
        phase2_parser.set_defaults(handler=phase2_func)
        help_parser = self.sub_parser.add_parser("help", help="See 'help -h'")
        help_parser.add_argument("command", help="Command name which help is shown")
        help_parser.set_defaults(handler=self.show_help)

    def show_help(self, args):
        self.parse_args([args.command, '--help'])

if __name__ == "__main__":
    tool = Tool()

    argument = Argument(tool.phase1, tool.phase2)
    args = argument.parse_args()
    if hasattr(args, 'handler'):
        try:
            if not hasattr(args, 'command'):
                if hasattr(args, 'expectedvaluefile_path'):
                    tool.set_path(args.mavenproject_path, args.javasource_path, args.expectedvaluefile_path)
                else:
                    tool.set_path(args.mavenproject_path, args.javasource_path)
                args.handler()
            else:
                args.handler(args)
        except:
            print(traceback.format_exc())
    else:
        argument.print_help()
