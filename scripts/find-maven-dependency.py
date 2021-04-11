#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import pathlib
import argparse
# Python3自带的ElementTree需要自己硬编码name space
# https://stackoverflow.com/questions/14853243/parsing-xml-with-namespace-in-python-via-elementtree
from lxml import etree
from queue import Queue
from queue import LifoQueue

need_find_group_id = ''
need_find_artifact_id = ''

# 解析指定maven依赖在本地仓库中路径


def resolve_jar_pom_location(group_id: str, artifact_id: str, version: str) -> str:
    return "/~/.m2/repo/" + group_id + "/" + artifact_id + "/" + version + "/" + artifact_id + "-" + version + ".pom"


def get_group_id(xml_root) -> str:
    return xml_root.find("groupId", xml_root.nsmap).text


def get_artifact_id(xml_root) -> str:
    return xml_root.find('artifactId', xml_root.nsmap).text


def get_version(xml_root) -> str:
    version_node = xml_root.find('version', xml_root.nsmap)
    if version_node is None:
        return None
    return version_node.text


def generate_module_id(xml_root) -> str:
    return get_group_id(xml_root) + ":" + get_artifact_id(xml_root)


def parse_dependency(module_path, dependency, node_name, args):
    group_id = dependency.getElementsByTagName("groupId")[0].childNodes[0].data
    artifact_id = dependency.getElementsByTagName(
        "artifactId")[0].childNodes[0].data
    version = ''
    version_node = dependency.getElementsByTagName("version")
    if version_node:
        version = version_node[0].childNodes[0].data
    if group_id == args.groupId and artifact_id == args.artifactId:
        print("在路径: %s下发现对指定依赖的引用." % (
            module_path + ":" + node_name + ":" + group_id + ":" + artifact_id + ":" + version))

    # 找到在maven仓库中jar包的位置
    if not version:
        # dependency没有设置version，不进行jar包解析，此时可能是在父module中设置的版本
        return
    jar_pom_location = resolve_jar_pom_location(group_id, artifact_id, version)
    jar_path = pathlib.Path(jar_pom_location)
    if not jar_path.exists() or jar_path.is_dir():
        raise Exception("Jar pom路径: %s不存在或者是个目录" % jar_path)
    jar_pom_tree = xml.dom.minidom.parse(jar_path.open())
    parse_module_dependencies(jar_pom_tree, args, "")


def resolve_parent_pom_path(parent_node):
    group_id = get_group_id(parent_node)
    artifact_id = get_artifact_id(parent_node)
    version = get_version(parent_node)
    group_id = group_id.replace(".", "/")
    pom_path = "/Users/zhaoxudong/.m2/repo/" + group_id + "/" + artifact_id + \
        "/" + version + "/" + artifact_id + "-" + version + ".pom"
    pom = pathlib.Path(pom_path)
    if (not pom.exists()) or pom.is_dir():
        raise Exception("Pom: %s不存在或者是一个目录" % pom_path)
    return etree.parse(pom.open()).getroot()


def parse_properties(xml_root) -> {}:
    result = {}
    properties_node = xml_root.find("properties", xml_root.nsmap)
    if properties_node is None:
        return result
    properties = properties_node.findall('*', xml_root.nsmap)
    for node in properties:
        # 移除tag前的namespace:
        # https://stackoverflow.com/questions/18159221/remove-namespace-and-prefix-from-xml-in-python-using-lxml
        result[etree.QName(node).localname] = node.text
    return result


class _PomNode:

    def __init__(self, pom_dom_tree, pom_base_dir: str, id: str):
        self.pom_dom_tree = pom_dom_tree
        self.pom_base_dir = pom_base_dir
        self.parent_pom = None
        self.children_pom = list()
        self.level = 0
        self.id = id
        self.dependency_managements = None
        self.properties = None


# 解析Maven pom中${}属性引用
def try_parse_property_reference(properties: {}, version: str) -> str:
    if version is None:
        return None
    if version.startswith("${"):
        property_key = version[2:len(version) - 1]
        if property_key not in properties.keys():
            raise Exception("版本: {version}未找到".format(version=property_key))
        return properties[property_key]
    return version


# 按照依赖顺序自顶向下解析各module
def parse_module_tree(tree_root: _PomNode):
    # 广度优先遍历
    node_list = [tree_root]
    while len(node_list) > 0:
        new_node_list = list()
        for node in node_list:
            new_node_list.extend(node.children_pom)
            if node.dependency_managements is None:
                node.dependency_managements = {}
                if node.parent_pom is not None:
                    node.dependency_managements.update(
                        node.parent_pom.dependency_managements)
            if node.properties is None:
                node.properties = parse_properties(node.pom_dom_tree)
                if node.parent_pom is not None:
                    node.properties.update(node.parent_pom.properties)

            dependency_managent_node = node.pom_dom_tree.find(
                "dependencyManagent", node.pom_dom_tree.nsmap)
            if dependency_managent_node is not None:
                dependencies_node = dependency_managent_node.find(
                    "dependencies", node.pom_dom_tree.nsmap)
                if dependencies_node is not None:
                    for dependency in dependencies_node.findall('dependency', node.pom_dom_tree.nsmap):
                        group_id = get_group_id(dependency)
                        artifact_id = get_artifact_id(dependency)
                        version = try_parse_property_reference(
                            get_version(dependency))
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
                version = try_parse_property_reference(
                    node.properties, get_version(dependency))
                dependency_key = group_id + ":" + artifact_id
                if version is None:
                    # 没有填version，那么只可能是(合法的情况)依靠父级pom的dependencyManagement指定版本
                    if dependency_key not in node.dependency_managements.keys():
                        raise Exception("依赖: {dependency}没有版本".format(
                            dependency=dependency_key))
                    version = node.dependency_managements[dependency_key]
                global need_find_artifact_id
                global need_find_group_id
                if group_id == need_find_group_id and artifact_id == need_find_artifact_id:
                    print("在{id}的dependencies中发现给定依赖, 版本: {version}".format(
                        id=node.id, version=version))
        node_list = new_node_list


# 按照pom继承关系构建树型关系
def build_module_tree(base_dir: str) -> _PomNode:
    pom_path = base_dir + "/pom.xml"
    pom_file = pathlib.Path(pom_path)
    if not pom_file.exists() or pom_file.is_dir():
        raise Exception("路径: %s不是一个合法的pom.xml文件" % pom_path)
    xml_root = etree.parse(pom_file.open()).getroot()

    pom_node = _PomNode(xml_root, base_dir, generate_module_id(xml_root))
    child_parent_node = pom_node

    parent_dom_node = xml_root.find("parent", xml_root.nsmap)
    while parent_dom_node is not None:
        parent_pom_dom_tree = resolve_parent_pom_path(parent_dom_node)
        node = _PomNode(parent_pom_dom_tree, '',
                        generate_module_id(parent_pom_dom_tree))
        pom_node.parent_pom = node
        node.children_pom.append(pom_node)
        pom_node = node
        parent_dom_node = parent_pom_dom_tree.find(
            "parent", parent_pom_dom_tree.nsmap)

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
            node.parent_pom = parent_node
            parent_node.children_pom.append(node)
            queue.put(node)

    # 从树的根节点开始广度优先遍历，标记每层的level
    i = 0
    node_list = [pom_node]
    while len(node_list) > 0:
        new_node_list = list()
        for node in node_list:
            node.level = i
            new_node_list.extend(node.children_pom)
        node_list = new_node_list
        i = i + 1

    return pom_node


def generate_padding_spaces(level: int) -> str:
    result = ''
    for x in range(level):
        result = result + '  '
    return result


def main():
    arg_parser = argparse.ArgumentParser(description="maven依赖查找")
    arg_parser.add_argument('-p', help='maven工程绝对路径', type=str, dest='path')
    arg_parser.add_argument('-m', help='maven module', type=str, dest='module')
    arg_parser.add_argument('-g', help='group id', type=str, dest='groupId')
    arg_parser.add_argument('-a', help='artifact id',
                            type=str, dest='artifactId')
    args = arg_parser.parse_args()

    if not args.groupId:
        print("必须指定搜索的group id!")
        return
    global need_find_group_id
    need_find_group_id = args.groupId

    if not args.artifactId:
        print("必须指定搜索的artifact id!")
        return
    global need_find_artifact_id
    need_find_artifact_id = args.artifactId

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

    parse_module_tree(tree_head)


main()
