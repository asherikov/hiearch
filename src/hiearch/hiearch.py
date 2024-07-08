#!/usr/bin/env python3

import argparse
import yaml

from . import hh_node
from . import hh_edge
from . import hh_view
from . import graphviz


class ParsedEntities:
    def __init__(self):
        self.entities = {}
        self.must_exist = set()
        self.styled = []



def parse(filenames):
    nodes = ParsedEntities()
    edges = ParsedEntities()
    views = ParsedEntities()


    for filename in filenames:
        print(f'Processing {filename}')
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
    parser = argparse.ArgumentParser(prog='hiearch', description='Generates diagrams')

    parser.add_argument('inputs', metavar='<filename>', type=str, nargs='+', help='Input files')
    parser.add_argument('-o', '--output', required=True, default='hiearch', help='Output directory [hiearch]')
    parser.add_argument('-f', '--format', required=False, default='svg', help='Output format [SVG]')

    args = parser.parse_args()

    nodes, views = parse(args.inputs)

    for view in views.values():
        if len(view['nodes']) > 0:
            graphviz.generate(args.output, args.format, view, nodes)



if __name__ == "__main__":
    main()
