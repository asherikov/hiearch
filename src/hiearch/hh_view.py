"""Module for handling hiearch views and their processing."""

import copy
from collections import deque

from . import hh_edge
from . import hh_node
from . import util


class Neighbours():
    """Class defining the different types of neighbor selection for views."""
    DIRECT = 'direct'
    DIRECT_WITH_PARENTS = 'direct_with_parents'
    EXPLICIT = 'explicit'
    PARENT = 'parent'
    RECURSIVE_IN = 'recursive_in'
    RECURSIVE_OUT = 'recursive_out'
    RECURSIVE_ALL = 'recursive_all'

    types = [DIRECT, DIRECT_WITH_PARENTS, EXPLICIT, PARENT, RECURSIVE_IN, RECURSIVE_OUT, RECURSIVE_ALL]



default: dict = {
    'id': 'default',
    'nodes': None,
    'neighbours': Neighbours.EXPLICIT,
    'graphviz': {},
    'style': None,
    'tags': set(),
    'edge_tags': set(),
    'edges': {},
    'custom_edges': {},
    'tree': {},
    'expand': [],
    'nodes_subset': {},
    'expanded_from': {},
}


opposite = {
    'in': 'out',
    'out': 'in',
}


def select_explicit(view, nodes, edges):
    """Select edges that connect explicitly requested nodes."""
    for node_key in view['nodes']:
        for dir_key in ['in', 'out']:
            for edge_key in nodes[node_key][dir_key]:
                if edge_key not in edges:
                    continue
                if edges[edge_key][opposite[dir_key]] in view['nodes']:
                    view['edges'][edge_key] = copy.deepcopy(edges[edge_key])


def select_direct(view, nodes, edges, add_nodes):
    """Select edges that connect directly to requested nodes."""
    for node_key in view['nodes']:
        for dir_key in ['in', 'out']:
            opp_dir_key = opposite[dir_key]
            for edge_key in nodes[node_key][dir_key]:
                if edge_key not in edges:
                    continue
                if edges[edge_key][opp_dir_key] in nodes:
                    view['edges'][edge_key] = copy.deepcopy(edges[edge_key])

    for edge_key in view['edges']:
        for dir_key in ['in', 'out']:
            add_nodes.add(edges[edge_key][dir_key])


def select_direct_with_parents(view, nodes, edges, add_nodes):
    """Select directly connected nodes and all their parent scopes."""
    select_direct(view, nodes, edges, add_nodes)

    to_process = set(add_nodes)
    while to_process:
        node_key = to_process.pop()
        node = nodes[node_key]
        while node['scope'] is not None:
            next_scope = None
            for scope_id in node['scope']:
                if scope_id in nodes and scope_id not in add_nodes:
                    add_nodes.add(scope_id)
                    if next_scope is None:
                        next_scope = scope_id
                    else:
                        to_process.add(scope_id)
            if next_scope is not None:
                node = nodes[next_scope]
            else:
                break


def select_parent(view, nodes, edges, add_nodes):
    """Select parent nodes and edges that connect to them."""
    for node_key in view['nodes']:
        for dir_key in ['in', 'out']:
            opp_dir_key = opposite[dir_key]
            for edge_key in nodes[node_key][dir_key]:
                if edge_key not in edges:
                    continue
                nodes_to_explore = set([edges[edge_key][opp_dir_key]])

                while len(nodes_to_explore) > 0:
                    scope_node_key = nodes_to_explore.pop()
                    if scope_node_key not in nodes:
                        continue

                    # go up the tree until reached an explicitly requested or a root node
                    while scope_node_key not in view['nodes'] and nodes[scope_node_key]['scope'] is not None:
                        scope_copy = copy.deepcopy(nodes[scope_node_key]['scope'])
                        scope_node_key = scope_copy.pop()
                        nodes_to_explore = nodes_to_explore.union(scope_copy)

                    if scope_node_key in add_nodes:  # same node can be reached in multiple ways
                        continue

                    add_nodes.add(scope_node_key)
                    if scope_node_key == edges[edge_key][opp_dir_key]:
                        view['edges'][edge_key] = copy.deepcopy(edges[edge_key])
                    else:
                        # generate edge with a parent
                        new_edge = copy.deepcopy(edges[edge_key])
                        new_edge[opp_dir_key] = scope_node_key
                        hh_edge.generate_id(new_edge)
                        view['custom_edges'][new_edge['id']] = new_edge


def select_recursive(view, nodes, edges, add_nodes, direction):
    """Recursively select nodes in a specific direction (in or out)."""
    # Select connected nodes
    add_nodes.update(view['nodes'])
    add_nodes_list = list(view['nodes'])
    index = 0
    original_size = len(add_nodes_list)

    while index < len(add_nodes_list):
        edge_keys = nodes[add_nodes_list[index]][direction]
        for edge_key in edge_keys:
            if edge_key not in edges:
                continue
            if direction == 'in':
                connected_node = edges[edge_key]['out']
            else:
                connected_node = edges[edge_key]['in']

            if connected_node not in nodes:
                continue

            view['edges'][edge_key] = copy.deepcopy(edges[edge_key])

            # Check if connected node is not already selected
            if connected_node not in add_nodes:
                add_nodes_list.append(connected_node)
                add_nodes.add(connected_node)
        index += 1

    # Process parents of the newly selected nodes (excluding the original view nodes)
    index = original_size
    while index < len(add_nodes_list):
        node = nodes[add_nodes_list[index]]
        skip = False
        while node['scope'] is not None and not skip:
            for node_id in node['scope']:
                if node_id not in nodes:
                    skip = True
                    continue

                node = nodes[node_id]
                if node_id not in add_nodes:
                    add_nodes_list.append(node_id)
                    add_nodes.add(node_id)
        index += 1

    add_nodes.difference_update(view['nodes'])


def select_neighbours_for_view(view, nodes, edges):
    """Apply neighbour selection logic to a single view"""
    if 0 == len(view['nodes']):
        return

    view['edges'] = {}
    view['custom_edges'] = {}
    add_nodes = set()

    if Neighbours.EXPLICIT == view['neighbours']:
        select_explicit(view, nodes, edges)

    elif Neighbours.DIRECT == view['neighbours']:
        select_direct(view, nodes, edges, add_nodes)

    elif Neighbours.DIRECT_WITH_PARENTS == view['neighbours']:
        select_direct_with_parents(view, nodes, edges, add_nodes)

    elif Neighbours.PARENT == view['neighbours']:
        select_parent(view, nodes, edges, add_nodes)

    elif Neighbours.RECURSIVE_IN == view['neighbours']:
        select_recursive(view, nodes, edges, add_nodes, 'in')

    elif Neighbours.RECURSIVE_OUT == view['neighbours']:
        select_recursive(view, nodes, edges, add_nodes, 'out')

    elif Neighbours.RECURSIVE_ALL == view['neighbours']:
        select_recursive(view, nodes, edges, add_nodes, 'out')
        select_recursive(view, nodes, edges, add_nodes, 'in')

    else:
        raise RuntimeError(f'Unsupported neighbours type: {view["neighbours"]}, must be one of {Neighbours.types}.')

    if len(add_nodes) > 0:
        view['nodes'] = view['nodes'].union(add_nodes)


def _get_descendants(view_nodes, nodes):
    """Compute descendant ID sets and closest-scope mapping."""
    descendants = {}
    closest_scope = {}
    for node_key in view_nodes:
        closest_scope[node_key] = node_key
        descendants[node_key] = set()
        queue = deque([node_key])
        visited = {node_key}
        while queue:
            curr = queue.popleft()
            for child in nodes[curr]['child']:
                if child not in visited:
                    visited.add(child)
                    descendants[node_key].add(child)
                    queue.append(child)

    sorted_view_nodes = sorted(view_nodes, key=lambda k: len(descendants[k]))
    for node_key in sorted_view_nodes:
        for child in descendants[node_key]:
            if child not in view_nodes and child not in closest_scope:
                closest_scope[child] = node_key
    return descendants, closest_scope


def build_tree(view, nodes, edges):
    """Build tree structure and promote edges between scope nodes.

    When a view contains scope nodes (parents) but not their children, edges
    between those children are automatically promoted to the scope level,
    producing edges between the scope nodes themselves.
    """
    view_nodes = view['nodes']

    descendants, closest_scope = _get_descendants(view_nodes, nodes)

    existing_connections = set()
    for edge in view['edges'].values():
        existing_connections.add((edge['out'], edge['in']))
    for edge in view['custom_edges'].values():
        existing_connections.add((edge['out'], edge['in']))

    for a_node in view_nodes:
        source_nodes = [a_node] + [c for c in descendants[a_node] if c not in view_nodes and closest_scope.get(c) == a_node]
        for b_node in view_nodes:
            if a_node == b_node:
                continue
            if b_node in descendants[a_node] or a_node in descendants[b_node]:
                continue
            if (a_node, b_node) in existing_connections:
                continue

            promoted_edges = []
            for source in source_nodes:
                for edge_key in nodes[source]['out']:
                    if edge_key not in edges:
                        continue
                    edge_data = edges[edge_key]
                    far_node = edge_data['in']
                    if far_node == b_node:
                        promoted_edges.append(edge_key)
                    elif far_node not in view_nodes and far_node in closest_scope and closest_scope[far_node] == b_node:
                        promoted_edges.append(edge_key)
            edge_count = len(promoted_edges)

            if edge_count == 0:
                continue

            if edge_count == 1:
                new_edge = copy.deepcopy(edges[promoted_edges[0]])
            else:
                promoted_tags = set()
                for promoted_key in promoted_edges:
                    promoted_tags.update(edges[promoted_key]['tags'])
                new_edge = copy.deepcopy(hh_edge.default)
                new_edge['tags'] = promoted_tags
                new_edge['label'] = ['', f'({edge_count})', '']
                new_edge['graphviz']['label_format'] = ['{label}', '{label}', '{label}']

            new_edge['out'] = a_node
            new_edge['in'] = b_node
            hh_edge.generate_id(new_edge)
            view['custom_edges'][new_edge['id']] = new_edge
            existing_connections.add((a_node, b_node))

    view['tree'], view['node_key_paths'], view['scopes'] = hh_node.build_tree(nodes, view['nodes'])


def _resolve_view_nodes(views, nodes):
    empty_views_counter = 0
    for view in views.entities.values():
        if view['nodes'] is None:
            view['nodes'] = set()
            if 0 == len(view['tags']):
                view['tags'] = {'default'}
        else:
            num_nodes = len(view['nodes'])
            view['nodes'] = set(view['nodes'])  # set converted to list by | operator in apply_styles()
            if len(view['nodes']) != num_nodes:
                raise RuntimeError(f'Duplicate node ids in view: {view["id"]} | nodes: {view["nodes"]}')

        if not isinstance(view['edge_tags'], set):
            view['edge_tags'] = util.ensure_set(view['edge_tags'])

        if not isinstance(view['tags'], set):
            view['tags'] = util.ensure_set(view['tags'])

        if 0 == len(view['edge_tags']):
            view['edge_tags'] = {'default'}

        for tag in view['tags']:
            view['nodes'] = view['nodes'].union(hh_node.get_nodes_by_tag(nodes, tag))

        if 0 == len(view['nodes']):
            empty_views_counter += 1
            continue

    if empty_views_counter == len(views.entities):
        views.entities['default'] = default
        views.entities['default']['tags'] = {'default'}
        views.entities['default']['nodes'] = hh_node.get_nodes_by_tag(nodes, 'default')
        views.entities['default']['edge_tags'] = {'default'}
        if 0 == len(views.entities['default']['nodes']):
            raise RuntimeError(f'All views are empty: {views.entities.keys()}')


def _expand_views(views, nodes, edges):
    additional_views = {}

    for view_id, view in views.entities.items():
        if not isinstance(view['expand'], list):
            raise RuntimeError(f'Expand field in view "{view_id}" must be an array.')

        if len(view['expand']) == 0:
            continue

        view['expanded_from'] = view_id

        nodes_subset = {}
        for node_id in view['nodes']:
            nodes_subset[node_id] = nodes[node_id]

        for expand_type in view['expand']:
            if expand_type not in ['recursive_in', 'recursive_out', 'recursive_all']:
                raise RuntimeError(f'Unsupported expand type: "{expand_type}" in view "{view_id}".')

            expand_edges = hh_edge.get_edges_by_tags(edges, view['edge_tags'])
            for node_id in view['nodes']:
                new_view_id = f"{view_id}_{node_id}_{expand_type}"
                highlight_scope_id = f"{new_view_id}_highlight_scope"

                nodes[highlight_scope_id] = util.merge_styles(
                        hh_node.default,
                        {
                            'id': highlight_scope_id,
                            'label': '',
                            'graphviz': {
                                'shape': 'rectangle',
                                'color': 'red',
                                'penwidth': '2',
                                'label': '',
                            },
                            'in': set(),
                            'out': set(),
                            'scope': nodes[node_id]['scope']
                        })
                nodes_subset[highlight_scope_id] = nodes[highlight_scope_id]

                new_view = copy.deepcopy(view)
                new_view['id'] = new_view_id
                new_view['nodes'] = set([node_id, highlight_scope_id])
                new_view['neighbours'] = getattr(Neighbours, expand_type.upper())

                original_scope = nodes[node_id]['scope']
                nodes[node_id]['scope'] = set([highlight_scope_id])
                select_neighbours_for_view(new_view, nodes_subset, expand_edges)
                build_tree(new_view, nodes, expand_edges)
                nodes[node_id]['scope'] = original_scope

                additional_views[new_view_id] = new_view

    views.entities.update(additional_views)


def postprocess(views, nodes, edges):
    """Post-process views after parsing."""
    util.check_key_existence(views.must_exist, views.entities, 'view')
    util.apply_styles(views.styled, views.entities, is_view=True)

    _resolve_view_nodes(views, nodes)

    for view in views.entities.values():
        if len(view['nodes']) > 0:
            view_edges = hh_edge.get_edges_by_tags(edges, view['edge_tags'])
            select_neighbours_for_view(view, nodes, view_edges)
            build_tree(view, nodes, view_edges)

    _expand_views(views, nodes, edges)


def parse(yaml_views, views, must_exist_nodes):
    """Parse YAML view definitions and populate the views structure."""
    for view in yaml_views:
        key = view['id']

        if key in views.entities.keys():
            raise RuntimeError(f'Duplicate view id: {key}')

        if 'style' in view:
            views.must_exist.add(view['style'])
            views.styled.append(view)

            views.entities[key] = view
        else:
            views.entities[key] = util.merge_styles(default, view, is_view=True)

        if 'nodes' in view:
            for node in view['nodes']:
                must_exist_nodes.add(node)

