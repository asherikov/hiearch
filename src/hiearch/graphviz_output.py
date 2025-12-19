"""Module for generating graphviz diagrams using pydot."""

import copy
import os
import subprocess

import pydot

from . import hh_node


def get_attributes(node, extended_attrs, label_format_key):
    attrs = extended_attrs | copy.deepcopy(node['graphviz'])

    substitutions = hh_node.get_substitutions(node)
    if extended_attrs['expanded_from'] is not None:
        substitutions.update({'expanded_from': extended_attrs['expanded_from']})
    attrs['label'] = attrs[label_format_key].format(**substitutions)
    for attr in extended_attrs.keys():
        attrs.pop(attr, None)

    return attrs


def get_scope_attributes(node, extended_attrs):
    attrs = get_attributes(node, extended_attrs, 'scope_label_format')
    attrs['cluster'] = 'true'
    return attrs


def get_edge_attributes(edge):
    attrs = copy.deepcopy(edge['graphviz'])

    for attr, label, fmt in zip(['taillabel', 'label', 'headlabel'], edge['label'], attrs['label_format']):
        substitutions = edge['substitutions'] | {
            'label': label,
            'id': edge['id'],
            'node_in': edge['in'],
            'node_out': edge['out'],
            'scope_in': edge['scope_in'],
            'scope_out': edge['scope_out'],
            'style': edge['style']
        }

        formatted_label = fmt.format(**substitutions)
        if len(formatted_label) > 0:
            attrs[attr] = formatted_label

    if 'label_format' in attrs:
        attrs.pop('label_format')

    return attrs


def generate_tree(graph, tree, nodes, extended_attrs):
    if len(tree) > 0:
        for node_key, node_tuple in tree.items():
            node = nodes[node_key]

            if 0 == len(node_tuple['subtree']):
                graph.add_node(
                        pydot.Node(node_tuple['key_path'],
                                   **get_attributes(node, extended_attrs, 'node_label_format')))
            else:
                subgraph = pydot.Subgraph(
                        graph_name=node_tuple['key_path'],
                        **get_scope_attributes(node, extended_attrs))
                generate_tree(subgraph, node_tuple['subtree'], nodes, extended_attrs)
                graph.add_subgraph(subgraph)


def generate(directory, fmt, view, nodes):
    graph = pydot.Dot(graph_name=view['id'], graph_type='digraph')

    extended_attrs = {
        'node_label_format': '{label}',
        'scope_label_format': '{label}',
        'expanded_from': view['expanded_from'],
    }

    if 'graph' in view['graphviz']:
        for key, value in view['graphviz']['graph'].items():
            graph.set(key, value)
    if 'node' in view['graphviz']:
        for key, value in extended_attrs.items():
            extended_attrs[key] = view['graphviz']['node'].pop(key, value)
        graph.set_node_defaults(**view['graphviz']['node'])
    if 'edge' in view['graphviz']:
        graph.set_edge_defaults(**view['graphviz']['edge'])

    graph.set('compound', 'true')

    generate_tree(graph, view['tree'], nodes, extended_attrs)

    for edge_set in ['edges', 'custom_edges']:
        for edge in view[edge_set].values():
            # adjust edges that connect scopes
            if edge['out'] in view['scopes']:
                scope = edge['out']
                for edge_out in view['scopes'][scope]:
                    # https://stackoverflow.com/questions/59825/how-to-retrieve-an-element-from-a-set-without-removing-it
                    break
                edge['graphviz']['ltail'] = scope
                edge['graphviz']['tailclip'] = 'false'  # workaround for bad angle of the arrow head
            else:
                edge_out = edge['out']

            if edge['in'] in view['scopes']:
                scope = edge['in']
                for edge_in in view['scopes'][scope]:
                    # https://stackoverflow.com/questions/59825/how-to-retrieve-an-element-from-a-set-without-removing-it
                    break
                edge['graphviz']['lhead'] = scope
                edge['graphviz']['headclip'] = 'false'  # workaround for bad angle of the arrow head
            else:
                edge_in = edge['in']


            tail = ''
            head = ''
            best_match = -1

            for tail_candidate in view['node_key_paths'][edge_out]:
                for head_candidate in view['node_key_paths'][edge_in]:
                    current_match = len(os.path.commonprefix([tail_candidate, head_candidate]))
                    if current_match > best_match:
                        tail = tail_candidate
                        head = head_candidate
                        best_match = current_match

            graph.add_edge(pydot.Edge(tail, head, **get_edge_attributes(edge)))

    # Write the DOT file
    dot_file_path = f'{directory}/{view["id"]}.gv'
    graph.write(dot_file_path)

    # Call dot directly (pydot uses temporary dirs that dont play nice with inclusions)
    output_file_path = f'{directory}/{view["id"]}.{fmt}'

    cmd = ['dot', '-T' + fmt, '-o', output_file_path, dot_file_path]
    subprocess.run(cmd, check=True, capture_output=True)

