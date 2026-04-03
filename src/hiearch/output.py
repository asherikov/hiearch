"""Module for handling generic output tasks such as resource resolution and copying."""

import os

from . import util


def resolve_resource_path(resource_path, resource_dirs, temp_dir, copied_resources):
    if resource_path in copied_resources:
        return resource_path

    relative_path = None

    if os.path.exists(resource_path):
        relative_path = util.copy_resource(resource_path, temp_dir)

    if resource_dirs:
        for resource_dir in resource_dirs:
            full_path = os.path.join(resource_dir, resource_path)
            if os.path.exists(full_path):
                relative_path = util.copy_resource(full_path, temp_dir)

    if relative_path is not None:
        copied_resources.add(relative_path)
        return relative_path

    raise RuntimeError(f'Resource not found: {resource_path}')


def resolve_resources(node_ids, nodes, temp_dir, resource_dirs, copied_resources):
    for node_id in node_ids:
        node = nodes[node_id]
        substitutions = node.get('substitutions', {})

        for subst_key, subst_value in substitutions.items():
            if subst_key.startswith("resource_"):
                relative_path = resolve_resource_path(subst_value, resource_dirs, temp_dir, copied_resources)
                node['substitutions'][subst_key] = relative_path

        if 'graphviz' in node and 'image' in node['graphviz']:
            relative_path = resolve_resource_path(node['graphviz']['image'], resource_dirs, temp_dir, copied_resources)
            node['graphviz']['image'] = relative_path

    return copied_resources
