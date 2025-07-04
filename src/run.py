import os.path
import time
from tools import *
from database import *
from parse_data import parse_data
from export_data import export_data
from scope_test import start_generation
from parse_xml import result_analysis
from task import Task


# 函数用于清空存储数据集的文件夹。该函数会检查指定的 dataset_dir 数据集目录
# 文件夹是否存在，如果存在，则使用 shutil.rmtree 删除该文件夹及其所有内容。
def clear_dataset():
    """
    Clear the dataset folder.
    :return: None
    """
    # Delete the dataset folder
    if os.path.exists(dataset_dir):
        shutil.rmtree(dataset_dir)

#通过一键式操作生成测试用例并进行分析
# 删除历史数据：
#
# 调用 drop_table() 函数，删除数据库中的历史数据，为新的操作清空数据表。
# 创建新表：
#
# 调用 create_table() 函数，重新创建需要的数据库表，准备好新的数据存储结构。
# 解析项目数据：
#
# Task.parse(project_dir) 解析项目目录，返回包含项目信息的路径。
# 解析数据：
#
# 使用 parse_data(info_path) 将解析后的数据进一步处理，并存入数据库。
# 清理最后的数据集：
#
# 调用 clear_dataset() 函数删除之前的数据集文件夹，确保新的数据集是干净的。
# 导出数据以支持多进程处理：
#
# 调用 export_data() 函数，准备好数据以供多进程处理。
# 获取项目名：
#
# 使用 os.path.basename(os.path.normpath(project_dir)) 从项目目录路径中提取项目名称。
# 修改SQL查询：
#
# 通过动态 SQL 查询，获取该项目下所有方法的 ID，作为生成测试用例的基础。
# 开始生成过程：
#
# 调用 start_generation()，根据 SQL 查询结果开始生成测试用例的过程，并传入相关参数（例如：multiprocess=False 表示不使用多进程，repair=True 表示启用修复，confirmed=False 表示未确认）。
# 分析结果：
#
# 调用 result_analysis() 对生成的测试结果进行分析，提供详细的统计信息。
def run():
    """
    Generate the test cases with one-click.
    :return: None
    """
    # Delete history data
    drop_table()


    # Create the table
    create_table()


    #解析目标项目并提取其类信息  解析project_dir并返回output_path
    #self.output = "../class_info/"       ../ 当前目录的上一级目录
    # Parse project
    info_path = Task.parse(project_dir)


    ##函数的作用是解析 "../class_info/"中的.json 文件中解析数据，并将其插入到数据库中。
    # 它会遍历指定目录中的所有 .json 文件，读取并解析文件内容，提取其中的类和方法数据，并将这些数据插入到数据库的 class 和 method 表中。
    # Parse data
    parse_data(info_path)


    #函数用于清空存储数据集的文件夹。该函数会检查指定的 dataset_dir 数据集目录
    #包括  direction_1 contains the context without dependencies.
         # direction_3 contains the context with dependencies.
         # raw_data contains all the information about focal methods.
    # clear last dataset
    clear_dataset()


    # 该函数将数据库中的方法数据导出为多个 JSON 文件，分别保存为：
    # 方向1 (direction_1)：包含类的元信息、字段、方法源代码等。
    # 方向3 (direction_3)：包含方法的依赖信息，方法的上下文和相关类的构造器信息。
    # 原始数据 (raw_data)：方法的详细信息，如签名、参数、源代码等。
    # Export data for multi-process
    export_data()

    #这行代码的作用是从路径 project_dir 中提取出最后的目录名称，作为项目的名称
    project_name = os.path.basename(os.path.normpath(project_dir))

    #在数据里查找这个项目所有的焦点方法
    # Modify SQL query to test the designated classes.
    sql_query = """
        SELECT id FROM method WHERE project_name='{}';
    """.format(project_name)

    # 解析项目名称 函数通过正则表达式从 SQL 查询中提取出项目名称。
    # 包括项目名称提取、删除旧的测试结果、获取方法 ID、确认测试启动、创建新的结果文件夹、记录信息、执行测试、以及最后保存和输出测试结果。
    # 其中result_path：结果存放路径。    如../result/scope_test%2020241117222232%focal
    # 更加详细信息点击函数进去
    # Start the whole process
    start_generation(sql_query, multiprocess=False, repair=True, confirmed=False)

    # 遍历 result_path 下的所有文件夹。
    # 查找名为 coverage.xml 的文件，将其路径传递给 xml_to_json 函数，将 XML 格式的覆盖率文件转换为 JSON 格式。
    # 分析后的结果是主要通过 print 打印到控制台
    # Export the result
    result_analysis()

#倒计时提示方式适用于在执行关键任务（如数据处理、配置文件修改等）之前，确保用户已经完成了所有必需的操作。
if __name__ == '__main__':
    print("Make sure the config.ini is correctly configured.")
    seconds = 5
    while seconds > 0:
        print(seconds)
        time.sleep(1)  # Pause for 1 second
        seconds -= 1
    run()
