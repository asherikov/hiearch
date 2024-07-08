import copy


def merge_styles(secondary, primary):
    if 'graphviz' in secondary:
        if 'substitutions' in secondary:
            if 'substitutions' in primary:
                primary['substitutions'] = secondary['substitutions'] | primary['substitutions']
            else:
                primary['substitutions'] = secondary['substitutions']

        if 'graphviz' in primary:
            primary['graphviz'] = secondary['graphviz'] | primary['graphviz']
        else:
            primary['graphviz'] = secondary['graphviz']

    return secondary | primary


def apply_styles(styled_entities, entities):
    size = len(styled_entities)
    nodes_style_applied = set()

    while size > 0:
        index = 0
        size_copy = copy.deepcopy(size)
        while index < size:
            father_entity = entities[styled_entities[index]['style']]

            if father_entity['style'] is None or father_entity['id'] in nodes_style_applied:
                key = styled_entities[index]['id']
                entities[key] = merge_styles(father_entity, styled_entities[index])
                nodes_style_applied.add(key)
                styled_entities[index], styled_entities[size - 1] = styled_entities[size - 1], styled_entities[index]
                size -= 1
            else:
                index += 1
        if size_copy == size:
            raise RuntimeError(f'Style cycle detected: {styled_entities}')


def check_key_existence(keys, dictionary, data_type):
    for key in keys:
        if key not in dictionary.keys():
            raise RuntimeError(f'Missing {data_type} id: {key}')

