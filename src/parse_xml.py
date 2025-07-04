from tools import *
from bs4 import BeautifulSoup

#用于将覆盖率数据从 XML 格式转换为 JSON 格式。它通过解析 XML 文件，提取覆盖率相关信息，然后将这些数据保存为一个 JSON 文件。
def xml_to_json(result_path):
    """

    :param result_path:
    :return:
    """
    output_path = os.path.abspath(result_path[:-4] + ".json")
    if os.path.exists(output_path):  # if the file already exists
        return
    src_path = os.path.abspath(result_path)
    with open(src_path, "r") as f:
        soup = BeautifulSoup(f, "xml")
    result = {"line-rate": soup.find("coverage").attrs["line-rate"],
              "branch-rate": soup.find("coverage").attrs["branch-rate"],
              "lines-covered": soup.find("coverage").attrs["lines-covered"],
              "branches-covered": soup.find("coverage").attrs["branches-covered"],
              "branches-valid": soup.find("coverage").attrs["branches-valid"],
              "complexity": soup.find("coverage").attrs["complexity"]}
    with open(output_path, "w") as f:
        json.dump(result, f)

#用于处理并分析覆盖率数据，特别是关于 numberutils 类的覆盖率。
# 它从指定路径或默认路径读取相关数据，查找每个方法的覆盖率，并将最终结果保存为一个 JSON 文件。
def get_numberutils_result(result_path=None):
    """

    :param result_path:
    :return:
    """
    if result_path is None:
        result_path = find_newest_result()
    final_result = {}
    for name in os.listdir(result_path):
        file_path = os.path.join(result_path, name)
        if os.path.isdir(file_path):
            m_id, project_name, class_name, method_name = parse_file_name(name)
            raw_data = get_raw_data(m_id, project_name, class_name, method_name)
            parameters = raw_data["parameters"]
            for i in range(1, test_number + 1):
                runtemp_path = os.path.join(file_path, str(i), "runtemp")
                if os.path.exists(runtemp_path):
                    shutil.rmtree(runtemp_path)
                coverage_path = os.path.join(file_path, str(i), "temp", "coverage.json")
                if os.path.exists(coverage_path):
                    with open(coverage_path, "r") as f:
                        coverage = json.load(f)
                    if parameters not in final_result:
                        final_result[parameters] = {"line-covered": 0,
                                                    "coverage_path": ""}
                    covered = eval(coverage["lines-covered"])
                    if covered > final_result[parameters]["line-covered"]:
                        final_result[parameters] = {"line-covered": covered,
                                                    "coverage_path": coverage_path}
    # print(final_result)
    compare_list = ["toInt(String, int)", "toLong(String, long)", "toFloat(String, float)", "toDouble(String, double)",
                    "toByte(String, byte)", "toShort(String, short)", "createFloat(String)", "createDouble(String)",
                    "createInteger(String)", "createLong(String)", "createBigInteger(String)",
                    "createBigDecimal(String)", "min(long[])", "min(int, int, int)", "max(float[])",
                    "max(byte, byte, byte)", "isDigits(String)", "isNumber(String)"]
    for key in compare_list:
        print(key, final_result[key]["line-covered"])
        # print(key, final_result[key]["line-covered"], final_result[key]["coverage_path"])
    with open(os.path.join(result_path, "numberutils_result.json"), "w") as f:
        json.dump(final_result, f)


# 函数用于分析存储在指定目录中的项目结果，生成一系列与项目测试运行和覆盖率相关的统计信息。
# 它处理 XML 覆盖文件，计算各种结果，如成功与失败，并根据尝试次数跟踪修复的成功率。
#寻找名为 coverage.xml 的 XML 文件。 将 XML 格式的数据转换为 JSON 格式。
def result_analysis(result_path=None):
    #如果未提供 result_path，调用 find_newest_result() 获取最新结果路径。
    # result_path：结果存放路径。    如../result/scope_test%2020241117222232%focal
    if not result_path:
        result_path = find_newest_result()
    if not os.path.exists(result_path):
        raise RuntimeError("Result Path not found!")
    print("\n" + result_path)
    # Parse result to json
    #遍历 result_path 下的所有文件夹。
    #查找名为 coverage.xml 的文件，将其路径传递给 xml_to_json 函数，将 XML 格式的覆盖率文件转换为 JSON 格式。
    for directory_path, directory_names, file_names in os.walk(result_path):
        for file_name in file_names:
            if file_name == 'coverage.xml':  # check if the file name is 'coverage.xml'
                file_path = os.path.join(directory_path, file_name)
                xml_to_json(file_path)

    # 文件总数：all_files_cnt
    # Java 文件总数：all_java_files_cnt
    # 成功计数：success_cnt 和 success_cnt_json
    # 失败计数：fail_cnt
    # 运行临时目录计数：runtemp_cnt
    # 修复成功和失败计数：repair_success_cnt 和 repair_failed_cnt
    # 修复轮次统计：repair_rounds，记录不同轮次的修复成功次数。
    all_files_cnt = 0
    all_java_files_cnt = 0
    success_cnt = 0
    success_cnt_json = 0
    fail_cnt = 0
    runtemp_cnt = 0
    repair_success_cnt = 0
    repair_failed_cnt = 0
    project_name = ""
    repair_rounds = {i: 0 for i in range(2, max_rounds + 1)}

    # 遍历 result_path 下的所有子目录。
    # 如果项目名称未设置，通过 parse_file_name 提取项目名称。
    # 累计子目录内文件的数量到 all_files_cnt。
    for name in os.listdir(result_path):
        directory_name = os.path.join(result_path, name)
        if os.path.isdir(directory_name):
            if not project_name:
                project_name = parse_file_name(directory_name)[1]
            all_files_cnt += len(os.listdir(directory_name))
            #遍历测试编号目录。
            # 检查是否存在 runtemp/ 子目录（运行时临时文件夹），如果存在：
            # 增加 runtemp_cnt 计数。
            # 删除该文件夹，清理临时数据。
            for i in range(1, test_number + 1):
                sub_dir = os.path.join(directory_name, str(i))
                if os.path.exists(sub_dir):
                    runtemp_path = os.path.abspath(os.path.join(sub_dir, "runtemp/"))
                    if os.path.exists(runtemp_path):
                        runtemp_cnt += 1
                        shutil.rmtree(runtemp_path)

                    #检查 temp/ 目录是否存在：
                    #如果存在 .java 文件，增加 all_java_files_cnt 计数。
                    temp_dir = os.path.join(sub_dir, "temp")
                    coverage_path = os.path.join(temp_dir, "coverage.xml")
                    if os.path.exists(temp_dir):
                        for file_name in os.listdir(temp_dir):
                            if file_name.endswith(".java"):
                                all_java_files_cnt += 1
                                break
                    #如果 coverage.json 文件存在，增加成功 JSON 计数 success_cnt_json
                    coverage_json = os.path.join(temp_dir, "coverage.json")
                    if os.path.exists(coverage_json):
                        success_cnt_json += 1

                    #检查 coverage.xml 文件是否存在：
                    # 如果存在，增加成功计数 success_cnt。
                    # 如果尝试修复超过 3 次，记录修复成功次数 repair_success_cnt 并更新修复轮次 repair_rounds。
                    # 如果不存在 coverage.xml，统计失败次数 fail_cnt 和修复失败次数 repair_failed_cnt。
                    json_file_number = len(os.listdir(sub_dir)) - 1
                    if os.path.exists(coverage_path):
                        success_cnt += 1
                        if json_file_number > 3:
                            repair_success_cnt += 1
                            repair_rounds[math.ceil(json_file_number / 3)] += 1
                    else:
                        fail_cnt += 1
                        if json_file_number > 3:
                            repair_failed_cnt += 1
    #输出信息 项目名称。 各类文件计数。测试成功与失败统计。修复成功与失败统计。修复轮次的统计。被清理的运行时临时目录计数。
    print("Project name:        " + str(project_name))
    print("All files:           " + str(all_files_cnt))
    print("All java files:      " + str(all_java_files_cnt))
    print("Success:             " + str(success_cnt))
    print("Success json:        " + str(success_cnt_json))
    print("Fail:                " + str(fail_cnt))
    print("Repair success:      " + str(repair_success_cnt))
    print("Repair failed:       " + str(repair_failed_cnt))
    print("Repair rounds:       " + str(repair_rounds))
    print("runtemp counts:      " + str(runtemp_cnt))
    print()

#full_analysis 函数用于对指定目录下的所有子目录进行全面分析
# 特别是针对以 scope_test 开头的子目录，它会调用 result_analysis 函数来分析每个符合条件的目录。
# 分析后的结果是主要通过 print 打印到控制台
def full_analysis(directory=result_dir):
    for root, dirs, files in os.walk(directory):
        for dir_name in dirs:
            if dir_name.startswith("scope_test"):
                result_analysis(os.path.join(root, dir_name))


if __name__ == '__main__':
    # result_analysis()
    full_analysis("")
    # get_numberutils_result()
