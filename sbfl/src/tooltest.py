import os.path as path
import os
import json
import subprocess
import multiprocessing
from multiprocessing import Pool
import sys
import traceback
import datetime
import time
import copy
import re
import shutil
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element
from main import Tool

class CompileError(Exception):
    pass

class GitCheckoutError(Exception):
    pass

class GitApplyError(Exception):
    pass

class ToolEval:

    def __init__(self):
        self.bugtype = [
            "CHANGE_NUMERAL",
            "CHANGE_OPERAND",
            "OVERLOAD_METHOD_MORE_ARGS",
            "OVERLOAD_METHOD_DELETED_ARGS",
            "DIFFERENT_METHOD_SAME_ARGS",
            "MORE_SPECIFIC_IF",
            "SWAP_BOOLEAN_LITERAL",
            "LESS_SPECIFIC_IF",
            "CHANGE_UNARY_OPERATOR",
            "SWAP_ARGUMENTS"
        ]
        self.r_e_p_o_p_a_t_h = sys.argv[1]
        self.out_dir = path.join(path.dirname(path.abspath(__file__)), "..", "outTest")
        self.load_s_stu_bs_json()
        self.split_s_stu_bs_by_project()

    def load_s_stu_bs_json(self):
        with open(path.join(self.get_self_path(), "..", "eval", "sstubs", "sstubs.json")) as f:
            self.sstubs = json.load(f)

    def split_s_stu_bs_by_project(self):
        self.sstubs_dict = {}
        for sstubs_element in self.sstubs:
            projectname = sstubs_element['projectName']
            if not projectname in self.sstubs_dict:
                self.sstubs_dict[projectname] = []
            if sstubs_element['bugType'] in self.bugtype:
                self.sstubs_dict[projectname].append(sstubs_element)

    def exec(self, project_list=None, exclude_list=None, finish_notify=False):
        start = time.perf_counter()
        if not project_list:
            self.exec_all_project(exclude_list=exclude_list)
        else:
            self.exec_designated_project(project_list)
        time_result = time.perf_counter() - start
        if finish_notify:
            subprocess.run(["notify-send", __file__, f"time: {time.strftime('%dday %H:%M:%S', time.gmtime(time_result))}"])

    def exec_designated_project(self, target_projects):
        arglist = []
        for projectname, sstubs_list in self.sstubs_dict.items():
            if len(sstubs_list) == 0: continue
            if projectname.split('.')[1] in target_projects:
                arglist.append((projectname, sstubs_list))
        self.split_process(arglist)

    def exec_all_project(self, exclude_list=None):
        arglist = []
        for projectname, sstubs_list in self.sstubs_dict.items():
            if len(sstubs_list) == 0: continue
            if not exclude_list:
                arglist.append((projectname, sstubs_list))
            else:
                if not projectname.split('.')[1] in exclude_list:
                    arglist.append((projectname, sstubs_list))
        # print([a[0] for a in arglist])
        self.split_process(arglist)

    def split_process(self, arglist):
        pool = Pool(8)
        pool_res = pool.map(self.eval_process_handler, arglist)
        print(pool_res)
        with open(path.join(self.out_dir, "result.txt"), mode='w') as f:
            for res in pool_res:
                projectname, rank_result, status = res
                print(projectname, file=f)
                print(json.dumps(rank_result, indent=2), file=f)
                print("", file=f)


    def eval_process_handler(self, arg):
        # PROPATY
        a_m_b_i_g_u_i_t_y_d_e_t_e_c_t_l_o_o_p_c_o_u_n_t = 3

        projectname, sstubs_list = arg
        rank_result = {}
        self.sstubs = sstubs_list
        if not path.exists(self.get_project_path(0)):
            return (projectname, {}, "not exist")
        for id, sstubs_element in enumerate(sstubs_list):
            try:

                if "Test" in path.basename(sstubs_element['bugFilePath']):
                    continue

                # return to buggy git version
                self.checkout_to_parent_virsion(id)

                # make output dir
                out_dir = path.join(self.out_dir, "outEachToolOutput", projectname, f"{projectname}_{id}") + os.path.sep
                if not path.exists(out_dir):
                    os.makedirs(out_dir)

                # save sstub
                with open(out_dir + "sstub.json", mode='w') as f:
                    json.dump(sstubs_element, f, indent=2)

                # Tool phase1 setup and launch -> evosuite Test
                t = Tool()
                t.output_dir = out_dir
                if not path.exists(t.output_dir):
                    os.makedirs(t.output_dir)
                t.setPath(self.get_project_path(id), self.get_java_path(id))
                shutil.copy(self.get_java_path(id), out_dir)
                os.rename(path.join(out_dir, path.basename(self.get_java_path(id))), path.join(out_dir, path.basename(self.get_java_path(id)) + "_raw"))
                t.phase1()

                # attach patch -> fixed Program
                self.attach_patch(id)
                shutil.copy(self.get_java_path(id), out_dir)
                os.rename(path.join(out_dir, path.basename(self.get_java_path(id))), path.join(out_dir, path.basename(self.get_java_path(id)) + "_patched"))

                # calculate which attribute value does not fluctuate -> valid attribute
                t.compile_maven_project()
                e_s_tests = t.getESTestFiles()
                assert_pattern = re.compile(r'\n.*?assert\w*.*?\n')
                e_s_test_buf = []
                estest = None
                for e in e_s_tests:
                    if "ESTest.java" in e:
                        estest = e
                with open(estest, mode='r+') as f:
                    readbuf = f.read()
                    e_s_test_buf = readbuf
                with open(estest, mode='w') as f:
                    f.write(assert_pattern.sub(r'\n', readbuf))
                t.compileEvosuiteTest()
                with open(estest, mode='w') as f:
                    f.write(e_s_test_buf)
                valid_attr_xml = {}
                measured_attr = []
                for i in range(a_m_b_i_g_u_i_t_y_d_e_t_e_c_t_l_o_o_p_c_o_u_n_t):
                    t.execEvosuiteTest()
                    os.rename(path.join(t.output_dir, "EvoSuiteTestOutput"), path.join(t.output_dir, f"EvoSuiteTestOutput_{i}"))
                    t.collectObjectStateXML()
                    measured_attr.append({})
                    for testname, objects in t.testcase_finalstate.items():
                        measured_attr[i][testname] = {}
                        if not testname in valid_attr_xml:
                            valid_attr_xml[testname] = {}
                        for objectname, xml_ET in objects.items():
                            measured_attr[i][testname][objectname] = self.make_dict_from_xml(xml_ET)
                            if not objectname in valid_attr_xml[testname]:
                                valid_attr_xml[testname][objectname] = xml_ET
                            else:
                                self.remove_non_valid_attr(valid_attr_xml[testname][objectname], xml_ET)
                with open(path.join(t.output_dir, f"measured_attr.json"), mode="w") as f:
                    json.dump(measured_attr, f, indent=2)

                # return to buggy git version -> undo patch
                self.checkout_to_parent_virsion(id)
                shutil.copy(self.get_java_path(id), out_dir)
                os.rename(path.join(out_dir, path.basename(self.get_java_path(id))), path.join(out_dir, path.basename(self.get_java_path(id)) + "_depatched"))

                # make json from valid attribute -> expected json
                json_dir = t.output_dir
                json_path = path.join(json_dir, f"exp_{id}.json")
                if not path.exists(json_dir):
                    os.makedirs(json_dir)
                json_dict = {}
                with open(json_path, mode='w') as f:
                    for testname, objects in valid_attr_xml.items():
                        json_dict[testname] = {}
                        for objectname, xml in objects.items():
                            json_dict[testname]["finallyObjectState"] = {
                                objectname: self.make_dict_from_xml(valid_attr_xml[testname][objectname])
                            }
                    ToolEval.delete_empty_attr(json_dict)
                    if len(json_dict) == 0:
                        raise Exception("expected json file length is 0")
                    json.dump(json_dict, f, indent=2)

                # Tool phase2 setup and launch -> suspicious value
                if not path.exists(t.output_dir):
                    os.makedirs(t.output_dir)
                t.output_dir += path.sep
                t.setPath(self.get_project_path(id), self.get_java_path(id), json_path)
                t.phase2()

                # output suspicious value in json
                suspicious_dir = t.output_dir
                suspicious_path = path.join(suspicious_dir, f"susp_{id}.txt")
                if not path.exists(suspicious_dir):
                    os.makedirs(suspicious_dir)
                with open(suspicious_path, mode='w') as f:
                    print(f"{sstubs_element['bugFilePath']}", file=f)
                    print(json.dumps(t.ochiai, indent=2), file=f)

                # calculate rank
                fixline_name = f"line{sstubs_element['fixLineNum']}"
                rank = 0
                now_rank_value = float('inf')
                rank_result[str(id)] = {}
                rank_result[str(id)]['sstubs'] = sstubs_element
                rank_result[str(id)]['ochiai'] = t.ochiai
                if fixline_name in t.ochiai:
                    sorted_ochiai = sorted(t.ochiai.items(), key=lambda x:x[1], reverse=True)
                    for line_tuple in sorted_ochiai:
                        linename, suspicious = line_tuple
                        if now_rank_value != suspicious:
                            rank += 1
                            now_rank_value = suspicious
                        if fixline_name == linename:
                            break
                    rank_result[str(id)]['rank'] = rank
            except:
                log_dir = path.join(self.out_dir, "outEachToolOutput", projectname, f"{projectname}_{id}") + os.path.sep
                if not path.exists(log_dir):
                    os.makedirs(log_dir)
                with open(path.join(log_dir, "error.log"), mode="w") as f:
                    print(datetime.datetime.now().strftime("written in: %Y/%m/%d %H:%M:%S"), file=f)
                    print(f"On running id {id} (file: \"{path.join(self.r_e_p_o_p_a_t_h, sstubs_element['projectName'].split('.')[1], sstubs_element['bugFilePath'])}\" commit: {sstubs_element['fixCommitParentSHA1']})", file=f)
                    f.write(traceback.format_exc())
                    print("", file=f)

            if len(os.listdir(t.output_dir)) == 0:
                    os.rmdir(t.output_dir)

        return (projectname, rank_result, "success")

    def remove_non_valid_attr(self, valid_elm:Element, element:Element) -> bool:
        remove_element = []
        for i, vl in enumerate(valid_elm):
            e = element.find(vl.tag)
            if e == None:
                remove_element.append(vl)
                continue
            elif len(e): # if e has some number of children
                if not self.remove_non_valid_attr(vl, e):
                    remove_element.append(vl)
                continue
            elif vl.text != e.text:
                remove_element.append(vl)
        for elm in remove_element:
            valid_elm.remove(elm)
        if len(valid_elm) == 0:
            return False
        return True

    def make_dict_from_xml(self, xml_tree:Element) -> dict:
        xml_dict = {}
        for xml_elm in xml_tree:
            if len(xml_elm):
                xml_dict[xml_elm.tag] = self.make_dict_from_xml(xml_elm)
            else:
                xml_dict[xml_elm.tag] = xml_elm.text
        return xml_dict

    @staticmethod
    def delete_empty_attr(exp_dict:dict) -> bool:
        exp_dict_copy = copy.deepcopy(exp_dict)
        for name, val in exp_dict_copy.items():
            if not val:
                del exp_dict[name]
            elif isinstance(val, dict):
                if ToolEval.delete_empty_attr(exp_dict[name]):
                    del exp_dict[name]
        print([e for e in exp_dict.values() if e])
        print(exp_dict)
        print(len([e for e in exp_dict.values() if e]) == 0)
        return len([e for e in exp_dict.values() if e]) == 0

    def checkout_to_parent_virsion(self, id):
        self.delete_index_lock(id)
        res = subprocess.run(["git", "checkout", "--force", self.sstubs[id]['fixCommitParentSHA1']], cwd=self.get_project_path(id))
        if res.returncode != 0:
            raise GitCheckoutError(f"{id} checkout (sha1: {self.sstubs[id]['fixCommitParentSHA1']})")

    def delete_index_lock(self, id):
        index_lock_path = path.join(self.get_project_path(id), ".git", "index.lock")
        if path.exists(index_lock_path):
            os.remove(index_lock_path)

    def compile_maven_project(self, id):
        result = subprocess.run("mvn compile", cwd=self.get_project_path(id), shell=True)
        if result.returncode != 0:
            raise CompileError

    def attach_patch(self, id):
        res = subprocess.run(["git", "apply"], input=self.sstubs[id]['fixPatch'], text=True, cwd=self.get_project_path(id))
        if res.returncode != 0:
            raise GitApplyError(f"{id} apply ({self.sstubs[id]['fixPatch']})")

    def get_project_path(self, id):
        sstubs_projectname = self.sstubs[id]['projectName'].split('.')[1]
        return path.join(self.r_e_p_o_p_a_t_h, sstubs_projectname)

    def get_java_path(self, id):
        return path.join(self.get_project_path(id), self.sstubs[id]['bugFilePath'])

    def _getFixCommitParentSHA1(self, id):
        return self.sstubs[id]['fixCommitParentSHA1']

    def get_self_path(self):
        return path.dirname(path.abspath(__file__))

if __name__ == "__main__":
    te = ToolEval()
    target_projects = [
        "nanohttpd"
    ]
    exclude_projects = [
        "storm",
        "deeplearning4j",
        "spring-boot",
        "hive",
        "presto",
        "camel",
        "hadoop",
        "netty",
        "jersey",
        "canal",
        "hbase",
        "guice",
        "neo4j",
        "Android-PullToRefresh"
    ]
    te.exec(finish_notify=True)
