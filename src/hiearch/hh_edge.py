from . import util


def generate_id(edge):
    edge['id'] = f'{edge["out"]}.{edge["in"]}'


def get_style_key(style):
    if isinstance(style, list):
        return f'{style[0]}.{style[1]}'
    return style


def parse(yaml_edges, edges, must_exist_nodes):
    default = {
        'link': ['', ''],
        'style': None,
        'graphviz': {},
        'label': [],
        'substitutions': {},
        # overriden
        'id': None,
        'in': None,
        'out': None,
        'scope_in': None,
        'scope_out': None
    }


    for edge in yaml_edges:
        edge['out'] = edge['link'][0]
        edge['in'] = edge['link'][1]
        if len(edge['link']) > 2:
            edge['id'] = edge['link'][2]
        else:
            generate_id(edge)

        key = edge['id']

        if key in edges.entities.keys():
            raise RuntimeError(f'Duplicate edge id: {key}')

        must_exist_nodes.add(edge['in'])
        must_exist_nodes.add(edge['out'])

        if 'style' in edge:
            edge['style'] = get_style_key(edge['style'])
            edges.must_exist.add(edge['style'])
            edges.styled.append(edge)

            edges.entities[key] = edge
        else:
            edges.entities[key] = util.merge_styles(default, edge)


def postprocess(edges):
    util.check_key_existence(edges.must_exist, edges.entities, 'edge')
    util.apply_styles(edges.styled, edges.entities)


    for edge in edges.entities.values():
        if isinstance(edge['label'], str):
            edge['label'] = ['', edge['label'], '']
        if 'label_format' in edge['graphviz']:
            if isinstance(edge['graphviz']['label_format'], str):
                edge['graphviz']['label_format'] = ['{label}', edge['graphviz']['label_format'], '{label}']
            if len(edge['label']) == 0:
                edge['label'] = ['', '', '']
        else:
            edge['graphviz']['label_format'] = ['{label}', '{label}', '{label}']
