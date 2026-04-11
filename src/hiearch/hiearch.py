#!/usr/bin/env python3
"""Main hiearch module for generating diagrams from textual descriptions."""

import argparse
import fnmatch
import os
import sys
import shutil
import importlib_resources
import yaml

from . import graphviz_input
from . import graphviz_output
from . import hh_edge
from . import hh_node
from . import hh_view
from . import output


class ParsedEntities:
    """Class to hold parsed entities (nodes, edges, views) with associated metadata."""

    def __init__(self):
        self.entities = {}
        self.must_exist = set()
        self.styled = []


def parse(temp_dir, filenames, resource_dirs=None):
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

    return nodes.entities, views.entities, resource_dirs


def install_skill(skill_dir):
    """Install hiearch skill file to coding agent skill directory."""
    skill_source = importlib_resources.files('hiearch.data.skill')

    if not skill_source.is_dir():
        print('Error: Skill source directory not found in package', file=sys.stderr)
        sys.exit(1)

    hiearch_skill_dir = f'{skill_dir}/hiearch'

    if os.path.exists(hiearch_skill_dir):
        print(f'Warning: Skill directory already exists: {hiearch_skill_dir}. Overwriting.', file=sys.stderr)
        shutil.rmtree(hiearch_skill_dir)

    os.makedirs(hiearch_skill_dir, exist_ok=True)

    for item in skill_source.iterdir():
        if item.is_file():
            dest_file = os.path.join(hiearch_skill_dir, item.name)
            with item.open('rb') as src_file:
                content = src_file.read()
            with open(dest_file, 'wb') as dst_file:
                dst_file.write(content)

    print(f'Skill installed to {hiearch_skill_dir}')


def main():
    """Main entry point for hiearch application."""
    parser = argparse.ArgumentParser(prog='hiearch', description='Generates diagrams')

    parser.add_argument('inputs', metavar='<filename>', type=str, nargs='*', help='Input files')
    parser.add_argument('-o', '--output', required=False, default='./', help='Output directory [./]')
    parser.add_argument('-f', '--format', required=False, default='svg', help='Output format [SVG]')
    parser.add_argument('-t', '--temp-dir', required=False, default=None, help='Temporary files output directory (defaults to output directory)')
    parser.add_argument('-r', '--resource-dirs', required=False, default=[], action='append',
                        help='Directories to search for graphical resources (can be specified multiple times)')
    parser.add_argument('-i', '--install-skill', required=False, nargs='?', const=True, default=False,
                        help='Install hiearch skill to coding agent skill directory')
    parser.add_argument('-l', '--list-styles', required=False, action='store_true', default=False,
                        help='List installed styles')
    parser.add_argument('-s', '--styles', required=False, default=[], action='append',
                        help='Style names or patterns to include (can be specified multiple times, supports wildcards)')

    args = parser.parse_args()


    # Handle --install-skill option
    if args.install_skill is not False:
        skill_dir = args.install_skill if isinstance(args.install_skill, str) else os.path.expanduser('~/.qwen/skills/hiearch')
        install_skill(skill_dir)
        return

    styles_root = importlib_resources.files('hiearch.data.styles')

    # Handle --list-styles option
    if args.list_styles:
        for yaml_file in sorted(styles_root.iterdir()):
            if yaml_file.suffix == '.yaml':
                print(yaml_file.name[:-5])
        return

    # Require input files for normal operation
    if not args.inputs:
        parser.error('the following arguments are required: <filename>')

    # Build a map of base styles to their variants
    style_variants = {}
    for yaml_file in sorted(styles_root.iterdir()):
        if yaml_file.suffix == '.yaml':
            style_name = yaml_file.name[:-5]
            if '-' in style_name:
                # Style has base-variant format
                base_name = style_name.split('-', 1)[0]
                if base_name not in style_variants:
                    style_variants[base_name] = []
                style_variants[base_name].append((style_name, str(yaml_file)))
            else:
                # Style without variant (no dash)
                style_variants[style_name] = [(style_name, str(yaml_file))]

    if args.styles:
        # Use provided style patterns
        patterns = [p for pattern_list in args.styles for p in pattern_list.split(',')]
        selected_variants = set()
        for yaml_file in sorted(styles_root.iterdir()):
            if yaml_file.suffix != '.yaml':
                continue
            style_name = yaml_file.name[:-5]
            if any(fnmatch.fnmatch(style_name, pattern) for pattern in patterns):
                if '-' in style_name:
                    base_name = style_name.split('-', 1)[0]
                    if base_name in selected_variants:
                        print(f'Error: Conflicting style variants selected for base style "{base_name}"', file=sys.stderr)
                        sys.exit(1)
                    selected_variants.add(base_name)
                args.inputs.append(str(yaml_file))
    else:
        # Include first variant of each base style by default
        for base_name in sorted(style_variants.keys()):
            variants = style_variants[base_name]
            # First variant in sorted list
            args.inputs.append(variants[0][1])

    # Use temporary directory if specified, otherwise use output directory
    temp_dir = args.temp_dir if args.temp_dir is not None else args.output

    nodes, views, resource_dirs = parse(temp_dir, args.inputs, args.resource_dirs)

    copied_resources = set()
    for view in views.values():
        if len(view['nodes']) > 0:
            # Resolve and copy resources from selected nodes before generating views
            copied_resources = output.resolve_resources(view['nodes'], nodes, temp_dir, resource_dirs, copied_resources)

            graphviz_output.generate(args.output, temp_dir, args.format, view, nodes, copied_resources)


if __name__ == "__main__":
    main()
