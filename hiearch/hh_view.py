import copy

from . import hh_node
from . import hh_edge
from . import util


class Neighbours():
    DIRECT = 'direct'
    EXPLICIT = 'explicit'
    PARENT = 'parent'

    types = [DIRECT, EXPLICIT, PARENT]



default: dict = {
    'id': 'default',
    'nodes': None,
    'neighbours': Neighbours.EXPLICIT,
    'graphviz': {},
    'style': None,
    'tags': [],
    # overriden
    'edges': [],
    'custom_edges': [],
    'tree': {},
}


opposite = {
    'in': 'out',
    'out': 'in',
}


def select_explicit(view, nodes, edges):
    for node_key in view['nodes']:
        for dir_key in ['in', 'out']:
            for edge_key in nodes[node_key][dir_key]:
                if edges[edge_key][opposite[dir_key]] in view['nodes']:
                    view['edges'][edge_key] = copy.deepcopy(edges[edge_key])


def select_direct(view, nodes, edges, add_nodes):
    for node_key in view['nodes']:
        for dir_key in ['in', 'out']:
            for edge_key in nodes[node_key][dir_key]:
                view['edges'][edge_key] = copy.deepcopy(edges[edge_key])

    for edge_key in view['edges']:
        for dir_key in ['in', 'out']:
            add_nodes.add(edges[edge_key][dir_key])


def select_parent(view, nodes, edges, add_nodes):
    for node_key in view['nodes']:
        for dir_key in ['in', 'out']:
            opp_dir_key = opposite[dir_key]
            for edge_key in nodes[node_key][dir_key]:
                nodes_to_explore = set([edges[edge_key][opp_dir_key]])

                while len(nodes_to_explore) > 0:
                    scope_node_key = nodes_to_explore.pop()

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


def postprocess(views, nodes, edges):
    util.check_key_existence(views.must_exist, views.entities, 'view')
    util.apply_styles(views.styled, views.entities)


    if 0 == len(views.entities):
        views.entities['default'] = default
        views.entities['default']['tags'] = ['default']

    empty_views_counter = 0
    for view in views.entities.values():
        if view['nodes'] is None:
            view['nodes'] = set()
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


        view['edges'] = {}
        view['custom_edges'] = {}
        add_nodes = set()

        if Neighbours.EXPLICIT == view['neighbours']:
            select_explicit(view, nodes, edges)

        elif Neighbours.DIRECT == view['neighbours']:
            select_direct(view, nodes, edges, add_nodes)

        elif Neighbours.PARENT == view['neighbours']:
            select_parent(view, nodes, edges, add_nodes)

        else:
            raise RuntimeError(f'Unsupported neighbours type: {view["neighbours"]}, must be one of [{Neighbours.types}].')

        if len(add_nodes) > 0:
            view['nodes'] = view['nodes'].union(add_nodes)


        view['tree'], view['node_key_paths'], view['scopes'] = hh_node.build_tree(nodes, view['nodes'])


    if empty_views_counter == len(views.entities):
        raise RuntimeError(f'All views are empty: {views.entities.keys()}')


def parse(yaml_views, views, must_exist_nodes):
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

