from . import util


default = {
    'link': ['', ''],
    'style': None,
    'style_notag': None,
    'graphviz': {},
    'label': [],
    'substitutions': {},
    'tags': {'default'},
    # should never change after initialization
    'orig_in': None,
    'orig_out': None,
    # overriden
    'id': None,
    'in': None,
    'out': None,
}


def generate_id(edge):
    edge['id'] = f'{edge["out"]}.{edge["in"]}'


def get_style_key(style):
    if isinstance(style, list):
        return f'{style[0]}.{style[1]}'
    return style


def parse(yaml_edges, edges, must_exist_nodes):
    for edge in yaml_edges:
        edge['in'] = edge['link'][1]
        edge['out'] = edge['link'][0]
        edge['orig_in'] = edge['in']
        edge['orig_out'] = edge['out']
        if len(edge['link']) > 2:
            edge['id'] = edge['link'][2]
        else:
            generate_id(edge)

        key = edge['id']

        if key in edges.entities.keys():
            raise RuntimeError(f'Duplicate edge id: {key}')

        must_exist_nodes.add(edge['in'])
        must_exist_nodes.add(edge['out'])

        has_style = 'style' in edge
        has_style_notag = 'style_notag' in edge

        if has_style and has_style_notag:
            raise RuntimeError(f'Edge {key} cannot have both style and style_notag attributes')

        if has_style:
            edge['style'] = get_style_key(edge['style'])
            edges.must_exist.add(edge['style'])
            edges.styled.append(edge)
            edges.entities[key] = edge
        elif has_style_notag:
            edge['style_notag'] = get_style_key(edge['style_notag'])
            edges.must_exist.add(edge['style_notag'])
            edges.styled.append(edge)
            edges.entities[key] = edge
        else:
            edges.entities[key] = util.merge_styles(default, edge)


def postprocess(edges):
    util.check_key_existence(edges.must_exist, edges.entities, 'edge')
    util.apply_styles(edges.styled, edges.entities)


    for edge in edges.entities.values():
        if not isinstance(edge['tags'], set):
            edge['tags'] = util.ensure_set(edge['tags'])
        if isinstance(edge['label'], str):
            edge['label'] = ['', edge['label'], '']
        if 'label_format' in edge['graphviz']:
            if isinstance(edge['graphviz']['label_format'], str):
                edge['graphviz']['label_format'] = ['{label}', edge['graphviz']['label_format'], '{label}']
            if len(edge['label']) == 0:
                edge['label'] = ['', '', '']
        else:
            edge['graphviz']['label_format'] = ['{label}', '{label}', '{label}']

        if edge.get('style') is not None and edge.get('style_notag') is None:
            for ancestor in util.collect_style_ancestors(
                    edge['style'], edges.entities):
                edge['tags'].add(f'hh:style:{ancestor}')


def get_edges_by_tags(edges, tags):
    selection = {}
    for key, edge in edges.items():
        if tags.intersection(edge['tags']):
            selection[key] = edge
    return selection
