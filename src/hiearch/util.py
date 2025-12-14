"""Utility functions for hiearch package."""

import copy


def merge_styles(secondary, primary, with_tags=True):
    """Merge style attributes from secondary into primary."""
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

    result = secondary | primary

    if not with_tags and 'tags' not in primary:
        # do not inherit tags and tags are not explicitly overriden -- reset to default
        result['tags'] = ['default']

    return result


def apply_styles(styled_entities, entities):
    """Apply styles from styled entities to the main entities."""
    size = len(styled_entities)
    nodes_style_applied = set()

    while size > 0:
        index = 0
        size_copy = copy.deepcopy(size)
        while index < size:
            with_tags = True
            if 'style' in styled_entities[index]:
                father_entity = entities[styled_entities[index]['style']]
            else:
                father_entity = entities[styled_entities[index]['style_notag']]
                with_tags = False

            is_style_root = ('style' not in father_entity or father_entity['style'] is None) \
                and ('style_notag' not in father_entity or father_entity['style_notag'] is None)

            if is_style_root or father_entity['id'] in nodes_style_applied:
                key = styled_entities[index]['id']
                entities[key] = merge_styles(father_entity, styled_entities[index], with_tags)
                nodes_style_applied.add(key)
                styled_entities[index], styled_entities[size - 1] = styled_entities[size - 1], styled_entities[index]
                size -= 1
            else:
                index += 1
        if size_copy == size:
            raise RuntimeError(f'Style cycle detected: {styled_entities}')


def check_key_existence(keys, dictionary, data_type):
    """Check if all keys exist in the dictionary, raising an error if not."""
    for key in keys:
        if key not in dictionary.keys():
            raise RuntimeError(f'Missing {data_type} id: {key}')

