#!/usr/bin/env python3
"""Main hiearch module for generating diagrams from textual descriptions."""

import argparse
import os
import importlib_resources
import yaml

from . import graphviz_input
from . import graphviz_output
from . import hh_edge
from . import hh_node
from . import hh_view


class ParsedEntities:
    """Class to hold parsed entities (nodes, edges, views) with associated metadata."""

    def __init__(self):
        self.entities = {}
        self.must_exist = set()
        self.styled = []


def parse(temp_dir, filenames):
    nodes = ParsedEntities()
    edges = ParsedEntities()
    views = ParsedEntities()

    for filename in filenames:
        print(f'Processing {filename}')
        if filename.endswith('.dot') or filename.endswith('.gv'):
            # Handle DOT files by converting them to hiearch YAML representation directly
            with open(filename, 'r', encoding='utf-8') as file:
                content = file.read()
            data = graphviz_input.dot_to_hiearch(os.path.basename(filename), content)

            # Store the generated YAML in the temporary directory
            temp_yaml_path = f'{temp_dir}/{os.path.basename(filename)}.yaml'
            with open(temp_yaml_path, 'w', encoding='utf-8') as file:
                yaml.dump(data, file, default_flow_style=False, allow_unicode=True)
        else:
            # Process YAML files as usual
            with open(filename, encoding='utf-8') as file:
                data = yaml.load(file, Loader=yaml.SafeLoader)

        if 'nodes' in data:
            hh_node.parse(data['nodes'], nodes)

        if 'edges' in data:
            hh_edge.parse(data['edges'], edges, nodes.must_exist)

        if 'views' in data:
            hh_view.parse(data['views'], views, nodes.must_exist)

    hh_edge.postprocess(edges)
    hh_node.postprocess(nodes, edges.entities)
    hh_view.postprocess(views, nodes.entities, edges.entities)

    return nodes.entities, views.entities


def main():
    """Main entry point for hiearch application."""
    parser = argparse.ArgumentParser(prog='hiearch', description='Generates diagrams')

    parser.add_argument('inputs', metavar='<filename>', type=str, nargs='+', help='Input files')
    parser.add_argument('-o', '--output', required=False, default='./', help='Output directory [./]')
    parser.add_argument('-f', '--format', required=False, default='svg', help='Output format [SVG]')
    parser.add_argument('-t', '--temp-dir', required=False, default=None, help='Temporary files output directory (defaults to output directory)')

    args = parser.parse_args()

    # Automatically include installed style files
    for style_file in ['state_machine.yaml', 'use_case.yaml', 'dinit_service.yaml']:
        style_path = importlib_resources.files('hiearch.data.styles') / style_file
        if style_path.exists():
            args.inputs.append(str(style_path))

    # Use temporary directory if specified, otherwise use output directory
    temp_dir = args.temp_dir if args.temp_dir is not None else args.output

    nodes, views = parse(temp_dir, args.inputs)

    for view in views.values():
        if len(view['nodes']) > 0:
            graphviz_output.generate(args.output, temp_dir, args.format, view, nodes)


if __name__ == "__main__":
    main()
