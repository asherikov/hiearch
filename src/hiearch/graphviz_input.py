#!/usr/bin/env python3
"""Converter module for converting DOT files to hiearch YAML representation."""

import pydot


def _extract_default_attributes(defaults_list):
    """Generic function to extract default attributes from a list of default objects."""
    result = {}
    if defaults_list:
        for default_obj in defaults_list:
            if isinstance(default_obj, dict):
                result.update(default_obj)
            elif hasattr(default_obj, 'get_attributes'):
                result.update(default_obj.get_attributes())
    return result


class AttributeContainer:
    """Container for graph, node, and edge attributes with inheritance."""

    def __init__(self, graph, attr_container):
        self.graph_attrs = _extract_default_attributes(graph.get_graph_defaults())
        self.node_attrs = _extract_default_attributes(graph.get_node_defaults())
        self.edge_attrs = _extract_default_attributes(graph.get_edge_defaults())

        # Merge with higher-level defaults
        if attr_container:
            self.graph_attrs = attr_container.graph_attrs | self.graph_attrs
            self.node_attrs = attr_container.node_attrs | self.node_attrs
            self.edge_attrs = attr_container.edge_attrs | self.edge_attrs


class GraphStatus:
    """Tracks the status of a graph during conversion process."""

    def __init__(self, file_id):
        self.nodes = set()
        self.file_id = file_id
        self.view_id = ''

    def set_graph_name(self, graph_index, graph_name):
        """Set the graph name based on graph index and provided name."""
        if not graph_name:
            self.view_id = f'{self.file_id}_{graph_index}'
        else:
            self.view_id = graph_name

    def add_node(self, node_id, hiearch_data, attributes, scope_id):
        """Add a node to the hiearch data structure."""
        label = attributes.get('label', node_id)

        if node_id in self.nodes:
            # Node was already added (probably via an edge), so we need to update its attributes
            # Find the existing node and update both its attributes and label if needed
            for existing_node in hiearch_data['nodes']:
                if existing_node['id'][1] == node_id:
                    existing_node['graphviz'].update(attributes)
                    existing_node['id'][0] = label
                    break
        else:
            node_info = {
                'id': [label, node_id],
                'graphviz': attributes,
                'tags': ['default', self.view_id]
            }

            if scope_id:
                node_info['scope'] = scope_id

            hiearch_data['nodes'].append(node_info)
            self.nodes.add(node_id)


def _process_contents(graph, hiearch_data, graph_status, parent_attr_container, scope_id):
    """Process the contents of a graph including subgraphs, nodes, and edges."""
    attr_container = AttributeContainer(graph, parent_attr_container)

    for subgraph in graph.get_subgraphs():
        _process_subgraph_recursive(subgraph, hiearch_data, graph_status, attr_container, scope_id)

    for node in graph.get_nodes():
        final_attrs = attr_container.node_attrs | node.get_attributes()
        node_name = node.get_name().strip('"')
        if node_name not in ['node', 'edge', 'graph']:
            graph_status.add_node(node_name, hiearch_data, final_attrs, scope_id)

    for edge in graph.get_edges():
        edge_nodes = [edge.get_source().strip('"'), edge.get_destination().strip('"')]
        for node in edge_nodes:
            if node not in graph_status.nodes:
                graph_status.add_node(node, hiearch_data, attr_container.node_attrs, scope_id)

        edge_info = {
            'link': [edge_nodes[0], edge_nodes[1]],
            'graphviz': attr_container.edge_attrs | edge.get_attributes()
        }

        hiearch_data['edges'].append(edge_info)


def _process_subgraph_recursive(subgraph, hiearch_data, graph_status, attr_container, parent_scope_id):
    """Recursively process a subgraph and its contents."""
    node_id = subgraph.get_name().strip('"')
    subgraph_attrs = (attr_container.graph_attrs
                      | subgraph.get_attributes()
                      | _extract_default_attributes(subgraph.get_node("graph")))

    graph_status.add_node(node_id, hiearch_data, subgraph_attrs, parent_scope_id)

    # Process subgraph contents with inheritance
    _process_contents(subgraph, hiearch_data, graph_status, attr_container, node_id)


def dot_to_hiearch(file_id, dot_content):
    """Convert DOT content to hiearch YAML data structure.

    Args:
        file_id: ID of the input file
        dot_content: Content of the DOT file as string

    Returns:
        Dictionary representing hiearch data structure
    """
    graphs = pydot.graph_from_dot_data(dot_content)

    if not graphs:
        raise ValueError("Could not parse DOT content")

    hiearch_data = {
        'nodes': [],
        'edges': [],
        'views': [],
    }

    graph_status = GraphStatus(file_id)
    for i, graph in enumerate(graphs):
        graph_status.set_graph_name(i, graph.get_name())

        style_view = {
            'id': graph_status.view_id,
            'tags': [graph_status.view_id],
            'graphviz': {
                'graph': (graph.get_attributes()
                          | _extract_default_attributes(graph.get_node("graph")))
            }
        }
        hiearch_data['views'].append(style_view)

        _process_contents(graph, hiearch_data, graph_status, AttributeContainer(graph, None), None)

    return hiearch_data
