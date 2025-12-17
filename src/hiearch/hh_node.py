"""Module for handling hiearch nodes and their processing."""

import copy
from collections import defaultdict

from . import util


def gather(prop, node, must_exist_nodes):
    """Gather nodes that must exist based on property references."""
    if prop in node.keys() and node[prop] is not None:
        if isinstance(node[prop], list):
            must_exist_nodes = must_exist_nodes.union(set(node[prop]))
        else:
            must_exist_nodes.add(node[prop])
        return True
    return False


def postprocess(nodes, edges):
    """Post-process nodes after parsing."""
    util.check_key_existence(nodes.must_exist, nodes.entities, 'node')
    util.apply_styles(nodes.styled, nodes.entities)

    for node in nodes.entities.values():
        node['out'] = set()
        node['in'] = set()
        node['child_out'] = set()
        node['child_in'] = set()

        original_scope = node['scope']
        if original_scope is not None:
            if isinstance(original_scope, list):
                node['scope'] = set(original_scope)

                if len(original_scope) != len(node['scope']):
                    raise RuntimeError(f'Duplicate scopes: {node["label"]} | scopes: [{original_scope}] | [{node["scope"]}]')
            else:
                node['scope'] = set([original_scope])

    for key, edge in edges.items():
        for dir_key in ['in', 'out']:
            nodes.entities[edge[dir_key]][dir_key].add(key)


def add_branch_to_tree(branch, tree, node_key_paths, scopes, index=0):
    """Add a branch to the tree structure recursively."""
    if index != len(branch):
        node_key = branch[index]
        if index + 1 < len(branch):
            if node_key in scopes:
                scopes[node_key].add(branch[index + 1])
            else:
                scopes[node_key] = set([branch[index + 1]])

        if len(tree) > 0 and node_key in tree.keys():
            tree[node_key] = {
                    'subtree': add_branch_to_tree(branch, tree[node_key]['subtree'], node_key_paths, scopes, index + 1),
                    'key_path': tree[node_key]['key_path']
            }
        else:
            tree[node_key] = {
                    'subtree': add_branch_to_tree(branch, {}, node_key_paths, scopes, index + 1),
                    'key_path': '.'.join(branch[:index + 1])
            }

        node_key_paths[node_key].add(tree[node_key]['key_path'])

    return tree


def build_tree(nodes, nodes_view):
    """Build the tree structure from nodes and view information."""
    rank = defaultdict(lambda: 0)

    branches = defaultdict(lambda: [])
    branch = [None]
    scope_stack = [set(nodes_view)]

    nonleaf = set()

    while len(scope_stack) > 0:
        branch.pop()
        updated_branch = False
        while scope_stack[-1] is not None and len(scope_stack[-1]) > 0:
            scope = scope_stack[-1].pop()

            if scope in branch:
                raise RuntimeError(f'Detected cycle in branch: {branch} | {scope}')
            if scope in nodes_view:
                rank['scope'] += 1
                updated_branch = True
                branch.append(scope)
                if len(branch) > 1:
                    nonleaf.add(scope)

                scope_stack.append(copy.deepcopy(nodes[scope]['scope']))

        if updated_branch:
            branches[branch[0]].append(copy.deepcopy(branch))

        scope_stack.pop()


    scopes = {}
    node_tree = {}
    node_key_paths = defaultdict(set)
    for key, branch_list in branches.items():
        # a node may appear both as a leaf and nonleaf in a view with
        # multiscoping, in such cases we should omit the leaf due to
        # redundancy
        if key in nonleaf:
            continue

        branch = branch_list[0]
        for branch_merge in branch_list[1:]:
            index = 0
            for node in branch_merge:
                # if we reached the end of the original branch, or the nodes do not match
                # find a place where the node must be inserted
                if index == len(branch) or node != branch[index]:
                    while index < len(branch) and rank[node] > rank[branch[index]]:
                        index += 1
                    if rank[node] == rank[branch[index]] and node > branch[index]:
                        index += 1
                    branch.insert(index, node)
                index += 1

        branch.reverse()
        node_tree = add_branch_to_tree(branch, node_tree, node_key_paths, scopes)


    return node_tree, node_key_paths, scopes


def parse(yaml_nodes, nodes):
    """Parse YAML node definitions and populate the nodes structure."""
    default = {
        'id': ['', ''],
        'scope': None,
        'style': None,
        'style_notag': None,
        'graphviz': {},
        'tags': ['default'],
        'substitutions': {},
        # overriden
        'label': '',
        'in': [],
        'out': [],
        'child_in': [],
        'child_out': [],
    }

    for node in yaml_nodes:
        node['label'] = node['id'][0]
        node['id'] = node['id'][1]
        key = node['id']
        if key in nodes.entities.keys():
            raise RuntimeError(f'Duplicate node id: {key}')

        gather('scope', node, nodes.must_exist)

        has_style = gather('style', node, nodes.must_exist)
        has_style_notag = gather('style_notag', node, nodes.must_exist)

        if has_style and has_style_notag:
            raise RuntimeError(f'Node {key} cannot have both style and style_notag attributes')

        if has_style or has_style_notag:
            nodes.styled.append(node)
            nodes.entities[key] = node
        else:
            nodes.entities[key] = util.merge_styles(default, node)


def get_substitutions(node):
    """Get substitution values for formatting node labels."""
    substitutions = node['substitutions'] | {
        'label': node['label'],
        'id': node['id'],
        'scope': node['scope'],
        'style': node['style']
    }
    return substitutions


def get_nodes_by_tag(nodes, tag):
    """Get all nodes that have a specific tag."""
    selection = []
    for node in nodes.values():
        if tag in node['tags']:
            selection.append(node['id'])
    return set(selection)
