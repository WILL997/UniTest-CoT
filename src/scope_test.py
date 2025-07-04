"""
This file is for starting a scope test for selected methods.
It will automatically create a new folder inside dataset as well as result folder.
The folder format is "scope_test_YYYYMMDDHHMMSS_Direction".
The dataset folder will contain all the information in the direction.
"""
from tools import *
from askGPT import start_whole_process
from database import database
from task import Task
from colorama import Fore, Style, init

# init() 函数的作用是执行程序启动时所需的初始化操作，如设置环境变量、加载配置等。
# db = database() 创建一个 database 类的实例 db，用于执行与数据库相关的操作。
init()
db = database()

#函数通过时间戳和测试方向创建唯一的文件夹路径，确保每次测试都在不同的文件夹中存储结果，并避免重复创建文件夹。
def create_dataset_result_folder(direction):
    """
    Create a new folder for this scope test.
    :param direction: The direction of this scope test.
    :return: The path of the new folder.
    """
    # Get current time
    now = datetime.datetime.now()
    # format the time as a string
    time_str = now.strftime("%Y%m%d%H%M%S")
    result_path = os.path.join(result_dir, "scope_test%" + time_str + "%" + direction)
    if not os.path.exists(result_path):
        os.makedirs(result_path)
    else:
        raise Exception("Result folder already exists.")
    return result_path

#函数用于创建一个新的文件夹，如果文件夹路径已存在，则抛出异常
def create_new_folder(folder_path: str):
    """
    Create a new folder.
    :param folder_path: The folder path.
    :return: None
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    else:
        raise Exception("Folder already exists.")

#函数遍历指定文件夹，查找文件名中包含指定 method_ids 前缀的文件，并将其返回为列表。
# 该函数非常适用于根据文件名中嵌入的标识符过滤文件，并支持递归查找子目录中的文件。
def find_all_files(folder_path: str, method_ids: list = None):
    """
    Find all the files in the folder.
    :param method_ids: The method ids need to be found.
    :param folder_path: The folder path.
    :return: The file list.
    """
    file_list = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.split("%")[0] not in method_ids:
                continue
            file_list.append(file)
    return file_list

#解析项目名称 函数通过正则表达式从 SQL 查询中提取出项目名称。
#方法启动了整个 "scope test" 测试流程，涉及到多个步骤，
# 包括项目名称提取、删除旧的测试结果、获取方法 ID、确认测试启动、创建新的结果文件夹、记录信息、执行测试、以及最后保存和输出测试结果。
def start_generation(sql_query, multiprocess=True, repair=True, confirmed=False):
    """
    Start the scope test.
    :param multiprocess: if it needs to
    :param repair:
    :param sql_query:
    :return:
    """
    match = re.search(r"project_name\s*=\s*'([\w-]*)'", sql_query)
    if match:
        project_name = match.group(1)
        print(project_name)
    else:
        raise RuntimeError("One project at one time.")
    # delete the old result
    #获取项目project_name的绝对路径
    #会删除project_name的绝对路径下所有以 "test_" 为前缀的所有子目录
    remove_single_test_output_dirs(get_project_abspath())

    #查询数据库获取该项目下所有方法的ids
    method_ids = [x[0] for x in db.select(script=sql_query)]
    if not method_ids:
        raise Exception("Method ids cannot be None.")

    #检查 method_ids 列表中的第一个元素是否是字符串类型。如果不是字符串类型（可能是整数等），则会将所有的ID转换为字符串。
    if not isinstance(method_ids[0], str):
        method_ids = [str(i) for i in method_ids]
    #提示用户即将启动整个范围测试（scope test）
    print("You are about to start the whole process of scope test.")
    #输出将要处理的该项目下所有方法数量
    print("The number of methods is ", len(method_ids), ".")
    #估算测试的总成本，这里通过 len(method_ids) * 0.0184 * test_number 计算。
    # test_number 是每个方法测试的数量，0.0184 可能是每个方法的测试费用（单位是美元）。
    print("The approximate cost will be", Fore.RED + "$", len(method_ids) * 0.0184 * test_number, ".", Style.RESET_ALL)
    #记录的字符串变量 record，初始内容为 "This is a record of a scope test.\n"。
    record = "This is a record of a scope test.\n"
    #如果 confirmed 变量为 False（即用户没有事先确认），则系统会通过 input 函数询问用户是否确认启动测试。
    if not confirmed:
        confirm = input("Are you sure to start the scope test? (y/n): ")
        if confirm != "y":
            print("Scope test cancelled.")
            return

    # Create the new folder
    #result_dir/scope_test%时间戳%方向
    # result_dir = "../result/" 且 direction = "focal", 则result_path文件夹路径会是 ../result/scope_test%2020241117222232%focal
    #direction = "focal" 表示当前测试是针对焦点类的测试，通常是项目中最重要的类或方法。
    result_path = create_dataset_result_folder("")

    record += "Result path: " + result_path + "\n"
    record += 'SQL script: "' + sql_query + '"\n'
    record += "Included methods: " + str(method_ids) + "\n"

    #在result_path文件夹下的../result/scope_test%2020241117222232%focal目录下创建record.txt文件
    #record.txt 中的内容 为 结果路径 SQL 查询脚本 所有包含的测试方法 ID
    record_path = os.path.join(result_path, "record.txt")
    with open(record_path, "w") as f:
        f.write(record)
    #控制台会输出一条消息，表示 record.txt 文件已经保存，并显示文件所在的路径
    print(Fore.GREEN + "The record has been saved at", record_path, Style.RESET_ALL)

    #dataset_dir = ../dataset/
    #source_dir 设置为 dataset_dir 目录下的 direction_1 子目录路径。
    # 这意味着 dataset_dir 指向的数据集目录中有一个子目录 direction_1，并且这个子目录包含了测试所需的文件。
    source_dir = os.path.join(dataset_dir, "direction_1")

    #source_dir：从 dataset_dir 指定的目录加载数据。 如../dataset/direction_1
    # result_path：结果存放路径。    如../result/scope_test%2020241117222232%focal
    # multiprocess 和 repair：用于控制是否启用多进程处理和是否进行修复。
    # 该函数启动整个处理过程，并在完成后打印 "WHOLE PROCESS FINISHED"，表示该部分处理已结束。
    # 调用gpt产生测试用例的生成过程
    start_whole_process(source_dir, result_path, multiprocess=multiprocess, repair=repair)
    print("WHOLE PROCESS FINISHED")
    # Run accumulated tests
    #获取project_dir的绝对路径
    project_path = os.path.abspath(project_dir)
    print("START ALL TESTS")

    #Task.all_test 方法将会根据 项目路径 结果路径  执行与测试相关的任务  默认使用Java11版本
    Task.all_test(result_path, project_path)
    try:
        with open(record_path, "a") as f:
            #find_result_in_projects函数用于查找项目中最新的结果目录。该函数假定目录名称包含 % 字符并且目录名称中的第二部分是日期。
            f.write("Whole test result at: " + find_result_in_projects() + "\n")
    except Exception as e:
        print("Cannot save whole test result.")
        print(e)

    print("SCOPE TEST FINISHED")

# 从数据库中查询符合条件的方法 ID。
# 创建新的结果文件夹。
# 执行范围测试并保存相关的测试结果。
# 执行所有测试并生成最终结果。
if __name__ == '__main__':
    sql_query = "SELECT id FROM method WHERE project_name='Lang_1_f' AND class_name='NumberUtils' AND is_constructor=0;"
    start_generation(sql_query, multiprocess=True, repair=True, confirmed=False)
