import subprocess
import signal
import time
import concurrent.futures
from test_runner import TestRunner
from class_parser import ClassParser
from tools import *
from config import *
from colorama import Fore, init


class Task:

    #用于运行测试任务
    @staticmethod
    def test(test_path, target_path):
        """
        Run test task, make sure the target project has be compiled and installed.(run `mvn compile install`)
        """
        #print("test")
        test_task = TestTask(test_path, target_path)
        #print("test_task")
        return test_task.single_test()

    #执行所有的测试任务
    @staticmethod
    def all_test(test_path, target_path):
        """
        Run test task, make sure the target project has be compiled and installed.(run `mvn compile install`)
        """
        test_task = TestTask(test_path, target_path)
        return test_task.all_test()

    #解析目标项目并提取其类信息
    #process_d4j_revisions 用于处理 defects4j 项目的修订版本并提取焦点类。
    #find_classes 用于解析普通 Java 项目，找到所有的类（排除测试类），并将其相关信息存储到指定的输出目录。
    #返回都为  output_path，即保存解析结果的目录路径
    @staticmethod
    def parse(target_path):
        """
        Run parse task, extract class information of target project.
        """
        parse_task = ParseTask()
        return parse_task.parse_project(target_path)


class TestTask:

    #初始化测试路径、目标路径、测试运行器，并设定 CPU 和内存的资源阈值。这些功能和设置将确保后续测试的顺利进行，并避免系统资源过度使用。
    def __init__(self, test_path, target_path):
        init()  # colorama init
        self.test_path = test_path
        self.target_path = target_path
        self.runner = TestRunner(test_path, target_path)

        # define the threshold for CPU utilization and available memory
        self.cpu_threshold = 80
        self.mem_threshold = 1024 * 1024 * 5000  # 5G

    #方法在执行测试之前会检查 Java 版本，确保项目是 Defects4J 项目还是普通项目，然后调用相应的方法执行测试。
    # 该方法通过判断项目路径的后缀来确定项目类型，并分别处理不同类型的测试任务。
    def single_test(self):
        """
        Only run tests.
        tests directory path, e.g., /data/share/TestGPT_ASE/result/scope_test%20230414210243%d3_1/1460%lang_1_f%ToStringBuilder%append%d3/5
        """
        if check_java_version() != 11:
            raise Exception(Fore.RED + "Wrong java version! Need: java 11")
        if self.target_path.endswith("_f") or self.target_path.endswith("_b"):  # defects4j project
            #print("defects4j project")
            return self.start_d4j()
        else:  # general project
            #print("general project")
            return self.runner.start_single_test()

    #all_test 方法用于执行所有的测试用例。它首先检查 Java 版本是否为 11，
    # 然后通过调用 runner.start_all_test() 来执行所有的测试任务
    def all_test(self):
        """
        Run all test cases.
        test_path: test cases directory path, e.g., /data/share/TestGPT_ASE/result/scope_test%20230414210243%d3_1/
        target_path: target project path
        """
        if check_java_version() != 11:
            raise Exception(Fore.RED + "Wrong java version! Need: java 11")
        return self.runner.start_all_test()

    #start_d4j 方法的主要功能是检查系统的 CPU 和内存使用情况，并在资源条件合适时启动 Defects4J 测试任务。
    def start_d4j(self):
        """
        Adaptive assignment for d4j tests.
        test case path: /root/TestGPT_ASE/result_429/scope_test%20230428134414%/4950%Chart_8_f%Week%getYear%d1/1/temp
        """
        # loop until the CPU utilization falls below the threshold
        while True:
            # get the current CPU utilization
            cpu_utilization = psutil.cpu_percent()
            mem_available = psutil.virtual_memory().available
            # if the CPU utilization is below the threshold, start a new process and break the loop
            if cpu_utilization < self.cpu_threshold and mem_available > self.mem_threshold:
                self.run_d4j()
                break
            # if the CPU utilization is still above the threshold, wait for some time (e.g. 1 second) and check again
            time.sleep(2)
    #启动一个子进程执行 Defects4J 测试脚本。
    # 监控进程状态，并处理测试过程中的异常（如编译错误）。
    # 超过设定超时时间后，终止进程并避免系统资源被过度占用。
    def run_d4j(self):
        """
        Run single test using defects4j test api
        test case path: /root/TestGPT_ASE/result_429/scope_test%20230428134414%/4950%Chart_8_f%Week%getYear%d1/1/temp
        """
        d4j_script = 'scripts/d4j_test.sh'
        test_case_src = os.path.join(self.test_path, "temp")

        process = subprocess.Popen(["bash", d4j_script, test_case_src, self.target_path], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        start_time = time.monotonic()
        while True:
            exit_code = process.poll()
            if exit_code is not None:
                if exit_code != 0:
                    with open(os.path.join(test_case_src, 'compile_error.txt'), "w") as f:
                        pattern = r"compile\.gen\.tests:(.*?)BUILD FAILED"
                        match = re.search(pattern, stderr.decode(), re.DOTALL)
                        if match:
                            compile_output = match.group(1).strip().split('[javac] ', 1)[1]
                            compile_output = compile_output.replace('    [javac] ', '')
                            f.write(compile_output)
                        else:
                            f.write(stderr.decode())
                break
            elif time.monotonic() - start_time >= TIMEOUT:
                sub_pids = find_processes_created_by(process.pid)
                for pid in sub_pids:
                    os.kill(pid, signal.SIGTERM)
                break
            else:
                time.sleep(0.1)

    #用于在 Defects4J 的有缺陷版本（buggy revisions）上运行测试。
    def run_d4j_b(self, tests_src, threaded=True):
        """
        run tests at defects4j buggy revisions
        :param tests_src: result directory, e.g., /root/TestGPT_ASE/result/
        """
        target_path = '/root/TestGPT_ASE/projects'
        if threaded:
            with concurrent.futures.ProcessPoolExecutor(max_workers=process_number) as executor:
                for scope_tests in os.listdir(tests_src):
                    scope_tests_path = os.path.join(tests_src, scope_tests)
                    for tests_dir in os.listdir(scope_tests_path):
                        tests_path = os.path.join(scope_tests_path, tests_dir)
                        m_id, project_name, class_name, method_name = parse_file_name(tests_path)
                        project_path = os.path.join(target_path, project_name.replace('_f', '_b'))
                        self.target_path = project_path
                        for i in range(1, test_number + 1):
                            if not os.path.exists(os.path.join(tests_path, str(i))):
                                continue
                            print("Processing project:", project_name, "method id:", m_id, "test number:", str(i))
                            test_case_src = os.path.join(tests_path, str(i), 'temp')
                            self.test_path = test_case_src
                            executor.submit(self.run_d4j)
        else:
            for scope_tests in os.listdir(tests_src):
                scope_tests_path = os.path.join(tests_src, scope_tests)
                for tests_dir in os.listdir(scope_tests_path):
                    tests_path = os.path.join(scope_tests_path, tests_dir)
                    m_id, project_name, class_name, method_name = parse_file_name(tests_path)
                    project_path = os.path.join(target_path, project_name.replace('_f', '_b'))
                    self.target_path = project_path
                    for i in range(1, test_number + 1):
                        if not os.path.exists(os.path.join(tests_path, str(i))):
                            continue
                        print("Processing project:", project_name, "method id:", m_id, "test number:", str(i))
                        test_case_src = os.path.join(tests_path, str(i), 'temp')
                        self.test_path = test_case_src
                        self.run_d4j()


class ParseTask:
    # 1.初始化parser
    # 2.设置输出路径
    def __init__(self):
        self.parser = ClassParser(GRAMMAR_FILE, LANGUAGE)
        self.output = "../class_info/"

    #用于解析一个项目并提取相关类信息
    #Defects4J 项目：提取指定的修订版本及其焦点类。
    #普通项目：遍历项目目录，查找和提取所有类信息。
    def parse_project(self, target_path):
        """
        Analyze a single project
        """
        # Create folders
        target_path = target_path.rstrip('/')
        os.makedirs(self.output, exist_ok=True)
        if target_path.endswith("_f") or target_path.endswith("_b"):
            _, output_path = self.process_d4j_revisions(target_path, './scripts/focal_classes.json')
            return output_path
        tot_m, output_path = self.find_classes(target_path)
        return output_path

    #解析指定路径下的 Java 项目，找到所有类（排除测试类），并将相关信息存储到输出目录中。
    def find_classes(self, target_path):
        """
        Find all classes exclude tests
        Finds test cases using @Test annotation
        """
        # Run analysis
        print("Parse", target_path, " ...")
        if not os.path.exists(target_path):
            return 0, ""
        # Test Classes
        try:
            result = subprocess.check_output(r'grep -l -r @Test --include \*.java {}'.format(target_path), shell=True)
            tests = result.decode('ascii').splitlines()
        except:
            tests = []
        # Java Files
        try:
            result = subprocess.check_output(['find', target_path, '-name', '*.java'])
            java = result.decode('ascii').splitlines()
        except:
            return 0, ""
        # All Classes exclude tests
        focals = list(set(java) - set(tests))
        focals = [f for f in focals if not "src/test" in f]
        project_name = os.path.split(target_path)[1]
        output = os.path.join(self.output, project_name)
        os.makedirs(output, exist_ok=True)
        return self.parse_all_classes(focals, project_name, output), output

    #要功能是对指定的类文件进行解析，并将解析结果以 JSON 格式保存到指定的输出目录中。
    def parse_all_classes(self, focals, project_name, output):
        classes = {}
        for focal in focals:
            parsed_classes = self.parser.parse_file(focal)
            for _class in parsed_classes:
                _class["project_name"] = project_name

            classes[focal] = parsed_classes
            json_path = os.path.join(output, os.path.split(focal)[1] + ".json")
            self.export_result(classes[focal], json_path)
        return classes

    # 方法的功能是将数据导出为 JSON 文件，并确保输出路径的目录结构存在。
    @staticmethod
    def export_result(data, out):
        """
        Exports data as json file
        """
        directory = os.path.dirname(out)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(out, "w") as text_file:
            data_json = json.dumps(data)
            text_file.write(data_json)

    #从指定目录及其子目录中查找文件路径的函数。通过遍历目录结构，当找到指定文件时，返回其完整路径。
    def get_class_path(self, start_path, filename):
        for root, dirs, files in os.walk(start_path):
            if filename in files:
                return os.path.join(root, filename)

    #用于分析 defects4j 的指定项目版本，并提取目标类（焦点类，focal classes）的信息。
    def process_d4j_revisions(self, repo_path, focal_classes_json):
        """
        Analysis defects4j revisions focal method.
        """
        if '_f' not in os.path.basename(repo_path):
            return
        # Run analysis
        print("Parsing focal class...")
        project_name = os.path.split(repo_path)[1]
        with open(focal_classes_json, 'r') as f:
            content = json.load(f)
        for repo in content:
            if repo['project'] == project_name:
                classes = repo['classes']
        focals = []
        for _class in classes:
            class_path = self.get_class_path(repo_path, os.path.basename(_class.rstrip('\n').replace('.', '/') + '.java'))
            focals.append(class_path)

        output = os.path.join(self.output, project_name)
        return self.parse_all_classes(focals, project_name, output), output
