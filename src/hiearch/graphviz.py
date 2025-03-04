import copy
import os
# https://graphviz.readthedocs.io/en/stable/api.html
import graphviz

from . import hh_node


def get_node_attributes(node):
    attrs = copy.deepcopy(node['graphviz'])

    attrs['label'] = node['graphviz']['node_label_format'].format(**hh_node.get_substitutions(node))
    attrs.pop('node_label_format')
    attrs.pop('scope_label_format')
    return attrs


def get_scope_attributes(node):
    attrs = copy.deepcopy(node['graphviz'])

    attrs['label'] = hh_node.get_formatted_scope_label(node)
    attrs['cluster'] = 'true'
    attrs.pop('node_label_format')
    attrs.pop('scope_label_format')
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


def generate_tree(graph, tree, nodes):
    if len(tree) > 0:
        for node_key, node_tuple in tree.items():
            node = nodes[node_key]

            if 0 == len(node_tuple['subtree']):
                graph.node(name=node_tuple['key_path'], **get_node_attributes(node))
            else:
                with graph.subgraph(
                        name=node_tuple['key_path'],
                        graph_attr=get_scope_attributes(node)) as subgraph:
                    generate_tree(subgraph, node_tuple['subtree'], nodes)



def generate(directory, fmt, view, nodes):
    graph = graphviz.Digraph(name=view['id'], directory=directory)

    for attr_group in ['graph', 'node', 'edge']:
        # https://graphviz.org/docs/nodes/
        # https://graphviz.org/docs/edges/
        # https://graphviz.org/docs/graph/
        if attr_group in view['graphviz']:
            graph.attr(attr_group, **view['graphviz'][attr_group])
    graph.graph_attr['compound'] = 'true'

    generate_tree(graph, view['tree'], nodes)

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

            graph.edge(tail_name=tail, head_name=head, **get_edge_attributes(edge))

    graph.render(format=fmt)
    os.rename(f'{directory}/{view["id"]}.gv.{fmt}', f'{directory}/{view["id"]}.{fmt}')  # should not be needed in newer versions


