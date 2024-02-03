#!/usr/bin/python3
# -*- coding: UTF-8 -*-

def check_packages():
    try:
        exec("import lxml")
    except ModuleNotFoundError:
        print("此脚本依赖lxml库, 尝试执行命令: 'pip3 install lxml'.")
        exit(0)

check_packages()

import pathlib
import argparse
# Python3自带的ElementTree需要自己硬编码name space
# https://stackoverflow.com/questions/14853243/parsing-xml-with-namespace-in-python-via-elementtree
from lxml import etree
from queue import Queue
from queue import LifoQueue
import os

# 全局变量
need_find_group_id = ''
need_find_artifact_id = ''
debug_enabled = False
maven_repo = ''


def is_debug_enabled() -> bool:
    global debug_enabled
    return debug_enabled


# 解析指定maven依赖在本地仓库中路径
def resolve_jar_pom_location(group_id: str, artifact_id: str, version: str) -> str:
    group_id = group_id.replace(".", "/")
    global maven_repo
    return maven_repo + "/" + group_id + "/" + artifact_id + "/" + version + "/" + artifact_id + "-" + version + ".pom"


def get_group_id(xml_root) -> str:
    group_id_node = xml_root.find("groupId", xml_root.nsmap)
    # group id不是必填的，可以从parent那里继承
    # https://maven.apache.org/pom.html
    if group_id_node is None:
        parent_node = xml_root.find("parent", xml_root.nsmap)
        if parent_node is None:
            raise Exception("未设置group id, 同时也没有设置parent")
        group_id_node = parent_node.find("groupId", xml_root.nsmap)
        if group_id_node is None:
            raise Exception("未设置group id, 同时parent内也没有指定")
    return group_id_node.text


def get_artifact_id(xml_root) -> str:
    return xml_root.find('artifactId', xml_root.nsmap).text


def get_version(xml_root) -> str:
    version_node = xml_root.find('version', xml_root.nsmap)
    if version_node is None:
        return None
    return version_node.text


def generate_module_id(xml_root) -> str:
    return get_group_id(xml_root) + ":" + get_artifact_id(xml_root)


class _PomNode:

    # 如果为True, 表示当前pom为工作目录的pom, 其它pom均为间接依赖的pom
    is_current_pom = False

    def __init__(self, pom_dom_tree, pom_base_dir: str, id: str):
        self.pom_dom_tree = pom_dom_tree
        self.pom_base_dir = pom_base_dir
        self.parent_pom = None
        self.children_pom = list()
        self.level = 0
        self.id = id
        self.dependency_managements = None
        self.properties = None
        # 和起始module的关系路径
        self.context_path = ''


def build_module_tree_parent(init_node, init_base_dir: str = '', init_context_path: str = None) -> _PomNode:
    pom_node = _PomNode(init_node, '', generate_module_id(init_node))
    pom_node.pom_base_dir = init_base_dir

    if init_context_path is None:
        pom_node.context_path = pom_node.id
    else:
        pom_node.context_path = init_context_path

    parent_node = init_node.find("parent", init_node.nsmap)
    while parent_node is not None:
        parent_pom_tree = resolve_parent_pom_path(parent_node)
        node = _PomNode(parent_pom_tree, '',
                        generate_module_id(parent_pom_tree))
        node.context_path = node.id + " -> " + pom_node.context_path
        node.children_pom.append(pom_node)
        pom_node.parent_pom = node
        pom_node = node
        parent_node = parent_pom_tree.find("parent", parent_pom_tree.nsmap)
    return pom_node


def inherit_properties(children: {}, parent: {}):
    for key in parent:
        if key in children.keys():
            continue
        children[key] = parent[key]


# 按照依赖顺序自顶向下解析各module
def parse_module_tree(tree_root: _PomNode, exclusions=set(), dependency_parsed=set()):
    # 广度优先遍历
    node_list = [tree_root]
    while len(node_list) > 0:
        new_node_list = list()
        for node in node_list:
            new_node_list.extend(node.children_pom)
            if node.dependency_managements is None:
                node.dependency_managements = {}
                if node.parent_pom is not None:
                    inherit_properties(
                        node.dependency_managements, node.parent_pom.dependency_managements)
            if node.properties is None:
                node.properties = parse_properties(node.pom_dom_tree)
                if node.parent_pom is not None:
                    inherit_properties(
                        node.properties, node.parent_pom.properties)

            dependency_managment_node = node.pom_dom_tree.find(
                "dependencyManagement", node.pom_dom_tree.nsmap)
            if dependency_managment_node is not None:
                dependencies_node = dependency_managment_node.find(
                    "dependencies", node.pom_dom_tree.nsmap)
                if dependencies_node is not None:
                    for dependency in dependencies_node.findall('dependency', node.pom_dom_tree.nsmap):
                        group_id = get_group_id(dependency)
                        artifact_id = get_artifact_id(dependency)
                        scope_legal, scope = is_scope_transitive(dependency)
                        if not scope_legal:
                            if is_debug_enabled():
                                print("Dependency management: {dependency}的scope为{scope}, 跳过, context: {context}.".format(
                                    dependency=(group_id + ":" + artifact_id), scope=scope, context=node.context_path))
                            continue
                        version = try_parse_property_reference(
                            node.properties, get_version(dependency))
                        # dependency managent的版本是可以不填的
                        node.dependency_managements[group_id +
                                                    ":" + artifact_id] = version

            # 正经的dependencies
            dependencies_node = node.pom_dom_tree.find(
                "dependencies", node.pom_dom_tree.nsmap)
            if dependencies_node is None:
                continue
            for dependency in dependencies_node.findall("dependency", node.pom_dom_tree.nsmap):
                group_id = get_group_id(dependency)
                artifact_id = get_artifact_id(dependency)
                dependency_key = group_id + ":" + artifact_id
                if dependency_key in exclusions:
                    if is_debug_enabled():
                        print("依赖:[{dependency}]已被排除, context: {context}".format(
                            dependency=dependency_key, context=node.context_path))
                    continue
                version = try_parse_property_reference(
                    node.properties, get_version(dependency))
                if version is None:
                    # 没有填version，那么只可能是(合法的情况)依靠父级pom的dependencyManagement指定版本
                    if dependency_key not in node.dependency_managements.keys():
                        if is_debug_enabled():
                            print("依赖: {dependency_key}没有设置版本, context: {context}".format(
                                dependency_key=dependency_key, context=node.context_path))
                        continue
                    version = node.dependency_managements[dependency_key]
                parse_dependency(
                    dependency, version, node.context_path, exclusions, dependency_parsed, node.is_current_pom)
        node_list = new_node_list


def is_scope_transitive(xml_root):
    scope_node = xml_root.find("scope", xml_root.nsmap)
    if scope_node is None:
        return True, None
    
    scope = scope_node.text
    if scope == 'system':
        raise Exception("暂不支持scope为system的依赖")

    return scope == 'compile' or scope == 'runtime', scope


# 解析一个dependencies中的依赖, 这里还要考虑依赖中的依赖
def parse_dependency(dependency, version: str, context_path: str, exclusions=set(), dependency_parsed=set(), is_in_current_pom = False):
    group_id = get_group_id(dependency)
    artifact_id = get_artifact_id(dependency)
    scope_transitive, scope = is_scope_transitive(dependency)

    if not is_in_current_pom and not scope_transitive:
        if is_debug_enabled():
            print("间接依赖: {groupId}:{artifactId}:{version}的scope = {scope}, 跳过.".format(
                groupId=group_id, artifactId=artifact_id, version=version, scope=scope))
        return

    optional_node = dependency.find("optional", dependency.nsmap)
    if not is_in_current_pom and optional_node is not None and optional_node.text == 'true':
        if is_debug_enabled():
            print("间接依赖: {groupId}:{artifactId}:{version}的optional = true, 跳过.".format(
                groupId=group_id, artifactId=artifact_id, version=version))
        return

    parsed_key = group_id + ":" + artifact_id + ":" + version
    if parsed_key in dependency_parsed:
        return

    global need_find_group_id
    global need_find_artifact_id
    if group_id == need_find_group_id and artifact_id == need_find_artifact_id:
        print("发现引用: [{context_path}]: {group_id}:{artifact_id}:{version}".format(
            context_path=context_path, group_id=group_id, artifact_id=artifact_id, version=version))

    jar_pom_location = resolve_jar_pom_location(group_id, artifact_id, version)
    jar_path = pathlib.Path(jar_pom_location)
    if not jar_path.exists() or jar_path.is_dir():
        print("Jar pom: {path}不存在或者是个目录, 可能此依赖被maven排除了.".format(
            path=jar_pom_location))
        return
    jar_pom_tree = etree.parse(jar_path.open()).getroot()

    # 解析exclusions
    exclusions_new = exclusions.copy()
    exclusions_node = dependency.find("exclusions", dependency.nsmap)
    if exclusions_node is not None:
        exclusion_nodes = exclusions_node.findall(
            "exclusion", dependency.nsmap)
        for exclusion_node in exclusion_nodes:
            group_id = get_group_id(exclusion_node)
            artifact_id = get_artifact_id(exclusion_node)
            exclusions_new.add(group_id + ":" + artifact_id)

    # 构建依赖的jar包的依赖树，和主module的依赖树没有关系
    jar_context_path = "{context_path} -> jar[{group_id}:{artifact_id}:{version}]".format(
        group_id=group_id, artifact_id=artifact_id, version=version,
        context_path=context_path
    )
    tree_root = build_module_tree_parent(
        jar_pom_tree, init_context_path=jar_context_path)
    dependency_parsed.add(parsed_key)
    parse_module_tree(tree_root, exclusions=exclusions_new,
                      dependency_parsed=dependency_parsed)


def resolve_parent_pom_path(parent_node):
    group_id = get_group_id(parent_node)
    artifact_id = get_artifact_id(parent_node)
    version = get_version(parent_node)
    group_id = group_id.replace(".", "/")
    global maven_repo
    pom_path = maven_repo + "/" + group_id + "/" + artifact_id + \
        "/" + version + "/" + artifact_id + "-" + version + ".pom"
    pom = pathlib.Path(pom_path)
    if (not pom.exists()) or pom.is_dir():
        raise Exception("Pom: %s不存在或者是一个目录" % pom_path)
    return etree.parse(pom.open()).getroot()


def parse_properties(xml_root) -> {}:
    result = {}
    # 特殊处理project.version
    version_node = xml_root.find("version", xml_root.nsmap)
    if version_node is not None:
        result['project.version'] = version_node.text
    properties_node = xml_root.find("properties", xml_root.nsmap)
    if properties_node is None:
        return result
    properties = properties_node.findall('*', xml_root.nsmap)
    for node in properties:
        # 移除tag前的namespace:
        # https://stackoverflow.com/questions/18159221/remove-namespace-and-prefix-from-xml-in-python-using-lxml
        result[etree.QName(node).localname] = node.text
    return result


# 解析Maven pom中${}属性引用
def try_parse_property_reference(properties: {}, version: str) -> str:
    if version is None:
        return None
    # 可能存在属性引用嵌套的情况
    while version.startswith("${"):
        property_key = version[2:len(version) - 1]
        if property_key not in properties.keys():
            return None
        version = properties[property_key]
    return version


# 按照pom继承关系构建树型关系
def build_module_tree(base_dir: str) -> _PomNode:
    pom_path = base_dir + "/pom.xml"
    pom_file = pathlib.Path(pom_path)
    if not pom_file.exists() or pom_file.is_dir():
        raise Exception("路径: %s不是一个合法的pom.xml文件" % pom_path)
    xml_root = etree.parse(pom_file.open()).getroot()

    tree_root = build_module_tree_parent(xml_root, base_dir)
    child_parent_node = tree_root
    while len(child_parent_node.children_pom) == 1:
        child_parent_node = child_parent_node.children_pom[0]

    child_parent_node.is_current_pom = True

    # 向下再根据子module构建pom tree
    queue = Queue()
    queue.put(child_parent_node)
    while not queue.empty():
        parent_node = queue.get()
        modules_dom_node = parent_node.pom_dom_tree.find(
            "modules", parent_node.pom_dom_tree.nsmap)
        if modules_dom_node is None:
            break
        for module_node in modules_dom_node.findall("module", modules_dom_node.nsmap):
            module_pom_dir = parent_node.pom_base_dir + "/" + module_node.text
            module_pom_path = module_pom_dir + "/pom.xml"
            module_pom_file = pathlib.Path(module_pom_path)
            if not module_pom_file.exists() or module_pom_file.is_dir():
                raise Exception("子module pom: %s不存在或者是一个目录" % module_pom_path)
            module_dom_tree = etree.parse(module_pom_file.open()).getroot()
            node = _PomNode(module_dom_tree, module_pom_dir,
                            generate_module_id(module_dom_tree))
            node.context_path = parent_node.context_path + " -> " + node.id
            node.parent_pom = parent_node
            parent_node.children_pom.append(node)
            queue.put(node)

    # 从树的根节点开始广度优先遍历，标记每层的level
    i = 0
    node_list = [tree_root]
    while len(node_list) > 0:
        new_node_list = list()
        for node in node_list:
            node.level = i
            new_node_list.extend(node.children_pom)
        node_list = new_node_list
        i = i + 1

    return tree_root


def generate_padding_spaces(level: int) -> str:
    result = ''
    for x in range(level):
        result = result + '  '
    return result


def main():
    global debug_enabled
    global need_find_group_id
    global need_find_artifact_id
    global maven_repo

    arg_parser = argparse.ArgumentParser(description="maven依赖查找")
    arg_parser.add_argument(
        '-p', help='maven工程绝对路径, 可选, 不设置则使用当前目录', type=str, dest='path')
    arg_parser.add_argument(
        '-r', help='maven repo path, 可选, 不设置则读取[$HOME/.m2/settings.xml]以决定仓库位置', type=str, dest='repo')
    arg_parser.add_argument('-g', help='group id', type=str, dest='groupId')
    arg_parser.add_argument('-a', help='artifact id',
                            type=str, dest='artifactId')
    arg_parser.add_argument("-X", help='debug模式',
                            dest='debug', action='store_true')
    args = arg_parser.parse_args()

    if args.debug:
        debug_enabled = True

    if not args.groupId:
        print("必须指定搜索的group id!")
        return
    need_find_group_id = args.groupId

    if not args.artifactId:
        print("必须指定搜索的artifact id!")
        return
    need_find_artifact_id = args.artifactId

    if args.repo is not None:
        maven_repo = args.repo
    else:
        # 尝试解析maven默认配置文件获取repo目录
        home_path = os.getenv("HOME")
        default_maven_setting_path = home_path + "/.m2/settings.xml"
        default_maven_setting_file = pathlib.Path(default_maven_setting_path)
        if not default_maven_setting_file.exists or default_maven_setting_file.is_dir():
            print("maven配置文件: %s不存在或者是一个目录." % default_maven_setting_path)
            return
        default_maven_setting_tree = etree.parse(
            default_maven_setting_file.open()).getroot()
        local_repo_node = default_maven_setting_tree.find(
            "localRepository", default_maven_setting_tree.nsmap)
        if local_repo_node is not None:
            local_repo_path = local_repo_node.text
        else:
            local_repo_path = home_path + "/.m2/repository"
        maven_repo = local_repo_path

    path = args.path
    if path is None:
        base_dir = '.'
    else:
        base_dir = path

    try:
        tree_head = build_module_tree(base_dir)
    except Exception as e:
        print("依赖查询失败: {reason}".format(reason=str(e)))
        return

    if is_debug_enabled():
        print("主Module继承关系: ")
        stack = LifoQueue()
        stack.put(tree_head)
        while not stack.empty():
            node = stack.get()
            print("{padding}{groupId}:{artifactId}".format(
                padding=generate_padding_spaces(node.level),
                groupId=get_group_id(node.pom_dom_tree),
                artifactId=get_artifact_id(node.pom_dom_tree))
            )
            for childNode in node.children_pom:
                stack.put(childNode)
        print("------------------------------------------")

    try:
        parse_module_tree(tree_head)
    except Exception as e:
        print("依赖查询失败: {reason}".format(reason=str(e)))

main()
