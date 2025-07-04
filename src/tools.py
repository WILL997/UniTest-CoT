import math
import shutil
from config import *
import os
import json
import psutil
import re
import tiktoken
import datetime
import subprocess
#使用了 tiktoken 库来获取与 GPT 模型相关的编码
enc = tiktoken.get_encoding("cl100k_base")
encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

#一个计算消息列表中所有消息的 token 数量的函数
def get_messages_tokens(messages):
    """
    Get the tokens of messages.
    :param messages: The messages.
    :return: The tokens.
    """
    cnt = 0
    for message in messages:
        cnt += count_tokens(message["content"])
    return cnt

#count_tokens 函数有效地将字符串转化为 token 并返回数量
def count_tokens(strings):
    tokens = encoding.encode(strings)
    cnt = len(tokens)
    return cnt

#给定一个进程的 PID（pid），找到该进程及其所有子进程（包括子进程的子进程，递归查找）的 PID 列表。
def find_processes_created_by(pid):
    """
    Find the process's and all subprocesses' pid
    """
    parent_process = psutil.Process(pid)
    child_processes = parent_process.children(recursive=True)
    pids = [process.pid for process in child_processes]
    return pids.append(pid)

#作用是从给定的代码字符串中移除所有以 import 开头的语句
def remove_imports(code):
    # Define the regular expression pattern
    pattern = r"^import.*;$\n"

    # Use re.sub to remove lines matching the pattern
    output_str = re.sub(pattern, "", code, flags=re.MULTILINE)

    return output_str

#文件名如str(steps) + "_GPT_" + str(rounds) + ".json"
#默认返回str(steps)最大的   如file_number 是目录中 .json 文件的总数，因此这里 file_number = 4 函数会寻找以 4_ 开头的文件找到第一个匹配的  比如 4_GPT_2.json   获取的文件为GPT最新的修复文件

#指定 suffix="GPT" 且不指定 rounds    返回如果文件总数 file_number = 4，则 rounds = math.floor(4 / 3) = 1。函数寻找以 "GPT_1.json" 结尾的文件。 如匹配到的文件是：1_GPT_1.json 和 2_GPT_1.json  第一个匹配到的文件：1_GPT_1.json    会获取suffix="GPT"且按照规则算出轮数的文件
# 获取的文件为GPT最新一轮的文件且suffix="GPT"
#指定 suffix="GPT" 且指定 rounds=2   函数寻找以 "GPT_2.json" 结尾的文件 根据文件列表，匹配到的文件是：3_GPT_2.json 和 4_GPT_2.json   返回值： 第一个匹配到的文件：3_GPT_2.json     会获取suffix="GPT"且指定轮数的文件
def get_latest_file(file_dir, rounds=None, suffix=None):
    """
    Get the latest file
    :param file_dir:
    :return:
    """
    all_files = os.listdir(file_dir)
    file_number = len([x for x in all_files if x.endswith(".json")])
    if not suffix:
        for file in all_files:
            if file.startswith(str(file_number) + "_"):
                return os.path.join(file_dir, file)
    else:
        if not rounds:
            rounds = math.floor(file_number / 3)
        for file in all_files:
            if file.endswith(suffix + "_" + str(rounds) + ".json"):
                return os.path.join(file_dir, file)
    return ""

#的作用是根据方法的标识信息和处理方向，生成一个数据集文件的路径
def get_dataset_path(method_id, project_name, class_name, method_name, direction):
    """
    Get the dataset path
    :return:
    """
    if direction == "raw":
        return os.path.join(dataset_dir, "raw_data",
                            method_id + "%" + project_name + "%" + class_name + "%" + method_name + "%raw.json")
    return os.path.join(dataset_dir, "direction_" + str(direction),
                        method_id + "%" + project_name + "%" + class_name + "%" + method_name + "%d" + str(
                            direction) + ".json")

#根据方法的相关信息，从指定的原始数据文件中提取项目的包信息和导入信息。
def get_project_class_info(method_id, project_name, class_name, method_name):
    file_name = get_dataset_path(method_id, project_name, class_name, method_name, "raw")
    if os.path.exists(file_name):
        with open(file_name, "w") as f:
            raw_data = json.load(f)
        return raw_data["package"], raw_data["imports"]
    return None, None

# 函数的作用是解析特定格式的文件名，提取出其中的关键信息并返回
def parse_file_name(filename):
    m_id, project_name, class_name, method_name, direction_and_test_num = filename.split('%')
    direction, test_num = direction_and_test_num.split('_')
    return m_id, project_name, class_name, method_name, direction, test_num.split('.')[0]

# 函数用于解析给定目录路径的最后一级目录名称（即基目录），并从中提取出方法 ID、项目名、类名和方法名
def parse_file_name(directory):
    dir_name = os.path.basename(directory)
    m_id, project_name, class_name, method_name, invalid = dir_name.split('%')
    return m_id, project_name, class_name, method_name

#函数用于读取指定方法的原始数据文件（raw.json），并将其内容解析为 Python 数据结构。
def get_raw_data(method_id, project_name, class_name, method_name):
    with open(get_dataset_path(method_id, project_name, class_name, method_name, "raw"), "r") as f:
        raw_data = json.load(f)
    return raw_data

#函数用于返回项目目录的绝对路径
def get_project_abspath():
    return os.path.abspath(project_dir)

#函数用于删除指定路径下，以 test_ 为前缀的所有子目录
def remove_single_test_output_dirs(project_path):
    prefix = "test_"

    # Get a list of all directories in the current directory with the prefix
    directories = [d for d in os.listdir(project_path) if os.path.isdir(d) and d.startswith(prefix)]

    # Iterate through the directories and delete them if they are not empty
    for d in directories:
        try:
            shutil.rmtree(d)
            print(f"Directory {d} deleted successfully.")
        except Exception as e:
            print(f"Error deleting directory {d}: {e}")

#函数用于从给定的目录名称中提取日期字符串。该函数假定目录名称使用 %
# 字符进行分割，并返回分割后第二部分（即索引为 1 的部分）。
def get_date_string(directory_name):
    return directory_name.split('%')[1]

#函数用于查找项目中最新的结果目录。该函数假定目录名称包含 % 字符并且目录名称中的第二部分是日期。
def find_result_in_projects():
    """
    Find the new directory.
    :return: The new directory.
    """
    all_results = [x for x in os.listdir(project_dir) if '%' in x]
    all_results = sorted(all_results, key=get_date_string)
    return os.path.join(result_dir, all_results[-1])

#函数用于查找并返回 result_dir 目录下最新的目录。
# 该函数假设目录名称中包含日期信息，并通过日期对目录进行排序，返回最新的目录。
def find_newest_result():
    """
    Find the newest directory.
    :return: The new directory.
    """
    all_results = os.listdir(result_dir)
    all_results = sorted(all_results, key=get_date_string)
    return os.path.join(result_dir, all_results[-1])

#函数用于在 result_dir 目录中查找已完成的项目，并返回这些项目的名称。
# 函数通过查找以 scope_test 开头的子目录，然后解析每个子目录中的一个文件夹名称，从中提取出项目名称，最终返回所有项目名称的列表。
def get_finished_project():
    projects = []
    all_directory = os.listdir(result_dir)
    for directory in all_directory:
        if directory.startswith("scope_test"):
            sub_dir = os.path.join(result_dir, directory)
            child_dir = ""
            for dir in os.listdir(sub_dir):
                if os.path.isdir(os.path.join(sub_dir, dir)):
                    child_dir = dir
                    break
            m_id, project_name, class_name, method_name = parse_file_name(child_dir)
            if project_name not in projects:
                projects.append(project_name)
    return projects

#函数用于从一个 OpenAI API 的响应字典中提取出具体的文本内容。
# 假设响应的格式为 OpenAI GPT API 的标准返回格式，该函数会从中提取出 choices 中的第一个元素，并进一步提取 message 中的 content 字段内容。
def get_openai_content(content):
    """
    Get the content for OpenAI
    :param content:
    :return:
    """
    if not isinstance(content, dict):
        return ""
    return content["choices"][0]['message']["content"]

#函数用于从 OpenAI API 的响应字典中提取出 message 字段，而不仅仅是其中的 content。
# 该函数返回包含 message 的整个字典，而不是只提取文本内容。
def get_openai_message(content):
    """
    Get the content for OpenAI
    :param content:
    :return:
    """
    if not isinstance(content, dict):
        return ""
    return content["choices"][0]['message']

# #获取Java版本 17或11  有bug原版
# def check_java_version():
#     java_home = os.environ.get('JAVA_HOME')
#     if 'jdk-17' in java_home:
#         return 17
#     elif 'jdk-11' in java_home:
#         return 11
def check_java_version():
    # First, check JAVA_HOME
    java_home = os.environ.get('JAVA_HOME')
    if not java_home:
        raise Exception("JAVA_HOME is not set. Please set JAVA_HOME to the correct path.")

    # Verify the path in JAVA_HOME contains 'java-11' or 'java-17'
    if "java-11" in java_home:
        return 11
    elif "java-17" in java_home:
        return 17

    # If JAVA_HOME path is ambiguous, fallback to java command
    try:
        result = subprocess.run(["java", "-version"], stderr=subprocess.PIPE, text=True)
        version_output = result.stderr
        if "11" in version_output:
            return 11
        elif "17" in version_output:
            return 17
        else:
            raise Exception("Unsupported Java version detected.")
    except Exception as e:
        raise Exception(f"Error checking Java version: {e}")

#函数用于修复 Java 代码中的 package 声明，确保它包含正确的包名。
def repair_package(code, package_info):
    """
    Repair package declaration in test.
    """
    first_line = code.split('import')[0]
    if package_info == '' or package_info in first_line:
        return code
    code = package_info + "\n" + code
    return code

#函数用于修复 Java 代码中的 import 语句，确保代码中包含所需的导入语句，并且它们的顺序与 imports 参数一致。
# TODO: imports can be optimized
def repair_imports(code, imports):
    """
    Repair imports in test.
    """
    import_list = imports.split('\n')
    first_line, _code = code.split('\n', 1)
    for _import in reversed(import_list):
        if _import not in code:
            _code = _import + "\n" + _code
    return first_line + '\n' + _code

#函数用于给 JUnit 测试用例添加超时设置。
# 它能够检测 JUnit 版本并根据不同的版本格式将超时设置应用于测试用例。
def add_timeout(test_case, timeout=8000):
    """
    Add timeout to test cases. Only for Junit 5
    """
    # check junit version
    junit4 = 'import org.junit.Test'
    junit5 = 'import org.junit.jupiter.api.Test'
    if junit4 in test_case:  # Junit 4
        test_case = test_case.replace('@Test(', f'@Test(timeout = {timeout}, ')
        return test_case.replace('@Test\n', f'@Test(timeout = {timeout})\n')
    elif junit5 in test_case:  # Junit 5
        timeout_import = 'import org.junit.jupiter.api.Timeout;'
        test_case = repair_imports(test_case, timeout_import)
        return test_case.replace('@Test\n', f'@Test\n    @Timeout({timeout})\n')
    else:
        print("Can not know which junit version!")
        return test_case

#函数用于将生成的测试用例（method_test_case）导出到指定路径的文件中。
# 它会根据提供的路径、类名、方法ID和测试编号生成文件名，并将测试用例保存为 .java 文件。
# 测试用例的超时设置会通过调用 add_timeout 函数来添加。
def export_method_test_case(output, class_name, m_id, test_num, method_test_case):
    """
    Export test case to file.
    output : pathto/project/testcase.java
    """
    method_test_case = add_timeout(method_test_case)
    f = os.path.join(output, class_name + "_" + str(m_id) + '_' + str(test_num) + "Test.java")
    if not os.path.exists(output):
        os.makedirs(output)
    with open(f, "w") as output_file:
        output_file.write(method_test_case)

#函数用于根据给定的 m_id 和 test_num 修改测试用例中的类名。函数会将原来的类名（通常是 class_name + 'Test'）
# 替换为新生成的类名（class_name + '_' + m_id + '_' + test_num + 'Test'）。
def change_class_name(test_case, class_name, m_id, test_num):
    """
    Change the class name in the test_case by given m_id.
    """
    old_name = class_name + 'Test'
    new_name = class_name + '_' + str(m_id) + '_' + str(test_num) + 'Test'
    return test_case.replace(old_name, new_name, 1)

#函数用于获取当前系统时间，并将其格式化为时分秒的形式。
def get_current_time():
    """
    Get current time
    :return:
    """
    current_time = datetime.datetime.now()
    formatted_time = current_time.strftime("%H:%M:%S")
    return formatted_time
