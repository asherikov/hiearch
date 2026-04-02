"""Module for generating graphviz diagrams using pydot."""

import copy
import os
import subprocess

import pydot

from . import hh_node
from . import util


def resolve_resource_path(resource_path, resource_dirs):
    if os.path.exists(resource_path):
        return resource_path

    if resource_dirs:
        for resource_dir in resource_dirs:
            full_path = os.path.join(resource_dir, resource_path)
            if os.path.exists(full_path):
                return full_path

    raise RuntimeError(f'Resource not found: {resource_path}')


def get_attributes(node, extended_attrs, label_format_key, resource_dirs=None):
    attrs = dict(extended_attrs)
    attrs.update(copy.deepcopy(node['graphviz']))

    substitutions = hh_node.get_substitutions(node)
    if extended_attrs['expanded_from'] is not None:
        substitutions.update({'expanded_from': extended_attrs['expanded_from']})

    # Add image path to substitutions for use in label format strings
    for subst_key, _ in substitutions.items():
        if subst_key.startswith("resource_"):
            substitutions[subst_key] = resolve_resource_path(substitutions[subst_key], resource_dirs)

    attrs['label'] = attrs[label_format_key].format(**substitutions)

    # fix new line in html labels
    if len(attrs['label']) > 2 and attrs['label'][0] == '<' and attrs['label'][-1] == '>':
        attrs['label'] = attrs['label'].replace("\n", "<br />")

    for attr in extended_attrs.keys():
        attrs.pop(attr, None)

    if 'image' in attrs:
        attrs['image'] = resolve_resource_path(attrs['image'], resource_dirs)

    util.process_auto_colors(attrs, [
        node['id'],
        node['style'],
        node['label']
    ])

    return attrs


def get_scope_attributes(node, extended_attrs, resource_dirs=None):
    attrs = get_attributes(node, extended_attrs, 'scope_label_format', resource_dirs)
    attrs['cluster'] = 'true'
    return attrs


def get_edge_attributes(edge):
    attrs = copy.deepcopy(edge['graphviz'])

    for attr, label, fmt in zip(['taillabel', 'label', 'headlabel'], edge['label'], attrs['label_format']):
        substitutions = dict(edge['substitutions'])
        substitutions.update({
            'label': label,
            'id': edge['id'],
            'node_in': edge['in'],
            'node_out': edge['out'],
            'style': edge['style']
        })

        formatted_label = fmt.format(**substitutions)
        if len(formatted_label) > 0:
            attrs[attr] = formatted_label

    if 'label_format' in attrs:
        attrs.pop('label_format')

    util.process_auto_colors(attrs, [
        edge['orig_in'],
        edge['orig_out'],
        edge['style'],
        edge['label']
    ])

    return attrs


def generate_tree(graph, tree, nodes, extended_attrs, resource_dirs=None):
    if len(tree) > 0:
        for node_key, node_tuple in tree.items():
            node = nodes[node_key]

            if 0 == len(node_tuple['subtree']):
                graph.add_node(
                        pydot.Node(node_tuple['key_path'],
                                   **get_attributes(node, extended_attrs, 'node_label_format', resource_dirs)))
            else:
                subgraph = pydot.Subgraph(
                        graph_name=node_tuple['key_path'],
                        **get_scope_attributes(node, extended_attrs, resource_dirs))
                generate_tree(subgraph, node_tuple['subtree'], nodes, extended_attrs, resource_dirs)
                graph.add_subgraph(subgraph)


def generate(output_dir, temp_dir, fmt, view, nodes, resource_dirs=None):
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

    generate_tree(graph, view['tree'], nodes, extended_attrs, resource_dirs)

    for edge_set in ['edges', 'custom_edges']:
        for edge in view[edge_set].values():
            # adjust edges that connect scopes: pick one non-scope child as the edge start/end
            # perform sorting of scoped nodes to avoid random placing
            edge_out = edge['out']
            while edge_out in view['scopes']:
                sorted_childs = list(view['scopes'][edge_out])
                sorted_childs.sort()
                edge_out = sorted_childs[0]
            if edge['out'] != edge_out:
                edge['graphviz']['ltail'] = edge['out']
                edge['graphviz']['tailclip'] = 'false'  # workaround for bad angle of the arrow head

            edge_in = edge['in']
            while edge_in in view['scopes']:
                sorted_childs = list(view['scopes'][edge_in])
                sorted_childs.sort()
                edge_in = sorted_childs[0]
            if edge['in'] != edge_in:
                edge['graphviz']['lhead'] = edge['in']
                edge['graphviz']['headclip'] = 'false'  # workaround for bad angle of the arrow head


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

    # Write the DOT file to the temporary directory
    dot_file_path = f'{temp_dir}/{view["id"]}.gv'
    graph.write(dot_file_path)

    # Call dot directly (pydot uses temporary dirs that dont play nice with inclusions)
    output_file_path = f'{output_dir}/{view["id"]}.{fmt}'

    cmd = ['dot', '-T' + fmt, '-o', output_file_path, dot_file_path]
    subprocess.run(cmd, check=True, capture_output=True)

