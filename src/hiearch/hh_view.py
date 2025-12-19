"""Module for handling hiearch views and their processing."""

import copy

from . import hh_edge
from . import hh_node
from . import util


class Neighbours():
    """Class defining the different types of neighbor selection for views."""
    DIRECT = 'direct'
    EXPLICIT = 'explicit'
    PARENT = 'parent'
    RECURSIVE_IN = 'recursive_in'
    RECURSIVE_OUT = 'recursive_out'
    RECURSIVE_ALL = 'recursive_all'

    types = [DIRECT, EXPLICIT, PARENT, RECURSIVE_IN, RECURSIVE_OUT, RECURSIVE_ALL]



default: dict = {
    'id': 'default',
    'nodes': None,
    'neighbours': Neighbours.EXPLICIT,
    'graphviz': {},
    'style': None,
    'tags': [],
    'edges': [],
    'custom_edges': [],
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
                if edges[edge_key][opposite[dir_key]] in view['nodes']:
                    view['edges'][edge_key] = copy.deepcopy(edges[edge_key])


def select_direct(view, nodes, edges, add_nodes):
    """Select edges that connect directly to requested nodes."""
    for node_key in view['nodes']:
        for dir_key in ['in', 'out']:
            opp_dir_key = opposite[dir_key]
            for edge_key in nodes[node_key][dir_key]:
                if edges[edge_key][opp_dir_key] in nodes:
                    view['edges'][edge_key] = copy.deepcopy(edges[edge_key])

    for edge_key in view['edges']:
        for dir_key in ['in', 'out']:
            add_nodes.add(edges[edge_key][dir_key])


def select_parent(view, nodes, edges, add_nodes):
    """Select parent nodes and edges that connect to them."""
    for node_key in view['nodes']:
        for dir_key in ['in', 'out']:
            opp_dir_key = opposite[dir_key]
            for edge_key in nodes[node_key][dir_key]:
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

    if 0 == len(view['nodes_subset']):
        nodes_subset = nodes
    else:
        nodes_subset = view['nodes_subset']

    if Neighbours.EXPLICIT == view['neighbours']:
        select_explicit(view, nodes_subset, edges)

    elif Neighbours.DIRECT == view['neighbours']:
        select_direct(view, nodes_subset, edges, add_nodes)

    elif Neighbours.PARENT == view['neighbours']:
        select_parent(view, nodes_subset, edges, add_nodes)

    elif Neighbours.RECURSIVE_IN == view['neighbours']:
        select_recursive(view, nodes_subset, edges, add_nodes, 'in')

    elif Neighbours.RECURSIVE_OUT == view['neighbours']:
        select_recursive(view, nodes_subset, edges, add_nodes, 'out')

    elif Neighbours.RECURSIVE_ALL == view['neighbours']:
        select_recursive(view, nodes_subset, edges, add_nodes, 'out')
        select_recursive(view, nodes_subset, edges, add_nodes, 'in')

    else:
        raise RuntimeError(f'Unsupported neighbours type: {view["neighbours"]}, must be one of {Neighbours.types}.')

    if len(add_nodes) > 0:
        view['nodes'] = view['nodes'].union(add_nodes)

    view['tree'], view['node_key_paths'], view['scopes'] = hh_node.build_tree(nodes, view['nodes'])


def postprocess(views, nodes, edges):
    """Post-process views after parsing."""
    util.check_key_existence(views.must_exist, views.entities, 'view')
    util.apply_styles(views.styled, views.entities)

    # resolve nodes
    empty_views_counter = 0
    for view in views.entities.values():
        if view['nodes'] is None:
            view['nodes'] = set()
            if 0 == len(view['tags']):
                view['tags'] = ['default']
        else:
            num_nodes = len(view['nodes'])
            view['nodes'] = set(view['nodes'])  # set converted to list by | operator in apply_styles()
            if len(view['nodes']) != num_nodes:
                raise RuntimeError(f'Duplicate node ids in view: {view["id"]} | nodes: {view["nodes"]}')

        for tag in view['tags']:
            view['nodes'] = view['nodes'].union(hh_node.get_nodes_by_tag(nodes, tag))

        if 0 == len(view['nodes']):
            empty_views_counter += 1
            continue

    if empty_views_counter == len(views.entities):
        views.entities['default'] = default
        views.entities['default']['tags'] = ['default']
        views.entities['default']['nodes'] = hh_node.get_nodes_by_tag(nodes, 'default')
        if 0 == len(views.entities['default']['nodes']):
            raise RuntimeError(f'All views are empty: {views.entities.keys()}')

    # select neighbours
    for view in views.entities.values():
        select_neighbours_for_view(view, nodes, edges)


    # Process views and create expanded views if needed (before neighbour processing)
    additional_views = {}

    for view_id, view in views.entities.items():
        # Check if expand field is properly initialized
        if not isinstance(view['expand'], list):
            raise RuntimeError(f'Expand field in view "{view_id}" must be an array.')

        # Process expand parameter if not empty
        if len(view['expand']) > 0:
            expand_types = view['expand']
            view['expanded_from'] = view_id

            original_copy = copy.deepcopy(view)
            original_copy['expand'] = []
            for node in original_copy['nodes']:
                original_copy['nodes_subset'][node] = nodes[node]
            view['expand'] = []

            for expand_type in expand_types:
                if expand_type not in ['recursive_in', 'recursive_out', 'recursive_all']:
                    raise RuntimeError(f'Unsupported expand type: "{expand_type}" in view "{view_id}".')

                for node_id in original_copy['nodes']:
                    # Create a new view with just this single node, expanded
                    new_view_id = f"{view_id}_{node_id}_{expand_type}"
                    new_view = copy.deepcopy(original_copy)
                    new_view['id'] = new_view_id
                    new_view['expanded_from'] = view_id
                    # Use only this single node as the starting point
                    new_view['nodes'] = set([node_id])
                    # Convert parameter to corresponding Neighbours constant
                    new_view['neighbours'] = getattr(Neighbours, expand_type.upper())

                    select_neighbours_for_view(new_view, nodes, edges)

                    additional_views[new_view_id] = new_view


    # Add all the generated expanded views to the main views dictionary
    views.entities.update(additional_views)


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
            views.entities[key] = util.merge_styles(default, view)

        if 'nodes' in view:
            for node in view['nodes']:
                must_exist_nodes.add(node)

