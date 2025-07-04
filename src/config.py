import configparser

# Use configparser.ConfigParser() to read config.ini file.
#创建一个 ConfigParser 实例，用于读取和解析配置文件。
config = configparser.ConfigParser()
config.read("../config/config.ini")
#通用配置 涉及到进程数、测试次数、最大轮数、提示令牌数量等参数。
process_number = eval(config.get("DEFAULT", "process_number"))
test_number = eval(config.get("DEFAULT", "test_number"))
max_rounds = eval(config.get("DEFAULT", "max_rounds"))
MAX_PROMPT_TOKENS = eval(config.get("DEFAULT", "MAX_PROMPT_TOKENS"))
MIN_ERROR_TOKENS = eval(config.get("DEFAULT", "MIN_ERROR_TOKENS"))
TIMEOUT = eval(config.get("DEFAULT", "TIMEOUT"))
#模板配置: 分别对应没有依赖产生函数意图和分支条件信息、带有依赖产生函数意图和分支条件信息和错误提示的模板
TEMPLATE_NO_DEPS = config.get("DEFAULT", "PROMPT_TEMPLATE_NO_DEPS")
TEMPLATE_NO_DEPS_INTENTION = config.get("DEFAULT", "PROMPT_TEMPLATE_NO_DEPS_INTENTION")
TEMPLATE_NO_DEPS_BRANCH = config.get("DEFAULT", "PROMPT_TEMPLATE_NO_DEPS_BRANCH")
TEMPLATE_INTENTION_BRANCH = config.get("DEFAULT", "PROMPT_TEMPLATE_INTENTION_BRANCH")
TEMPLATE_WITH_DEPS = config.get("DEFAULT", "PROMPT_TEMPLATE_DEPS")
TEMPLATE_WITH_DEPS_INTENTION = config.get("DEFAULT", "PROMPT_TEMPLATE_DEPS_INTENTION")
TEMPLATE_WITH_DEPS_BRANCH = config.get("DEFAULT", "PROMPT_TEMPLATE_DEPS_BRANCH")
TEMPLATE_INTENTION_BRANCH_WITH_DEPS = config.get("DEFAULT", "PROMPT_TEMPLATE_INTENTION_BRANCH_WITH_DEPS")
TEMPLATE_ERROR = config.get("DEFAULT", "PROMPT_TEMPLATE_ERROR")

#语言和工具配置 语言类型、文件路径、工具 JAR 包等
LANGUAGE = config.get("DEFAULT", "LANGUAGE")
GRAMMAR_FILE = config.get("DEFAULT", "GRAMMAR_FILE")
COBERTURA_DIR = config.get("DEFAULT", "COBERTURA_DIR")
JUNIT_JAR = config.get("DEFAULT", "JUNIT_JAR")
MOCKITO_JAR = config.get("DEFAULT", "MOCKITO_JAR")
LOG4J_JAR = config.get("DEFAULT", "LOG4J_JAR")
JACOCO_AGENT = config.get("DEFAULT", "JACOCO_AGENT")
JACOCO_CLI = config.get("DEFAULT", "JACOCO_CLI")
REPORT_FORMAT = config.get("DEFAULT", "REPORT_FORMAT")
#项目和结果目录: 提取数据集、结果和项目目录的路径
dataset_dir = config.get("DEFAULT", "dataset_dir")
result_dir = config.get("DEFAULT", "result_dir")
project_dir = config.get("DEFAULT", "project_dir")
#OpenAI API 配置:  提取 OpenAI API 的配置项，包括 API 密钥、模型类型、温度参数、top_p 等设置
api_keys = eval(config.get("openai", "api_keys"))
model = config.get("openai", "model")
temperature = eval(config.get("openai", "temperature"))
top_p = eval(config.get("openai", "top_p"))
frequency_penalty = eval(config.get("openai", "frequency_penalty"))
presence_penalty = eval(config.get("openai", "presence_penalty"))
