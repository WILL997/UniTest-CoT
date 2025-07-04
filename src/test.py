import re

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
            cleaned_information = re.sub(r'\n\s*@Override\s*\n*', '\n', cleaned_information).strip()  # 清理 @Override 注解前后的空白行
            cleaned_information = re.sub(r'\n\s*(?:public|private|protected|static|final)\s*\n*', '\n', cleaned_information).strip()  # 清理访问修饰符前后的空白行
            print(f"Successfully removed method: {signature}")
        else:
            print("No matching closing brace found.")
            cleaned_information = information
    else:
        print("Signature not found.")
        cleaned_information = information

    return cleaned_information

# 测试
information = '''
@Override public FilterHelpAppendable append(final CharSequence csq, final int start, final int end)
{
    output.append(csq, start, end);
    return this;
}

static <T extends CharSequence> T defaultValue(final T str, final T defaultValue)
{
    return isEmpty(str) ? defaultValue : str;
}

@Override public String toString()
{
    return String.format("TextStyle{%s, l:%s, i:%s, %s, min:%s, max:%s}", alignment, leftPad, indent, scalable, minWidth,
            maxWidth == UNSET_MAX_WIDTH ? "unset" : maxWidth);
}


public <T> T getParsedOptionValue(final OptionGroup optionGroup) throws ParseException {
        return getParsedOptionValue(optionGroup, () -> null);
}
'''

# 示例签名
signature = 'public  T getParsedOptionValue(final OptionGroup optionGroup) throws ParseException'

# 调用函数
cleaned_code = remove_method_from_code(signature, information)
print(cleaned_code)
