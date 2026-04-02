"""Utility functions for hiearch package."""

import copy
import hashlib


def generate_auto_color(seed_string):
    """Generate a deterministic random color based on a seed string.

    Args:
        seed_string: String to use as seed for color generation

    Returns:
        Hex color string in format '#rrggbb'
    """
    hash_object = hashlib.md5(seed_string.encode())
    hash_hex = hash_object.hexdigest()
    r = int(hash_hex[0:2], 16)
    g = int(hash_hex[2:4], 16)
    b = int(hash_hex[4:6], 16)
    return f'#{r:02x}{g:02x}{b:02x}'


def process_auto_colors(attrs, seed_data):
    """Replace 'auto' color values with deterministic generated colors.

    Args:
        attrs: Dictionary of attributes that may contain 'auto' colors
        seed_data: Data to use for generating deterministic seed strings

    Returns:
        Modified attrs dictionary with 'auto' replaced by generated colors
    """
    color_attrs = ['color', 'fillcolor', 'fontcolor', 'edgecolor', 'linecolor']

    for attr in color_attrs:
        if attr in attrs and attrs[attr] == 'auto':
            seed_string = attr
            for seed in seed_data:
                if seed is None:
                    continue
                if isinstance(seed, list):
                    for item in seed:
                        seed_string += item
                    continue
                seed_string += seed
            attrs[attr] = generate_auto_color(seed_string)

    return attrs


def merge_dict_by_key(secondary, primary, key):
    if key in primary:
        tmp = dict(secondary[key])
        tmp.update(primary[key])
        primary[key] = tmp
    else:
        primary[key] = secondary[key]


def merge_styles(secondary, primary, with_tags=True, is_view=False):
    """Merge style attributes from secondary into primary."""
    if 'graphviz' in secondary:
        if 'substitutions' in secondary:
            merge_dict_by_key(secondary, primary, 'substitutions')

        if is_view:
            # there is an extra nested level in views
            for group in ["graph", "edge", "node"]:
                if group in secondary['graphviz']:
                    if 'graphviz' in primary:
                        merge_dict_by_key(secondary['graphviz'], primary['graphviz'], group)
                    else:
                        primary['graphviz'] = secondary['graphviz']
        else:
            merge_dict_by_key(secondary, primary, 'graphviz')

    result = dict(secondary)
    result.update(primary)

    if not with_tags and 'tags' not in primary:
        # do not inherit tags and tags are not explicitly overriden -- reset to default
        result['tags'] = ['default']

    return result


def apply_styles(styled_entities, entities, is_view=False):
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
                entities[key] = merge_styles(father_entity, styled_entities[index], with_tags, is_view)
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

