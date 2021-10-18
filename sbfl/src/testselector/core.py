from extract import extract_testcase_line_number
from maketest import make_alone_test
from maketest import make_selected_test
from coverage import measure_coverage
from select_cov import select_testcase
from shutil import rmtree
from analyze import get_package_name
import traceback
import os
from os import path
import random
import string
import shutil

def start_test_selection(junit_testsuite_path: str, target_source_path: str, classpath: str, sourcepath: str, additional_test_path: list[str]):
    temp_testcase_dir = "temp"
    out_testcase_dir = "out"
    classfile_dir = "tempobj"
    jacoco_dumpfile_dir = "jacocoout"
    jacoco_report_dir = "jacocoreport"

    print("Coverage-based Testcase Selector")
    target = target_source_path
    testsuite_classname = get_package_name(junit_testsuite_path) + "." + path.basename(junit_testsuite_path).replace(".java", "")
    temp_dir = "".join([random.choice(string.ascii_letters + string.digits) for i in range(10)])
    temp_testcase_dir = path.join(temp_dir, temp_testcase_dir)
    out_testcase_dir = path.join(temp_dir, out_testcase_dir)
    classfile_dir = path.join(temp_dir, classfile_dir)
    jacoco_dumpfile_dir = path.join(temp_dir, jacoco_dumpfile_dir)
    jacoco_report_dir = path.join(temp_dir, jacoco_report_dir)
    try:
        testcase_line_numbers = extract_testcase_line_number(junit_testsuite_path)
        testcase_count = len(testcase_line_numbers)
        alone_test_path_list = []
        for i in range(testcase_count):
            alone_test_path = make_alone_test(junit_testsuite_path, i, testcase_line_numbers, temp_testcase_dir)
            alone_test_path_list.append(alone_test_path)
        coverage_list = measure_coverage(alone_test_path_list, junit_testsuite_path, target, path_split(classpath), path_split(sourcepath), testsuite_classname, classfile_dir, jacoco_dumpfile_dir, jacoco_report_dir, additional_testsource_path_list=additional_test_path)
        # for i, coverage in enumerate(coverage_list):
        #     print(i, coverage)
        selected_testcase_number_list = select_testcase(coverage_list)
        print("selected_testcase_number_list =", selected_testcase_number_list)
        selected_test_path = make_selected_test(junit_testsuite_path, selected_testcase_number_list, testcase_line_numbers, out_testcase_dir)
        copied_selected_test_path = shutil.copy(selected_test_path, path.dirname(junit_testsuite_path))
        print("選択したテストケースを以下に格納しました:", path.abspath(copied_selected_test_path))
    except Exception as e:
        print(traceback.format_exc())
        raise
    finally:
        rmtree(temp_dir, ignore_errors=True)
        pass

def path_split(separated_path: str) -> list[str]:
    if not separated_path:
        return []
    if os.name == "nt":
        return separated_path.split(";")
    else:
        return separated_path.split(":")