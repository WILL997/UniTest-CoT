import copy
import os.path
import time
import openai
from tools import *
import random
import concurrent.futures
import javalang
import jinja2
from colorama import Fore, Style, init
from task import Task
import platform
init()
# Create a jinja2 environment
env = jinja2.Environment(loader=jinja2.FileSystemLoader('../prompt'))



#替换成代理的url  使用国内代理ChatGPT需要配置
def set_environment_variable():
    """
    Automatically set the environment variable OPENAI_API_BASE
    and ensure immediate effect for the script.
    """
    api_base_url = "https://api.chatanywhere.tech/v1"
    system_type = platform.system()
    print(f"Detected system: {system_type}")

    if system_type == "Windows":
        os.system(f'setx OPENAI_API_BASE "{api_base_url}"')
        print("Environment variable set for Windows. Please restart your system if needed.")
    elif system_type in ["Linux", "Darwin"]:
        shell_config = os.path.expanduser("~/.bashrc") if system_type == "Linux" else os.path.expanduser("~/.zshrc")
        try:
            with open(shell_config, "a") as f:
                f.write(f'\nexport OPENAI_API_BASE="{api_base_url}"\n')
            print(f"Environment variable added to {shell_config}.")
            print("Run the following command to make it effective immediately:")
            print(f"source {shell_config}")
        except Exception as e:
            print(f"Failed to modify shell config file: {e}")
    else:
        print("Unsupported operating system. Please set the environment variable manually.")
        return

    # Ensure the variable is immediately available for the script
    os.environ["OPENAI_API_BASE"] = api_base_url
    current_value = os.getenv("OPENAI_API_BASE")
    print(f"Current value of OPENAI_API_BASE: {current_value}")


def ask_chatgpt(messages, save_path):
    """
    Send messages to GPT, and save its response.
    :param messages: The messages to send to OpenAI.
    :param save_path: The path to save the result.
    :return: [{"role":"user","content":"..."}]
    """
    #如果消息总令牌数超过限制，直接返回 False，避免发送无效请求。
    if get_messages_tokens(messages) > MAX_PROMPT_TOKENS:
        return False
    #随机从 api_keys 列表中选择一个 API 密钥，用于调用 OpenAI 的服务  避免单一密钥的速率限制
    openai.api_key = random.choice(api_keys)
    #配置请求的api_keys，使用国内代理ChatGPT需要配置
    openai.api_key = ""
    #print(openai.api_key)
    # 每次调用GPT 调用5次
    max_try = 5
    while max_try:
        try:
            #调用 OpenAI 的 ChatCompletion.create 方法，发送消息请求并获取响应
            # messages: 消息列表，定义对话上下文。
            # model: 使用的GPT模型（如gpt - 4或gpt - 3.5 - turbo）。  本文为gpt - 3.5 - turbo
            # temperature: 控制输出的随机性，值越高，结果越随机。   本文为0.5
            # top_p: 采样参数，控制模型从概率分布中选择的范围。     本文为1
            # frequency_penalty: 调节重复内容的惩罚。           本文为0
            # presence_penalty: 调节生成内容是否倾向于引入新话题。  本文为0
            #  completion为gpt的输出结果
            completion = openai.ChatCompletion.create(messages=messages,
                                                      model=model,
                                                      temperature=temperature,
                                                      top_p=top_p,
                                                      frequency_penalty=frequency_penalty,
                                                      presence_penalty=presence_penalty)
            #print(completion["choices"][0]['message']["content"])
            with open(save_path, "w") as f:
                json.dump(completion, f)
            return True
        except Exception as e:
            print(Fore.RED + str(e), Style.RESET_ALL)
            if "This model's maximum context length is 4097 tokens." in str(e):
                break
            time.sleep(10)
            # 遇到速率限制，随机等待 60 到 120 秒再重试
            if "Rate limit reached" in str(e):
                sleep_time = random.randint(60, 120)
                time.sleep(sleep_time)
        max_try -= 1
    return False


def ask_chatgpt_extract(messages):
    """
    Send messages to GPT and extract the test result.
    :param messages: The messages to send to OpenAI.
    :return: Extracted test content as a string, or None if the request fails.
    """
    #print(messages)
    # 如果消息总令牌数超过限制，直接返回 None，避免发送无效请求。
    if get_messages_tokens(messages) > MAX_PROMPT_TOKENS:
        return None

    # 随机从 api_keys 列表中选择一个 API 密钥，用于调用 OpenAI 的服务，避免单一密钥的速率限制。
    openai.api_key = random.choice(api_keys)
    # 配置请求的api_keys，使用国内代理ChatGPT需要配置
    openai.api_key = ""
    #print(openai.api_key)
    # 每次调用 GPT 允许尝试 5 次
    max_try = 5
    while max_try:
        try:
            # 调用 OpenAI 的 ChatCompletion.create 方法，发送消息请求并获取响应
            completion = openai.ChatCompletion.create(messages=messages,
                                                      model=model,
                                                      temperature=temperature,
                                                      top_p=top_p,
                                                      frequency_penalty=frequency_penalty,
                                                      presence_penalty=presence_penalty)
            # 提取 GPT 返回的内容
            extracted_content = completion["choices"][0]['message']["content"]
            #通义千问 的提取内容
            #extracted_content=completion.choices[0].message.content
            #print(extracted_content)
            return extracted_content

        except Exception as e:
            # 打印异常信息
            print(Fore.RED + str(e), Style.RESET_ALL)

            # 如果是上下文长度超限的错误，直接终止重试
            if "This model's maximum context length is" in str(e):
                break

            # 如果遇到速率限制，随机等待 60 到 120 秒再重试
            if "Rate limit reached" in str(e):
                sleep_time = random.randint(60, 120)
                time.sleep(sleep_time)

            # 其他情况稍微等待 10 秒后重试
            time.sleep(10)

        max_try -= 1  # 减少尝试次数

    # 如果所有尝试均失败，返回 None
    return None

#产生提示 基于模板名称和给到的字典信息 返回生成的提示
def generate_prompt(template_name, context: dict):
    """
    Generate prompt via jinja2 engine
    :param template_name: the name of the prompt template
    :param context: the context to render the template
    :return:
    """
    # Load template
    template = env.get_template(template_name)
    prompt = template.render(context)

    return prompt

#获取上下文文件的信息
def load_context_file(context_file):
    if isinstance(context_file, str):
        with open(context_file, "r") as f:
            return json.load(f)
    return context_file

#基于产生的提示 产生role角色信息
def generate_messages(template_name, context_file):
    """
    This function generates messages before asking GPT, using user and system templates.
    :param template_name: The template name of the user template.
    :param context_file: The context JSON file or dict to render the template.
    :return: A list of generated messages.
    """
    #context_file 可以是一个 JSON 文件路径或字典  通常包含该焦点方法的上下文信息
    context = load_context_file(context_file)
    messages = []
    #获取该template_name的系统提示模板名称 如d1_4.jinja2的系统提示模板名称为d1_4_system.jinja2
    system_name = f"{template_name.split('.')[0]}_system.jinja2"
    system_path = os.path.join("../prompt", system_name)
    #如果存在系统提示模板则先产生系统提示词   系统提示词里的上下文字典{} 通常为空即系统提示词通常为固定单词
    if os.path.exists(system_path):
        system_message = generate_prompt(system_name, {})
        messages.append({"role": "system", "content": system_message})

    #再产生用户提示词
    user_message = generate_prompt(template_name, context)
    messages.append({"role": "user", "content": user_message})
    #messages 包含两部分信息 messages.append({"role": "system", "content": system_message} system_message为固定的系统提示词
    #messages.append({"role": "user", "content": user_message})   user_message包含填充了该焦点方法上下文的提示词
    return messages

#删除最后一个未完成的测试用例
def complete_code(code):
    """
    To complete the code
    :param code:
    :return:
    """

    # We delete the last incomplete test.
    code = code.split("@Test\n")
    code = "@Test\n".join(code[:-1]) + '}'
    return code

#如果 error_message 的长度大于50个字符，则每次从字符串末尾截掉50个字符。
#如果字符串长度不足50个字符，直接退出循环，不再截短（避免删除过多内容）。
def process_error_message(error_message, allowed_tokens):
    """
    Process the error message
    :param error_message:
    :param allowed_tokens:
    :return:
    """
    if allowed_tokens <= 0:
        return ""
    while count_tokens(error_message) > allowed_tokens:
        if len(error_message) > 50:
            error_message = error_message[:-50]
        else:
            break
    return error_message

#检查代码是否正确
def if_code_is_valid(code) -> bool:
    """
    Check if the code is valid
    :param code:
    :return: True or False
    """
    if "{" not in code or "}" not in code:
        return False
    try:
        javalang.parse.parse(code)
        return True
    except Exception:
        return False

#这段代码通过简单的语法修复（如截短代码、补全括号等），尝试将语法错误的代码修复为正确的格式，
# 适合用于自动化代码生成或修复工具的辅助模块。
def syntactic_check(code):
    """
    Syntactic repair
    :param code:
    :return: has_syntactic_error, code
    """
    if is_syntactic_correct(code):
        return False, code
    else:
        stop_point = [";", "}", "{", " "]  # Stop point
        for idx in range(len(code) - 1, -1, -1):
            if code[idx] in stop_point:
                code = code[:idx + 1]
                break
        left_bracket = code.count("{")
        right_bracket = code.count("}")
        for idx in range(left_bracket - right_bracket):
            code += "}\n"

        if is_syntactic_correct(code):
            return True, code

        matches = list(re.finditer(r"(?<=\})[^\}]+(?=@)", code))
        if matches:
            code = code[:matches[-1].start() + 1]
            left_count = code.count("{")
            right_count = code.count("}")
            for _ in range(left_count - right_count):
                code += "\n}"
        if is_syntactic_correct(code):
            return True, code
        else:
            return True, ""

#这段代码通过调用 javalang.parse，检测输入的 Java 代码字符串是否符合语法规则
def is_syntactic_correct(code):
    """
    Check if the code is syntactically correct
    :param code:
    :return:
    """
    try:
        javalang.parse.parse(code)
        return True
    except Exception as e:
        return False

#代码提取：
#从复杂字符串中提取潜在的 Java 代码块，支持多种格式和分隔符。
#语法检查与修复：
#通过 syntactic_check 对代码进行语法验证，并尝试修复不完整代码。
#灵活的处理逻辑：
#支持正则提取、分段处理，以及基于语法标记的代码边界提取。
def extract_code(string):
    """
    Check if the string is valid code and extract it.
    :param string:
    :return: has_code, extracted_code, has_syntactic_error
    """
    # if the string is valid code, return True
    if is_syntactic_correct(string):
        return True, string, False

    has_code = False
    extracted_code = ""
    has_syntactic_error = False

    # Define regex pattern to match the code blocks
    pattern = r"```[java]*([\s\S]*?)```"

    # Find all matches in the text
    matches = re.findall(pattern, string)
    if matches:
        # Filter matches to only include ones that contain "@Test"
        filtered_matches = [match.strip() for match in matches if
                            "@Test" in match and "class" in match and "import" in match]
        if filtered_matches:
            for match in filtered_matches:
                has_syntactic_error, extracted_code = syntactic_check(match)
                if extracted_code != "":
                    has_code = True
                    break

    if not has_code:
        if "```java" in string:
            separate_string = string.split("```java")[1]
            if "@Test" in separate_string:
                has_syntactic_error, temp_code = syntactic_check(separate_string)
                if temp_code != "":
                    extracted_code = temp_code
                    has_code = True
        elif "```" in string:
            separate_strings = string.split("```")
            for separate_string in separate_strings:
                if "@Test" in separate_string:
                    has_syntactic_error, temp_code = syntactic_check(separate_string)
                    if temp_code != "":
                        extracted_code = temp_code
                        has_code = True
                        break
        else:  # Define boundary
            allowed = ["import", "packages", "", "@"]
            code_lines = string.split("\n")
            start, anchor, end = -1, -1, -1
            allowed_lines = [False for _ in range(len(code_lines))]
            left_brace = {x: 0 for x in range(len(code_lines))}
            right_brace = {x: 0 for x in range(len(code_lines))}
            for i, line in enumerate(code_lines):
                left_brace[i] += line.count("{")
                right_brace[i] += line.count("}")
                striped_line = line.strip()

                for allow_start in allowed:
                    if striped_line.startswith(allow_start):
                        allowed_lines[i] = True
                        break

                if re.search(r'public class .*Test', line) and anchor == -1:
                    anchor = i

            if anchor != -1:
                start = anchor
                while start:
                    if allowed_lines[start]:
                        start -= 1

                end = anchor
                left_sum, right_sum = 0, 0
                while end < len(code_lines):
                    left_sum += left_brace[end]
                    right_sum += right_brace[end]
                    if left_sum == right_sum and left_sum >= 1 and right_sum >= 1:
                        break
                    end += 1

                temp_code = "\n".join(code_lines[start:end + 1])
                has_syntactic_error, temp_code = syntactic_check(temp_code)
                if temp_code != "":
                    extracted_code = temp_code
                    has_code = True

    extracted_code = extracted_code.strip()
    return has_code, extracted_code, has_syntactic_error

#对于提取到测试用例进行运行并记录测试结果
# 记录运行过程中可能的编译错误、运行时错误和覆盖率信息。
# 以JSON格式保存结果，便于后续分析。
def extract_and_run(input_string, output_path, class_name, method_id, test_num, project_name, package):
    """
    Extract the code and run it
    :param project_name:
    :param test_num:
    :param method_id:
    :param class_name:
    :param input_string:
    :param output_path:
    :return:
    """
    result = {}
    # 1. Extract the code
    has_code, extracted_code, has_syntactic_error = extract_code(input_string)
    if not has_code:
        return False, True
    result["has_code"] = has_code
    result["source_code"] = extracted_code
    #修复包导入
    if package:
        result["source_code"] = repair_package(extracted_code, package)
    result["has_syntactic_error"] = has_syntactic_error
    # 2. Run the code
    temp_dir = os.path.join(os.path.dirname(output_path), "temp")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    export_method_test_case(os.path.abspath(temp_dir), class_name, method_id, test_num,
                            change_class_name(result["source_code"], class_name, method_id, test_num))

    # run test
    response_dir = os.path.abspath(os.path.dirname(output_path))
    target_dir = os.path.abspath(project_dir)
    Task.test(response_dir, target_dir)
    #print("Task.test finish")
    # 3. Read the result
    if "compile_error.txt" in os.listdir(temp_dir):
        with open(os.path.join(temp_dir, "compile_error.txt"), "r") as f:
            result["compile_error"] = f.read()

    if "runtime_error.txt" in os.listdir(temp_dir):
        with open(os.path.join(temp_dir, "runtime_error.txt"), "r") as f:
            result["runtime_error"] = f.read()
    if "coverage.html" in os.listdir(temp_dir):
        result["coverage_html"] = True
    if "coverage.xml" in os.listdir(temp_dir):
        result["coverage_xml"] = True

    test_passed = False
    if "coverage_xml" in result or "coverage_html" in result:
        test_passed = True

    # 4. Save the result
    with open(output_path, "w") as f:
        json.dump(result, f)

    return test_passed, False

#获取剩余的tokens长度
def remain_prompt_tokens(messages):
    return MAX_PROMPT_TOKENS - get_messages_tokens(messages)


# 这段代码实现了一个复杂的多进程测试生成与修复的过程，用于自动化生成测试用例，
# 并通过与GPT模型的交互逐步修复错误，最终生成有效的测试代码。这是一个迭代式的流程，
# 设计目的是在代码生成过程中处理各种异常场景（如编译错误、运行错误、依赖问题等），并通过对错误的反馈逐步改进代码。
def whole_process(test_num, base_name, base_dir, repair, submits, total):
    """
    :param test_num:   默认为每个焦点方法生成6次，传入值为第几次为该方法生成
    :param base_name:  /result/direction_1/1%commons-cli-master%CommandLine%builder%d1.json
    :param base_dir:   /result/direction_1/1%commons-cli-master%CommandLine%builder%d1
    :param repair:     默认开启修复模式
    :param submits:    已经提交LLM的总次数
    :param total:      整个项目需要提交的总数
    :return:
    """
    #记录当前项目生成任务的进度，格式为 [submits / total]。
    progress = '[' + str(submits) + ' / ' + str(total) + ']'
    #为每个焦点方法每次生成创建文件夹save_dir 如：/result/direction_1/1%commons-cli-master%CommandLine%builder%d1/3   为第三次为该焦点方法生成测试用例
    save_dir = os.path.join(base_dir, str(test_num))
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    #如 /result/direction_1/1%commons-cli-master%CommandLine%builder%d1/3  下创建临时目录 /runtemp  用于存放中间结果
    run_temp_dir = os.path.join(save_dir, "runtemp")

    #steps 表示当前这次生成测试用例的操作步骤数每个步骤代表不同操作 第一步为请求GPT  第二步为Extract information from GPT, and RUN save the result  第三步为Start imports Repair 最多为18即3*6   即一轮最多生成3个文件
    #通常第一步文件为 1 + "_GPT_" + str(rounds) + ".json"     表示接受GPT的输出文件
    #通常第二步文件为 2 + "_raw_" + str(rounds) + ".json"     表示  Extract information from GPT, and RUN save the result
    #通常第三步文件为 3 + "_imports_" + str(rounds) + ".json" 表示Start imports Repair
    #rounds为焦点方法生成测试用例分为6次，每次进行6轮，第一轮用来产生测试用来产生测试用来  后五轮用来修复测试用例
    #一轮分为3步
    steps, rounds = 0, 0

    #提取方法的标识符、项目名称、类名、方法名
    method_id, project_name, class_name, method_name = parse_file_name(base_name)

    #1.在  dataset/raw_data/1%commons-cli-master%CommandLine%builder%d1 中获取方法的基础信息，如包路径、导入语句等
    with open(get_dataset_path(method_id, project_name, class_name, method_name, "raw"), "r") as f:
        raw_data = json.load(f)
    #不放在上下文中  只用来运行和编译和修复包导入用
    package = raw_data["package"]
    imports = raw_data["imports"]

    # 2.context_d_1 和 context_d_3 是目标方法的上下文数据，分别对应不同的依赖结构（direction_1 和 direction_3）
    with open(get_dataset_path(method_id, project_name, class_name, method_name, 1), "r") as f:
        context_d_1 = json.load(f)
    with open(get_dataset_path(method_id, project_name, class_name, method_name, 3), "r") as f:
        context_d_3 = json.load(f)

    #其作用是清理字符串中的导入信息和包声明，以简化代码或上下文数据
    def _remove_imports_context(strings):
        if imports:
            strings = strings.replace(imports, "")
        if package:
            strings = strings.replace(package, "")
        strings = strings.strip()
        return strings

    #移除information对于focal_method
    def remove_method_from_code(signature, information):
        # 标准化签名，去除多余空白字符但保留必要结构（如 throws）
        signature = ' '.join(signature.split())

        # 改进正则表达式，避免变长的 look-behind
        pattern = (
                r'(\n|\A)\s*(?:@Override\s*)?'  # 匹配可选的 @Override 注解，并确保匹配开始的换行符或文件开头
                + re.escape(signature).replace(r'\ ', r'\s*')  # 匹配方法签名，允许空白字符
                + r'(\s*throws\s*\w+(\s*,\s*\w+)*)?\s*'  # 可选的 throws 部分
                + r'\{'  # 开始的大括号
        )

        def find_matching_braces(code, start_index):
            open_brace_count = 1
            for i in range(start_index + 1, len(code)):
                if code[i] == '{':
                    open_brace_count += 1
                elif code[i] == '}':
                    open_brace_count -= 1
                    if open_brace_count == 0:
                        return i
            return -1  # 没有找到匹配的大括号

        # 使用多行和点所有模式来匹配可能跨多行的方法定义
        match = re.search(pattern, information, flags=re.DOTALL | re.MULTILINE)
        if match:
            start, end = match.span()
            closing_brace_index = find_matching_braces(information, end - 1)
            if closing_brace_index != -1:
                # 移除方法定义及其主体
                cleaned_information = information[:start].rstrip() + information[closing_brace_index + 1:]
                # 确保删除方法后不会破坏类结构
                cleaned_information = re.sub(r'\{\s*\}', '{}', cleaned_information)  # 清理空的大括号
                cleaned_information = re.sub(r'\n\s*\n+', '\n\n', cleaned_information).strip()  # 清理多余的空白行
                cleaned_information = re.sub(r'\n\s*@Override\s*\n*', '\n',
                                             cleaned_information).strip()  # 清理 @Override 注解前后的空白行
                cleaned_information = re.sub(r'\n\s*(?:public|private|protected|static|final)\s*\n*', '\n',
                                             cleaned_information).strip()  # 清理访问修饰符前后的空白行
                print(f"Successfully removed method: {signature}")
            else:
                print("No matching closing brace found.")
                cleaned_information = information
        else:
            print("Signature not found.")
            cleaned_information = information

        return cleaned_information

    #menthon_information = None
    type_context=None
    try:
        #每次为焦点方法产生测试用例进行6轮
        while rounds < max_rounds:
            # 1. steps 第一步Ask GPT
            steps += 1
            rounds += 1
            #输出第几次第几轮为该方法生成测试用例
            print(progress, method_id, "test_" + str(test_num), "Asking ChatGPT...", "rounds", rounds)
            #GPT生成的文件名为/result/direction_1/1%commons-cli-master%CommandLine%builder%d1/3/str(steps) + "_GPT_" + str(rounds) + ".json"  用于保存该次为该焦点方法调用GPT生成的该步该轮的输出文件    为 .json文件总共调用六轮
            gpt_file_name = os.path.join(save_dir, str(steps) + "_GPT_" + str(rounds) + ".json")
            # 如果不是第一轮就进入修复阶段针对第一轮产生的测试用例
            if rounds != 1:
                #从指定的目录中找到这次GPT修复后的最新的文件 如在/result/direction_1/1%commons-cli-master%CommandLine%builder%d1/3 获取最新的  默认返回str(steps)最大的  如 3 + "_imports_" + str(rounds) + ".json"  第三步的文件为Start imports Repair
                last_round_result = get_latest_file(save_dir)
                with open(last_round_result, "r") as f:
                    last_round_result = json.load(f)

                #raw 文件中存储了GPT生成的原始测试用例代码包括该测试用例的编译运行结果，获取该次最新一轮轮GPT生成最新的测试用例  其中raw为提取GPT输出信息后存储的测试用例代码文件
                #如 1%commons-cli-master%CommandLine%builder%d1/3/str(steps) + "_raw_" + str(rounds) + ".json"
                last_raw = get_latest_file(save_dir, suffix="raw")
                with open(last_raw, "r") as f:
                    last_raw = json.load(f)

                # 在direction_1/1%commons-cli-master%CommandLine%builder%d1中获取该焦点方法的class_name和method_name和method_code
                # 在/result/direction_1/1%commons-cli-master%CommandLine%builder%d1/3/str(step)_raw_XX.json中获取最新的生成的测试用例
                context = {"class_name": context_d_1["class_name"], "method_name": context_d_1["focal_method"],
                           "unit_test": last_raw["source_code"], "method_code": context_d_1["information"]}

                # 使用错误修复模板默认为error_3.jinja2   以及上下文信息context产生提示词messages
                messages = generate_messages(TEMPLATE_ERROR, context)
                #获取剩余的tokens长度
                allow_tokens = remain_prompt_tokens(messages)
                #当剩余长度小于最小错误剩余长度时 移除context_d_1["information"]中的导入信息
                if allow_tokens < MIN_ERROR_TOKENS:
                    context["method_code"] = _remove_imports_context(context["method_code"])
                    messages = generate_messages(TEMPLATE_ERROR, context)
                    allow_tokens = remain_prompt_tokens(messages)
                #当剩余长度还是小于最小错误剩余长度时 context_d_1["information"]的值变为context_d_3["full_fm"]
                if allow_tokens < MIN_ERROR_TOKENS:
                    context["method_code"] = context_d_3["full_fm"]
                    messages = generate_messages(TEMPLATE_ERROR, context)
                    allow_tokens = remain_prompt_tokens(messages)
                # 当剩余长度还是小于最小错误剩余长度时 移除context_d_3["full_fm"]中的导入信息
                if allow_tokens < MIN_ERROR_TOKENS:
                    context["method_code"] = _remove_imports_context(context_d_3["full_fm"])
                    messages = generate_messages(TEMPLATE_ERROR, context)
                    allow_tokens = remain_prompt_tokens(messages)

                #在context中添加添加context["error_message"]信息
                # 从最新一轮的str(steps) + "_raw_" + str(rounds) + ".json" 中获取用例代码包括该测试用例的编译运行结果
                if allow_tokens >= MIN_ERROR_TOKENS:
                    #如果上次生成结果中包含编译错误则error_mes=last_round_result["compile_error"]
                    if "compile_error" in last_round_result:
                        context["error_type"] = "compiling"
                        error_mes = process_error_message(last_round_result["compile_error"], allow_tokens)
                        context["error_message"] = error_mes
                    #如果上次生成的结果中包含中包含运行时错误则error_mes=last_round_result["runtime_error"]
                    if "runtime_error" in last_round_result:
                        context["error_type"] = "running"
                        error_mes = process_error_message(last_round_result["runtime_error"], allow_tokens)
                        context["error_message"] = error_mes
                #如果 allow_tokens 小于 MIN_ERROR_TOKENS：打印错误日志，说明 Token 不足，无法继续。中断当前流程，退出循环（break）。
                else:
                    print(progress, Fore.RED + method_id, "Tokens not enough, test fatal error...",
                          Style.RESET_ALL)  # Fatal error
                    break
                #检查 last_round_result 中是否包含任何错误信息：如果既没有 "compile_error" 也没有 "runtime_error"：打印超时错误（可能因为 GPT 没有及时返回结果）。中断当前流程。
                if "compile_error" not in last_round_result and "runtime_error" not in last_round_result:
                    print(progress, Fore.RED + method_id, "Timeout error, test fatal error...", Style.RESET_ALL)
                    break
                #生成新的 GPT消息因为添加了context["error_message"]信息
                messages = generate_messages(TEMPLATE_ERROR, context)
                # print('-------------------')
                # print(context["error_message"])
            #第一轮为该焦点方法生成测试用例   现在需要修改流程  需要先产生函数意图和分支信息再产生测试用例其他不变
            else:  # Direction_1 or Direction_3
                # context_d_3["c_deps"] 和 context_d_3["m_deps"]：分别表示类级别依赖和方法级别依赖。如果 context_d_3 中没有依赖，表示方法独立（Direction_1 情况）。
                if not context_d_3["c_deps"] and not context_d_3["m_deps"]:  # No dependencies 使用 d_1
                    # 创建 context_d_1 的深拷贝，确保不会修改原始数据
                    context = copy.deepcopy(context_d_1)
                    menthon_information=context_d_1["information"]
                    type_context=1
                    # 生成意图信息消息，使用 TEMPLATE_NO_DEPS_INTENTION
                    messages_intention = generate_messages(TEMPLATE_NO_DEPS_INTENTION, context)
                    if remain_prompt_tokens(messages_intention) < 0:
                        context["information"] = _remove_imports_context(context["information"])
                        #menthon_information=context["information"]
                        messages_intention = generate_messages(TEMPLATE_NO_DEPS_INTENTION, context)
                        if remain_prompt_tokens(messages_intention) < 0:
                            messages_intention = []

                    # 调用 GPT 获取意图信息的输出
                    if messages_intention:
                        intention_output = ask_chatgpt_extract(messages_intention)
                    else:
                        intention_output = None

                    # 生成分支信息消息，使用 TEMPLATE_NO_DEPS_BRANCH
                    messages_branch = generate_messages(TEMPLATE_NO_DEPS_BRANCH, context)
                    if remain_prompt_tokens(messages_branch) < 0:
                        context["information"] = _remove_imports_context(context["information"])
                        messages_branch = generate_messages(TEMPLATE_NO_DEPS_BRANCH, context)
                        if remain_prompt_tokens(messages_branch) < 0:
                            messages_branch = []

                    # 调用 GPT 获取分支信息的输出
                    if messages_branch:
                        branch_output = ask_chatgpt_extract(messages_branch)
                    else:
                        branch_output = None

                else:  # 如果 context_d_3 中存在依赖
                    context = copy.deepcopy(context_d_3)
                    menthon_information=context["full_fm"]
                    type_context = 3
                    # 生成意图信息消息，使用 TEMPLATE_WITH_DEPS_INTENTION
                    messages_intention = generate_messages(TEMPLATE_WITH_DEPS_INTENTION, context)
                    if remain_prompt_tokens(messages_intention) < 0:
                        context["full_fm"] = _remove_imports_context(context["full_fm"])
                        #menthon_information = context["full_fm"]
                        messages_intention = generate_messages(TEMPLATE_WITH_DEPS_INTENTION, context)
                        if remain_prompt_tokens(messages_intention) < 0:
                            messages_intention = []

                    # 调用 GPT 获取意图信息的输出
                    if messages_intention:
                        intention_output = ask_chatgpt_extract(messages_intention)
                    else:
                        intention_output = None

                    # 生成分支信息消息，使用 TEMPLATE_WITH_DEPS_BRANCH
                    messages_branch = generate_messages(TEMPLATE_WITH_DEPS_BRANCH, context)
                    if remain_prompt_tokens(messages_branch) < 0:
                        context["full_fm"] = _remove_imports_context(context["full_fm"])
                        messages_branch = generate_messages(TEMPLATE_WITH_DEPS_BRANCH, context)
                        if remain_prompt_tokens(messages_branch) < 0:
                            messages_branch = []

                    # 调用 GPT 获取分支信息的输出
                    if messages_branch:
                        branch_output = ask_chatgpt_extract(messages_branch)
                    else:
                        branch_output = None

                # 如果 messages_intention和messages_branch 列表为空，说明之前的提示生成失败，需要采取降级措施。
                if not messages_intention or not messages_branch:
                    # 使用 context_d_1 作为该焦点方法的上下文
                    context = copy.deepcopy(context_d_1)
                    # 并使用 context_d_3["full_fm"] 替换掉 context_d_1["information"]
                    context["information"] = context_d_3["full_fm"]
                    menthon_information = context["information"]
                    type_context = 2
                    # 生成意图信息消息，使用 TEMPLATE_NO_DEPS_INTENTION
                    messages_intention = generate_messages(TEMPLATE_NO_DEPS_INTENTION, context)
                    if remain_prompt_tokens(messages_intention) < 0:
                        context["information"] = _remove_imports_context(context["information"])
                        #menthon_information = context["information"]
                        messages_intention = generate_messages(TEMPLATE_NO_DEPS_INTENTION, context)
                        if remain_prompt_tokens(messages_intention) < 0:  # Failed generating messages
                            print(progress, Fore.RED + "Tokens not enough, test fatal error...", Style.RESET_ALL)
                            break

                    # 调用 GPT 获取意图信息的输出
                    if messages_intention:
                        intention_output = ask_chatgpt_extract(messages_intention)
                    else:
                        intention_output = None

                    # 生成分支信息消息，使用 TEMPLATE_NO_DEPS_BRANCH
                    messages_branch = generate_messages(TEMPLATE_NO_DEPS_BRANCH, context)
                    if remain_prompt_tokens(messages_branch) < 0:
                        context["information"] = _remove_imports_context(context["information"])
                        messages_branch = generate_messages(TEMPLATE_NO_DEPS_BRANCH, context)
                        if remain_prompt_tokens(messages_branch) < 0:  # Failed generating messages
                            print(progress, Fore.RED + "Tokens not enough, test fatal error...", Style.RESET_ALL)
                            break

                    # 调用 GPT 获取分支信息的输出
                    if messages_branch:
                        branch_output = ask_chatgpt_extract(messages_branch)
                    else:
                        branch_output = None
                # print(Fore.BLUE, messages[1]['content'], Style.RESET_ALL)
                # 将产生的函数意图和分支信息存储在 context_method 中
                if type_context == 1:
                    context_method = copy.deepcopy(context_d_1)
                    context_method["branch"] = branch_output
                    context_method["intention"] = intention_output
                    #print(context_method["information"])
                    #print("*********************")
                    # context_method["information"]=remove_method_from_code(context_d_3["focal_method"],context_method["information"])
                    # print(context_d_3["focal_method"])
                    # print("*********************")
                    # print(context_method["information"])
                    # 使用产生的函数意图和分支信息生成新的提示messages产生该次为该焦点方法第一轮的测试用例  默认提示模板为d1_4_method.jinja2
                    messages = generate_messages(TEMPLATE_INTENTION_BRANCH, context_method)
                    if remain_prompt_tokens(messages) < 0:  # Truncate information
                        context_method["information"] = _remove_imports_context(context_method["information"])
                        messages = generate_messages(TEMPLATE_INTENTION_BRANCH, context_method)
                        if remain_prompt_tokens(messages) < 0:  # Failed generating messages
                            messages = []
                            #print(messages)

                if type_context == 3:
                    context_method = copy.deepcopy(context_d_3)
                    context_method["branch"] = branch_output
                    context_method["intention"] = intention_output
                    # print(context_method["information"])
                    # print("*********************")
                    # context_method["information"] = remove_method_from_code(context_d_3["focal_method"], context_method["information"])
                    # print(context_d_3["focal_method"])
                    # print("*********************")
                    # print(context_method["information"])
                    # 使用产生的函数意图和分支信息生成新的提示messages产生该次为该焦点方法第一轮的测试用例  默认提示模板为d3_4_method.jinja2
                    messages = generate_messages(TEMPLATE_INTENTION_BRANCH_WITH_DEPS, context_method)
                    if remain_prompt_tokens(messages) < 0:  # Need Truncate information
                        context_method["full_fm"] = _remove_imports_context(context_method["full_fm"])
                        messages = generate_messages(TEMPLATE_INTENTION_BRANCH_WITH_DEPS, context_method)
                        if remain_prompt_tokens(messages) < 0:  # Failed generating messages
                            messages = []
                            # print(messages)

                if type_context == 2:
                    context_method = copy.deepcopy(context_d_1)  # use direction 1 as template
                    context_method["information"] = context_d_3["full_fm"]  # use full_fm d_3 as context
                    context_method["branch"] = branch_output
                    context_method["intention"] = intention_output
                    # print(context_method["information"])
                    # print("*********************")
                    # context_method["information"] = remove_method_from_code(context_d_3["focal_method"],context_method["information"])
                    # print(context_d_3["focal_method"])
                    # print("*********************")
                    # print(context_method["information"])
                    # 使用产生的函数意图和分支信息生成新的提示messages产生该次为该焦点方法第一轮的测试用例  默认提示模板为d1_4_method.jinja2
                    messages = generate_messages(TEMPLATE_INTENTION_BRANCH, context_method)
                    if remain_prompt_tokens(messages) < 0:  # Truncate information
                        context_method["information"] = _remove_imports_context(context_method["information"])
                        messages = generate_messages(TEMPLATE_INTENTION_BRANCH, context_method)
                        if remain_prompt_tokens(messages) < 0:  # Failed generating messages
                            print(progress, Fore.RED + "Tokens not enough, test fatal error...", Style.RESET_ALL)
                            break
                #print(messages)
            #gpt_file_name  为保存gpt输出的文件  如/result/direction_1/1%commons-cli-master%CommandLine%builder%d1/3/str(steps) + "_GPT_" + str(rounds) + ".json"
            status = ask_chatgpt(messages, gpt_file_name)
            if not status:
                print(progress, Fore.RED + 'OpenAI Fail processing messages', Style.RESET_ALL)
                break

            with open(gpt_file_name, "r") as f:
                gpt_result = json.load(f)

            # 2. steps第二步  Extract information from GPT, and RUN save the result
            steps += 1
            #构造保存GPT生成的测试用例的文件名 如1%commons-cli-master%CommandLine%builder%d1/3/str(steps) + "_raw_" + str(rounds) + ".json"
            raw_file_name = os.path.join(save_dir, str(steps) + "_raw_" + str(rounds) + ".json")

            # extract the test and save the result in raw_file_name
            #数据路径：gpt_result["choices"][0]['message']["content"]，其中 choices 是 GPT 响应结果的核心字段
            input_string = gpt_result["choices"][0]['message']["content"]
            # 对于提取到测试用例进行运行并记录测试结果 有多种组装结果
            #如 (True, False)  测试运行成功，生成了覆盖率文件   无致命错误，运行过程正常
            #如 (False, True)   未能提取到有效的测试代码       GPT 返回的代码内容存在问题（如语法错误、无代码块等）
            #如 (False, False)   提取到了代码，但运行失败      可能原因：编译错误（compile_error.txt）。运行时错误（runtime_error.txt）。没有生成覆盖率报告
            test_passed, fatal_error = extract_and_run(input_string, raw_file_name, class_name, method_id, test_num,
                                                       project_name,
                                                       package)
            if test_passed:
                #打印绿色的提示信息，表明测试通过 退出循环：表示当前这次为该焦点方法测试完成，不需要再处理下一步
                print(progress, Fore.GREEN + method_id, "test_" + str(test_num), "steps", steps, "rounds", rounds,
                      "test passed",
                      Style.RESET_ALL)
                break

            #只有当代码成功提取、测试运行完成后，raw_file_name 文件才会被生成  包含内容 是否提取到了代码  编译错误、运行时错误信息  覆盖率数据等
            if not os.path.exists(raw_file_name):
                print(progress, Fore.RED + method_id, "test_" + str(test_num), "steps", steps, "rounds", rounds,
                      "no code in raw result", Style.RESET_ALL)
                break

            #get_latest_file默认获取 str(steps)最大的   1%commons-cli-master%CommandLine%builder%d1/3/str(steps) + "_raw_" + str(rounds) + ".json"
            # Open up the raw result
            with open(get_latest_file(save_dir), "r") as f:
                raw_result = json.load(f)

            # 3. Start imports Repair
            steps += 1
            # 为本次修复生成一个保存测试结果的文件路径，文件名中包含步骤编号（steps）+"_imports_"+轮次编号（rounds）
            imports_file_name = os.path.join(save_dir, str(steps) + "_imports_" + str(rounds) + ".json")
            # 获取最新生成成的测试用例
            source_code = raw_result["source_code"]
            #从 raw_result 提取原始代码，调用 repair_imports 函数对代码中的 import 语句进行修复。例如，可能会修复缺少或错误的模块导入。
            source_code = repair_imports(source_code, imports)
            #执行代码对应的测试用例，记录运行结果，包括是否测试通过、是否出现致命错误等   将运行结果保存到 imports_file_name 指定的路径中
            test_passed, fatal_error = extract_and_run(source_code, imports_file_name, class_name, method_id, test_num,
                                                       project_name,
                                                       package)
            if test_passed:
                #包导入修复成功，表示本次为该焦点方法生成的测试用例完成
                print(progress, Fore.GREEN + method_id, "test_" + str(test_num), "steps", steps, "rounds", rounds,
                      "test passed",
                      Style.RESET_ALL)
                break
            if fatal_error:
                #如果运行过程中出现无法修复的严重错误（如代码完全无法运行或语法错误），则结束本次测试用例修复工作因为无意义
                print(progress, Fore.RED + method_id, "test_" + str(test_num), "steps", steps, "rounds", rounds,
                      "fatal error",
                      Style.RESET_ALL)
                break
            #测试未通过但未出现致命错误，打印提示信息并尝试进一步修复本次生成的测试用例
            print(progress, Fore.YELLOW + method_id, "test_" + str(test_num), "Test failed, fixing...", "rounds",
                  rounds,
                  Style.RESET_ALL)
            #如果 repair 标志为 False，表示不进行修复，生成测试用例后直接退出循环   默认为开启
            if not repair:  # If we do not want to repair the code, we don't need to second round
                break
    except Exception as e:
        print(progress, Fore.RED + str(e), Style.RESET_ALL)
    #删除运行过程中本次为该焦点方法生成的临时目录下 /runtemp，避免占用额外存储空间
    if os.path.exists(run_temp_dir):
        run_temp_dir = os.path.abspath(run_temp_dir)
        shutil.rmtree(run_temp_dir)


# 这段代码实现了一个基于单进程或多进程的自动化测试修复任务的启动逻辑，
# source_dir：从 dataset_dir 指定的目录加载数据。 如../dataset/direction_1
# result_path：结果存放路径。    如../result/scope_test%2020241117222232%focal
# 代码通过任务分发实现并行化（多进程）或串行处理（单进程）。
def start_whole_process(source_dir, result_path, multiprocess=False, repair=True):
    """
    Start repair process
    :param repair:  Whether to repair the code
    :param multiprocess: Whether to use multiprocess
    :param source_dir: The directory of the dataset or scoped dataset.
    :return:
    """
    # 从../dataset/direction_1下获取焦点方法的上下文信息并存储到file_paths数组里
    set_environment_variable()
    file_paths = []
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".json"):
                file_paths.append(os.path.join(root, file))

    #submits 变量用来跟踪提交任务的数量
    submits = 0
    #test_number  作为为每个焦点函数执行的生成次数 默认test_number = 6
    #total 是任务的总数，计算方法是 焦点方法数目 * test_number
    total = len(file_paths) * test_number
    if multiprocess:
        print("Multi process executing!")
        # Create a process pool with maximum of process_number
        with concurrent.futures.ProcessPoolExecutor(max_workers=process_number) as executor:
            for idx, file_path in enumerate(file_paths):
                _, base_name = os.path.split(file_path.replace("/dataset/", "/result/"))
                base_dir = os.path.join(result_path, base_name.split(".json")[0])
                for test_num in range(1, test_number + 1):
                    submits += 1
                    executor.submit(whole_process, test_num, base_name, base_dir, repair, submits, total)
        print("Main process executing!")
    else:
        print("Single process executing!")
        #file_paths 是一个包含所有待处理 .json 文件路径的列表。
        # enumerate 会同时返回每个文件的索引（idx）和文件路径（file_path）
        for idx, file_path in enumerate(file_paths):
            #base_name值 如 /result/direction_1/1%commons-cli-master%CommandLine%builder%d1.json
            #将文件路径中的 /dataset/ 替换为 /result/，从而构建输出文件的输出路径
            _, base_name = os.path.split(file_path.replace("/dataset/", "/result/"))
            #并去除文件的 .json 扩展名，创建文件夹用于存储GPT输出信息
            #如 /result/direction_1/1%commons-cli-master%CommandLine%builder%d1
            base_dir = os.path.join(result_path, base_name.split(".json")[0])
            #默认为每个焦点方法生成6次
            for test_num in range(1, test_number + 1):
                submits += 1
                whole_process(test_num, base_name, base_dir, repair, submits, total)
