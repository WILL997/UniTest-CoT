from tree_sitter import Language, Parser
from typing import List


class ClassParser():
    #它初始化了一个使用 Tree-sitter 解析器解析特定编程语言（如 Java）语法的实例。
    def __init__(self, grammar_file, language):
        self.content = None
        JAVA_LANGUAGE = Language(grammar_file, language)
        self.parser = Parser()
        self.parser.set_language(JAVA_LANGUAGE)

    #解析 Java 文件的工具方法，使用 Tree-sitter 构建语法树，并提取文件中的类和方法的元数据
    #解析导入语句   解析类   提取类名称  解析类的元数据  解析类的方法 补充包信息
    #返回值如下  {
    #    "class_name": "HelloWorld",
    #    "package": "com.example",
    #    "imports": ["java.util.List", "java.util.Map"],
    #  "fields": ["private String message"],
    #  "has_constructor": True,
    #     "methods": [
    #         {
    #             "method_name": "HelloWorld",
    #             "parameters": [],
    #             "return_type": None,
    #             "modifiers": ["public"]
    #         },
    #         {
    #             "method_name": "printMessage",
    #             "parameters": [],
    #             "return_type": "void",
    #             "modifiers": ["public"]
    #         }
    #     ],
    #     "class_path": "/path/to/HelloWorld.java"
    # }
    def parse_file(self, file):
        """
        Parses a java file and extract metadata of all the classes and methods defined
        """

        # Build Tree
        with open(file, 'r') as content_file:
            try:
                content = content_file.read()
                self.content = content
            except:
                return list()
        tree = self.parser.parse(bytes(content, "utf8"))
        package_declaration = (node for node in tree.root_node.children if node.type == 'package_declaration')
        classes = (node for node in tree.root_node.children if node.type == 'class_declaration')
        imports = (node for node in tree.root_node.children if node.type == 'import_declaration')

        import_list = list()
        for _import in imports:
            import_list.append(_import.text.decode().lstrip("b'"))

        # Parsed Classes
        parsed_classes = list()

        # Classes
        for _class in classes:

            # Class metadata
            class_identifier = self.match_from_span(
                [child for child in _class.children if child.type == 'identifier'][0], content).strip()
            class_metadata = self.get_class_metadata(_class, content)

            methods = list()

            class_metadata['has_constructor'] = False
            # Parse methods
            for child in (child for child in _class.children if child.type == 'class_body'):
                for _, node in enumerate(child.children):
                    if node.type == 'method_declaration' or node.type == 'constructor_declaration':
                        if node.type == 'constructor_declaration':
                            class_metadata['has_constructor'] = True
                        # Read Method metadata
                        method_metadata = ClassParser.get_function_metadata(class_identifier, node,
                                                                            class_metadata['fields'], content)
                        methods.append(method_metadata)

            class_metadata['methods'] = methods
            class_metadata['imports'] = import_list
            class_metadata['class_path'] = file
            class_metadata['package'] = ""
            for _package in package_declaration:
                class_metadata['package'] = _package.text.decode().lstrip("b'")
            parsed_classes.append(class_metadata)

        return parsed_classes

    #用于提取 Java 类的元数据。它解析类的属性、继承关系、实现的接口、字段等信息，返回一个结构化的字典。
    @staticmethod
    def get_class_metadata(class_node, blob: str):
        """
        Extract class-level metadata
        """
        metadata = {
            'class_name': '',
            'superclass': '',
            'interfaces': '',
            'c_sig': '',
            'has_constructor': False,
            'fields': '',
            'methods': [],
            'argument_list': '',
        }

        # Superclass
        superclass = class_node.child_by_field_name('superclass')
        if superclass:
            metadata['superclass'] = ClassParser.match_from_span(superclass, blob)

        # Interfaces
        interfaces = class_node.child_by_field_name('interfaces')
        if interfaces:
            metadata['interfaces'] = ClassParser.match_from_span(interfaces, blob)

        metadata['c_sig'] = ClassParser.get_class_full_signature(class_node, blob)

        # Fields
        fields = ClassParser.get_class_fields(class_node, blob)
        metadata['fields'] = fields

        # Identifier and Arguments
        is_header = False
        for n in class_node.children:
            if is_header:
                if n.type == 'identifier':
                    metadata['class_name'] = ClassParser.match_from_span(n, blob).strip('(:')
                elif n.type == 'argument_list':
                    metadata['argument_list'] = ClassParser.match_from_span(n, blob)
            if n.type == 'class':
                is_header = True
            elif n.type == ':':
                break
        return metadata

    #用于从语法树中提取 Java 类的完整签名（即类声明部分的代码）。
    # 它使用 Tree-sitter 的语法树信息结合源代码，精确定位并提取类的头部声明（不包括类体）
    @staticmethod
    def get_class_full_signature(class_node, blob: str):
        """
        Extract the source code associated with a node of the tree
        """
        class_body = class_node.child_by_field_name('body')
        body_line_start = class_body.start_point[0]
        body_char_start = class_body.start_point[1]
        class_line_start = class_node.start_point[0]
        class_char_start = class_node.start_point[1]
        lines = blob.split('\n')
        if class_line_start != body_line_start:
            return '\n'.join(
                [lines[class_line_start][class_char_start:]] + lines[class_line_start + 1:body_line_start] + [
                    lines[body_line_start][:body_char_start - 1]])
        else:
            return lines[class_line_start][class_char_start:body_char_start - 1]

    #用于从 Java 类的语法树节点中提取所有字段（成员变量）的元数据。
    # 它使用 Tree-sitter 的节点访问功能和源代码字符串 blob 来生成字段的详细信息，包括修饰符、类型、变量名称等。
    @staticmethod
    def get_class_fields(class_node, blob: str):
        """
        Extract metadata for all the fields defined in the class
        """

        body_node = class_node.child_by_field_name("body")
        fields = []

        for f in ClassParser.children_of_type(body_node, "field_declaration"):
            # Complete field
            field_dict = {"original_string": ClassParser.match_from_span(f, blob)}

            # Modifier
            modifiers_node_list = ClassParser.children_of_type(f, "modifiers")
            if len(modifiers_node_list) > 0:
                modifiers_node = modifiers_node_list[0]
                field_dict["modifier"] = ClassParser.match_from_span(modifiers_node, blob)
            else:
                field_dict["modifier"] = ""

            # Type
            type_node = f.child_by_field_name("type")
            field_dict["type"] = ClassParser.match_from_span(type_node, blob)

            # Declarator
            declarator_node = f.child_by_field_name("declarator")
            field_dict["declarator"] = ClassParser.match_from_span(declarator_node, blob)

            # Var name
            var_node = declarator_node.child_by_field_name("name")
            field_dict["var_name"] = ClassParser.match_from_span(var_node, blob)

            fields.append(field_dict)

        return fields

    #get_function_metadata，用于提取 Java 类中方法的详细元数据。
    # 它结合了语法树节点和源代码，生成包含方法名称、参数、修饰符、返回值、签名等信息的字典
    @staticmethod
    def get_function_metadata(class_identifier, function_node, class_fields, blob: str):
        """
        Extract method-level metadata
        """
        metadata = {
            'method_name': '',
            'm_sig': '',
            'class': '',
            'source_code': '',
            'parameters': '',
            'modifiers': '',
            'return': '',
            'signature': '',
            'class_method_signature': '',
            'is_constructor': '',
            'use_field': '',
            'is_get_set': '',
            'm_deps': '',
        }
        # Parameters
        full_parameter_list, dependent_classes, instance_2_classes = ClassParser.get_method_name_and_params(
            function_node, metadata, blob)
        full_parameters = ' '.join(full_parameter_list)
        # Add field dependencies
        dependent_classes, instance_2_classes = ClassParser.get_field_dependencies(dependent_classes,
                                                                                   instance_2_classes, class_fields)
        # Body
        metadata['source_code'] = ClassParser.match_from_span(function_node, blob)
        metadata['class'] = class_identifier
        # is getter or setter
        metadata['is_get_set'] = ClassParser.is_gs(function_node, class_fields)
        # use fields or not
        if metadata['is_get_set']:
            metadata['use_field'] = True
        else:
            metadata['use_field'] = ClassParser.use_fields(function_node.child_by_field_name('body'), class_fields,
                                                           blob)
        # Constructor
        metadata['is_constructor'] = False
        # if "constructor" in function_node.type:
        if function_node.type == 'constructor_declaration':
            metadata['is_get_set'] = False
            metadata['is_constructor'] = True
        # Method Invocations
        ClassParser.get_method_m_deps(function_node, metadata, dependent_classes, instance_2_classes, blob)
        # Modifiers and Return Value
        for child in function_node.children:
            if child.type == "modifiers":
                metadata['modifiers'] = ' '.join(ClassParser.match_from_span(child, blob).split())
            if "type" in child.type:
                metadata['return'] = ClassParser.match_from_span(child, blob)
        # Signature
        metadata['signature'] = '{} {}{}'.format(metadata['return'], metadata['method_name'], full_parameters)
        metadata['m_sig'] = '{} {} {}{}'.format(metadata['modifiers'], metadata['return'], metadata['method_name'],
                                                full_parameters)
        metadata['class_method_signature'] = '{}.{}{}'.format(class_identifier, metadata['method_name'],
                                                              full_parameters)

        return metadata

    #用于提取 Java 类中方法的详细元数据。
    # 它结合了语法树节点和源代码，生成包含方法名称、参数、修饰符、返回值、签名等信息的字典
    @staticmethod
    def get_method_name_and_params(function_node, metadata, blob: str):
        """
        Get focal method name and parameters
        :return: dependent classes in parameters, variables to ClassTypes
        """
        declarators = []
        ClassParser.traverse_type(function_node, declarators, '{}_declaration'.format(function_node.type.split('_')[0]))
        parameters = []
        full_parameter_list = []
        dependent_classes = []
        instance_2_classes = {}
        for n in declarators[0].children:
            if n.type == 'identifier':
                metadata['method_name'] = ClassParser.match_from_span(n, blob).strip('(')
            elif n.type == 'formal_parameters':
                full_parameter_list.append(ClassParser.match_from_span(n, blob))
                parameters, d_classes, inst_2_classes = ClassParser.parse_parameters(n, blob)
                dependent_classes.extend(d_classes)
                instance_2_classes.update(inst_2_classes)
        metadata['parameters'] = metadata['method_name'] + '(' + ', '.join(parameters) + ')'
        return full_parameter_list, dependent_classes, instance_2_classes

    # 主要用于解析类的字段依赖关系，通过分析类中字段的类型和变量名，
    # 将字段类型添加到依赖类列表，并建立字段名与其类型的映射
    @staticmethod
    def get_field_dependencies(dependent_classes, instance_2_classes, fields):
        for f in fields:
            instance_2_classes[f['var_name']] = f['type']
            dependent_classes.append(f['type'])
        return dependent_classes, instance_2_classes

    #主要用于提取指定方法的依赖信息，分析方法调用的对象、参数类型和调用签名，
    # 从而生成一个方法依赖关系的结构化数据
    @staticmethod
    def get_method_m_deps(function_node, metadata, dependent_classes, instance_2_classes, blob: str):
        """
        Get method dependencies of focal method.
        """
        var_declares = ClassParser.get_var_declare(function_node, instance_2_classes, blob)
        invocation = []
        method_invocations = list()
        obj2method_invocations = {}
        ClassParser.traverse_type(function_node, invocation, '{}_invocation'.format(function_node.type.split('_')[0]))
        for inv in invocation:
            name = inv.child_by_field_name('name')
            method_invocation = ClassParser.match_from_span(name, blob)
            method_invocations.append(method_invocation)

            obj = inv.child_by_field_name('object')
            args = inv.child_by_field_name('arguments')
            method_inv_args_type = ClassParser.get_inv_arg_type(var_declares, args, blob)
            if obj is not None:
                obj_instance = ClassParser.match_from_span(obj, blob)
                if obj_instance not in instance_2_classes:
                    continue
                obj_class = instance_2_classes[obj_instance]
                method_brief_sig = method_invocation + '(' + ', '.join(method_inv_args_type) + ')'
                if obj_class in dependent_classes:
                    obj2method_invocations.setdefault(obj_class, [])
                    if method_brief_sig not in obj2method_invocations[obj_class]:
                        obj2method_invocations[obj_class].append(method_brief_sig)
            else:
                obj2method_invocations.setdefault('this', [])
                method_brief_sig = method_invocation + '(' + ', '.join(method_inv_args_type) + ')'
                if method_brief_sig not in obj2method_invocations['this']:
                    obj2method_invocations['this'].append(method_brief_sig)
        metadata['m_deps'] = obj2method_invocations

    #它通过检查参数列表中的每个参数，并结合方法体内已声明的变量，推断出这些参数的类型。
    @staticmethod
    def get_inv_arg_type(var_declare, arg_list, blob: str):
        """
        Get argument types of an invocation in focal method body.
        :param var_declare: declared variables in body.
        :param arg_list: argument list of the invocation.
        """
        type_list = []
        for arg_node in arg_list.named_children:
            if arg_node.type == 'identifier':
                arg = ClassParser.match_from_span(arg_node, blob)
                if arg in var_declare:
                    type_list.append(var_declare[arg])
        return type_list

    #方法的作用是从方法体内提取所有的局部变量声明以及方法的参数声明，并将它们存储为变量名到数据类型的映射。
    @staticmethod
    def get_var_declare(function_node, param_var_declares, blob: str):
        """
        Get all variable declarations in this body and method's parameters.
        """
        var_declares = {}
        var_declares.update(param_var_declares)
        declare_nodes = []
        ClassParser.traverse_type(function_node, declare_nodes, 'local_variable_declaration')
        for dn in declare_nodes:
            for child in dn.children:
                if child.type == 'type_identifier':
                    dtype = ClassParser.match_from_span(child, blob)
                    var_node = child.next_named_sibling
                    if var_node.type == 'variable_declarator':
                        for _child in var_node.children:
                            if _child.type == 'identifier':
                                dvar = ClassParser.match_from_span(_child, blob)
                                var_declares[dvar] = dtype
                                break
        return var_declares

    #用于判断某个方法是否是 getter 或 setter。
    @staticmethod
    def is_gs(function_node, fields):
        """
        Judge if a method is getter or setter.
        """
        fields_name = [f['var_name'] for f in fields]
        ret_statements = []
        # check setter
        statements = []
        ClassParser.traverse_type(function_node, statements, 'assignment_expression')
        for statement in statements:
            for child in statement.children:
                if child.type == "field_access" and (child.next_sibling is not None) and child.next_sibling.type == "=":
                    return True
        # check getter
        ClassParser.traverse_type(function_node, ret_statements, 'return_statement')
        for ret_statement in ret_statements:
            for child in ret_statement.children:
                if child.type == "return":
                    ret_val = child.next_named_sibling
                    if (ret_val is not None) and (ret_val.text.decode().lstrip("b'") in fields_name):
                        return True
        return False

    #判断一个方法是否使用了类的字段
    @staticmethod
    def use_fields(function_body_node, fields, blob: str):
        """
        If the method use any fields of the class.
        """
        if function_body_node is None:  # this function has no block
            return False
        fields_access_node = []
        ClassParser.traverse_type(function_body_node, fields_access_node, "field_access")
        if len(fields_access_node) != 0:
            return True

        fields_name = [f['var_name'] for f in fields]
        id_list = []
        ClassParser.traverse_type(function_body_node, id_list, 'identifier')
        for id_node in id_list:
            id = ClassParser.match_from_span(id_node, blob)
            if id in fields_name:
                return True
        return False

    #parse_parameters 方法用于解析方法的参数信息，获取参数类型、类信息以及实例与类的对应关系。
    @staticmethod
    def parse_parameters(param_node, blob: str):
        """
        Get parameter's type, classes, instance&type lists
        in the focal method's parameters.
        """
        param_list = []
        d_class_list = []
        instance2Class = {}
        for child in param_node.named_children:
            class_index = 0
            instance_index = 1
            if 'final' in ClassParser.match_from_span(child.named_children[0], blob):
                class_index = 1
                instance_index = 2
            class_name = ClassParser.match_from_span(child.named_children[class_index], blob)
            if not class_name.islower():  # class type
                d_class_list.append(class_name)
            param_list.append(class_name)
            class_instance = ClassParser.match_from_span(child.named_children[instance_index], blob)
            instance2Class[class_instance] = class_name
        return param_list, d_class_list, instance2Class

    #get_method_names 方法用于提取一个文件中定义的所有方法名称
    def get_method_names(self, file):
        """
        Extract the list of method names defined in a file
        """

        # Build Tree
        with open(file, 'r') as content_file:
            content = content_file.read()
            self.content = content
        tree = self.parser.parse(bytes(content, "utf8"))
        classes = (node for node in tree.root_node.children if node.type == 'class_declaration')

        # Method names
        method_names = list()

        # Class
        for _class in classes:
            # Iterate methods
            for child in (child for child in _class.children if child.type == 'class_body'):
                for _, node in enumerate(child.children):
                    if node.type == 'method_declaration':
                        if not ClassParser.is_method_body_empty(node):
                            # Method Name
                            method_name = ClassParser.get_function_name(node, content)
                            method_names.append(method_name)

        return method_names

    #方法用于从给定的函数节点中提取函数（方法）名称
    @staticmethod
    def get_function_name(function_node, blob: str):
        """
        Extract method name
        """
        declarators = []
        ClassParser.traverse_type(function_node, declarators, '{}_declaration'.format(function_node.type.split('_')[0]))
        for n in declarators[0].children:
            if n.type == 'identifier':
                return ClassParser.match_from_span(n, blob).strip('(')

    #用于从给定的代码节点（语法树节点）中提取对应的源代码部分。
    @staticmethod
    def match_from_span(node, blob: str) -> str:
        """
        Extract the source code associated with a node of the tree
        """
        line_start = node.start_point[0]
        line_end = node.end_point[0]
        char_start = node.start_point[1]
        char_end = node.end_point[1]
        lines = blob.split('\n')
        if line_start != line_end:
            return '\n'.join(
                [lines[line_start][char_start:]] + lines[line_start + 1:line_end] + [lines[line_end][:char_end]])
        else:
            return lines[line_start][char_start:char_end]

    #用于遍历语法树中的节点，查找并收集特定类型的节点
    @staticmethod
    def traverse_type(node, results: List, kind: str) -> None:
        """
        Traverses nodes of given type and save in results
        """
        if node.type == kind:
            results.append(node)
        if not node.children:
            return
        for n in node.children:
            ClassParser.traverse_type(n, results, kind)

    #用于检查给定的函数（或构造函数）是否为空。
    @staticmethod
    def is_method_body_empty(node):
        """
        Check if the body of a method is empty
        """
        for c in node.children:
            if c.type in {'method_body', 'constructor_body'}:
                if c.start_point[0] == c.end_point[0]:
                    return True
    #用于返回某个节点（node）的子节点中，类型属于给定的 types 的子节点。
    @staticmethod
    def children_of_type(node, types):
        """
        Return children of node of type belonging to types

        Parameters
        ----------
        node : tree_sitter.Node
            node whose children are to be searched
        types : str/tuple
            single or tuple of node types to filter

        Return
        ------
        result : list[Node]
            list of nodes of type in types
        """
        if isinstance(types, str):
            return ClassParser.children_of_type(node, (types,))
        return [child for child in node.children if child.type in types]
