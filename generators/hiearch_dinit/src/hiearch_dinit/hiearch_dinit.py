"""
Parse dinit service files and generate a dependency graph in hiearch YAML format.

This script traverses a set of directories, parses dinit service files,
builds a dependency graph, and outputs it in hiearch YAML format for use with hiearch.
"""

import argparse
import os
import re
import sys
import importlib_resources

import yaml


def extract_base_name(name):
    """
    Extract the base name by removing the @ and everything after it.

    Args:
        name (str): The name to extract base from

    Returns:
        str: Base name without @ and parameters
    """
    return name.split('@')[0] if '@' in name else name


def has_parametrized_dependency(dep):
    """
    Check if a dependency is parametrized (contains @ and $ or underscore and $).

    Args:
        dep (str): The dependency to check

    Returns:
        bool: True if the dependency is parametrized
    """
    return re.search(r'@.*\$\d+', dep) or re.search(r'_.*\$\d+', dep)


def is_parameter_placeholder(dep):
    """
    Check if a dependency is a parameter placeholder (starts with $).

    Args:
        dep (str): The dependency to check

    Returns:
        bool: True if the dependency is a parameter placeholder
    """
    return dep.startswith('$')


def filter_dependencies(deps):
    """
    Filter dependencies to remove parametrized dependencies and parameter placeholders.

    Args:
        deps (list): List of dependencies to filter

    Returns:
        tuple: (filtered_deps, parametrized_deps) - both lists
    """
    filtered_deps = []
    parametrized_deps = []

    for dep in deps:
        parametrized_deps.append(dep)  # Keep original parametrized form
        if has_parametrized_dependency(dep):
            # This is a parametrized dependency, don't add to regular dependencies
            continue
        # Filter out parameters after @ symbol in dependency names for regular dependencies
        base_dep = extract_base_name(dep)
        # Skip parameter placeholders like $1, $2, etc.
        if not is_parameter_placeholder(base_dep):
            filtered_deps.append(base_dep)

    return filtered_deps, parametrized_deps


def parse_service_file(file_path):
    """
    Parse a dinit service file and extract dependencies and service type.

    Args:
        file_path (str): Path to the service file

    Returns:
        dict: A dictionary with service name, type and its dependencies
    """
    dependencies = {
        'depends-on': [],
        'depends-ms': [],
        'waits-for': [],
        'after': [],
        'before': [],
        'chain-to': [],
        'depends-on.d': [],
        'depends-ms.d': [],
        'waits-for.d': []
    }

    # Store original parametrized dependencies for later matching
    parametrized_dependencies = {
        'depends-on': [],
        'depends-ms': [],
        'waits-for': [],
        'after': [],
        'before': [],
        'chain-to': [],
        'depends-on.d': [],
        'depends-ms.d': [],
        'waits-for.d': []
    }

    service_type = 'process'  # Default service type
    has_parameters = False  # Flag to detect if the service supports arguments

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, PermissionError):
        # Skip binary or unreadable files
        sys.stderr.write(f'Warning: Could not read file {file_path}\n')
        service_name = os.path.basename(file_path)
        service_name = service_name.split('@')[0] if '@' in service_name else service_name
        return {
            'name': service_name,
            'type': service_type,
            'dependencies': dependencies,
            'parametrized_dependencies': parametrized_dependencies,
            'has_parameters': has_parameters
        }

    current_line = 0
    lines = content.splitlines()

    while current_line < len(lines):
        line = lines[current_line].strip()
        current_line += 1

        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue

        # Handle meta-commands (lines starting with @)
        if line.startswith('@'):
            # For @include and @include-opt, we would need to process included files
            # For now, we'll just skip them
            continue

        # Check if this line contains parameter references (like $1, $2, $3 etc.)
        if re.search(r'\$\d+', line):
            has_parameters = True

        # Match property patterns
        # Format: property = value or property: value
        match = re.match(r'^([a-zA-Z0-9._-]+)\s*([:=])\s*(.*)$', line)
        if match:
            prop_name = match.group(1).strip()
            value = match.group(3).strip()

            # Remove trailing comments
            if '#' in value:
                value = value[:value.index('#')].strip()

            # Handle service type
            if prop_name == 'type':
                service_type = value.split()[0] if value.split() else 'process'

            # Handle dependency properties
            if prop_name in dependencies:
                # Handle multi-line values if they exist
                full_value = value
                while current_line < len(lines) and lines[current_line].startswith(' '):
                    continued_line = lines[current_line].strip()
                    if continued_line:
                        full_value += ' ' + continued_line
                    current_line += 1

                # Add dependencies (space-separated values)
                deps = full_value.split()

                # Filter dependencies to separate regular and parametrized dependencies
                filtered_deps, parametrized_deps = filter_dependencies(deps)

                dependencies[prop_name].extend(filtered_deps)
                parametrized_dependencies[prop_name].extend(parametrized_deps)

    # Extract service name - for files with @ in the name, keep the full name
    # as it's an instantiated parametrized service
    service_name = os.path.basename(file_path)
    # If the filename contains @ and the service doesn't have parameters in its content,
    # it's an instantiated parametrized service, so keep the full name
    if '@' in service_name and not has_parameters:
        # This is an instantiated parametrized service, keep the full name
        service_name = os.path.basename(file_path)  # Keep full name including @
    else:
        # This is either a regular service or a template service, extract base name
        service_name = extract_base_name(service_name)

    return {
        'name': service_name,
        'type': service_type,
        'dependencies': dependencies,
        'parametrized_dependencies': parametrized_dependencies,
        'has_parameters': has_parameters
    }


def get_services_from_directory(directory):
    """
    Get all service files from a directory (non-recursive).

    Args:
        directory (str): Directory path to scan

    Returns:
        list: List of service file paths
    """
    service_files = []

    # Look for all files in the directory (not subdirectories)
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isfile(item_path):
            service_files.append(item_path)

    return service_files


def expand_directory_dependencies(directory_dep_path, service_dir):
    """
    Expand directory-based dependencies by reading files in the specified directory.

    Args:
        directory_dep_path (str): Path relative to the service file
        service_dir (str): Directory containing the service file

    Returns:
        list: List of service names from the directory
    """
    # Resolve the actual directory path
    if directory_dep_path.startswith('/'):
        actual_dir = directory_dep_path
    else:
        actual_dir = os.path.join(service_dir, directory_dep_path)

    services = []
    if os.path.isdir(actual_dir):
        for item in os.listdir(actual_dir):
            if not item.startswith('.'):  # Skip hidden files/directories
                # Extract service name without parameters (before @ symbol)
                base_service_name = extract_base_name(item)
                services.append(base_service_name)

    return services


def get_style_for_service_type(service_type):
    """
    Get a hiearch style for a given service type.

    Args:
        service_type (str): Type of the service

    Returns:
        str: Style name for the service type
    """
    style_map = {
        'process': 'dinit_process',
        'bgprocess': 'dinit_bgprocess',
        'scripted': 'dinit_scripted',
        'internal': 'dinit_internal',
        'triggered': 'dinit_triggered',
        'unknown': 'dinit_unknown',  # For missing dependencies
    }
    return style_map.get(service_type, 'dinit_unknown')


def get_edge_style_for_dependency_type(dep_type):
    """
    Get a hiearch edge style for a given dependency type.

    Args:
        dep_type (str): Type of the dependency

    Returns:
        str: Edge style name for the dependency
    """
    edge_style_map = {
        'depends-on': 'dinit_depends_on',      # Standard dependency
        'depends-ms': 'dinit_depends_ms',      # Milestone dependency
        'waits-for': 'dinit_waits_for',        # Waits-for dependency
        'after': 'dinit_after',                # Ordering dependency
        'chain-to': 'dinit_chain_to',          # Chain-to dependency
        'parametrized_depends-on': 'dinit_parametrized_depends_on',  # Parametrized dependency
        'parametrized_depends-ms': 'dinit_parametrized_depends_ms',  # Parametrized milestone dependency
        'parametrized_waits-for': 'dinit_parametrized_waits_for',    # Parametrized waits-for dependency
        'parametrized_after': 'dinit_parametrized_after',            # Parametrized ordering dependency
        'parametrized_chain-to': 'dinit_parametrized_chain_to',      # Parametrized chain-to dependency
    }
    return edge_style_map.get(dep_type, 'dinit_depends_on')


def add_dependency_edges(service_name, dependencies, service_dir, nodes, edges):
    """Add dependency edges to the graph."""
    # Add all dependency types that create edges (hard dependencies)
    for dep_type in ['depends-on', 'depends-ms', 'waits-for']:
        for dep in dependencies[dep_type]:
            if dep.endswith('.d'):
                # This is a directory dependency
                expanded_deps = expand_directory_dependencies(dep[:-2], service_dir)
                for expanded_dep in expanded_deps:
                    # Always add the dependency as a node, regardless of whether
                    # it exists in scanned files
                    if expanded_dep not in nodes:
                        nodes[expanded_dep] = ('unknown', False)  # Default type for missing dependencies
                    edge_tuple = (service_name, expanded_dep, dep_type, None)  # None indicates no parameter
                    # Since edges is now always a list, just append if not already present
                    if edge_tuple not in edges:
                        edges.append(edge_tuple)
            else:
                # Regular dependency - always add as a node even if not found in scanned files
                if dep not in nodes:
                    nodes[dep] = ('unknown', False)  # Default type for missing dependencies
                edge_tuple = (service_name, dep, dep_type, None)  # None indicates no parameter label
                # Since edges is now always a list, just append if not already present
                if edge_tuple not in edges:
                    edges.append(edge_tuple)

    # Handle 'after' dependencies (ordering, but still represent as edges)
    for dep in dependencies['after']:
        if dep not in nodes:
            nodes[dep] = ('unknown', False)  # Default type for missing dependencies
        edge_tuple = (service_name, dep, 'after', None)  # None indicates no parameter label
        # Since edges is now always a list, just append if not already present
        if edge_tuple not in edges:
            edges.append(edge_tuple)

    # Handle 'before' dependencies (reverse of after)
    for dep in dependencies['before']:
        if dep not in nodes:
            nodes[dep] = ('unknown', False)  # Default type for missing dependencies
        edge_tuple = (dep, service_name, 'after', None)  # before is reverse of after,
        # Since edges is now always a list, just append if not already present
        if edge_tuple not in edges:
            edges.append(edge_tuple)
        # None indicates no parameter label

    # Handle 'chain-to' dependencies (chain service to another service)
    for dep in dependencies['chain-to']:
        if dep not in nodes:
            nodes[dep] = ('unknown', False)  # Default type for missing dependencies
        edge_tuple = (service_name, dep, 'chain-to', None)  # None indicates no parameter label
        # Since edges is now always a list, just append if not already present
        if edge_tuple not in edges:
            edges.append(edge_tuple)


def add_parametrized_dependency_edges(service_name, parametrized_dependencies, nodes, edges):
    """Add dependency edges for parametrized dependencies that match existing services."""
    # Get all service names
    all_service_names = list(nodes.keys())

    # Process all parametrized dependency types
    for dep_type in ['depends-on', 'depends-ms', 'waits-for', 'after', 'before', 'chain-to']:
        for parametrized_dep in parametrized_dependencies[dep_type]:
            _handle_parametrized_dependency(
                service_name, parametrized_dep, dep_type, all_service_names, edges
            )


def _handle_parametrized_dependency(service_name, parametrized_dep, dep_type, all_service_names, edges):
    """Helper function to handle individual parametrized dependencies to reduce nesting."""
    # Check if this dependency contains the @ pattern with parameter placeholder (like $1, $2, etc.)
    # This is "parametrized argument" - should create a dependency from service to
    # the base template service
    if re.search(r'@.*\$\d+', parametrized_dep):
        _handle_at_pattern_dependency(service_name, parametrized_dep, dep_type, all_service_names, edges)
        return

    # Check if this dependency contains the underscore pattern with parameter placeholder
    # This is "parametrized name" - should create dashed edges to matching services with labels
    if re.search(r'_.*\$\d+', parametrized_dep):
        _handle_underscore_pattern_dependency(service_name, parametrized_dep, dep_type, all_service_names, edges)


def _handle_at_pattern_dependency(service_name, parametrized_dep, dep_type, all_service_names, edges):
    """Handle dependencies with @ pattern (parametrized arguments)."""
    # Extract the base service name (before @)
    base_service_part = parametrized_dep.split('@')[0]

    # Create a dependency from the current service to the base template service
    base_service_exists = base_service_part in all_service_names
    if not (base_service_exists and service_name != base_service_part):  # Avoid self-dependencies
        return

    # For 'before' dependencies, reverse the edge direction
    if dep_type == 'before':
        edge_tuple = (base_service_part, service_name, 'after', None)
    else:
        edge_tuple = (service_name, base_service_part, dep_type, None)

    # Since edges is now always a list, just append if not already present
    if edge_tuple not in edges:
        edges.append(edge_tuple)


def _handle_underscore_pattern_dependency(service_name, parametrized_dep, dep_type, all_service_names, edges):
    """Handle dependencies with underscore pattern (parametrized names)."""
    # Extract the base service name (before _) and parameter pattern
    # Split by the last occurrence of _$ to handle cases like service_$1
    parts = parametrized_dep.rsplit('_$', 1)
    if len(parts) != 2:
        return

    base_service_part = parts[0]  # Everything before the last '_$'

    # Find all services that start with the base name followed by an underscore
    # e.g., if base is 'service', match 'service_gui', 'service_headless', etc.
    matching_services = [
        name for name in all_service_names
        if name.startswith(base_service_part + '_') and name != base_service_part
    ]

    # Add dashed edges to all matching services with parameter information
    for matching_service in matching_services:
        # Extract the parameter value from the matching service name
        # (everything after the base + _)
        param_value = matching_service[len(base_service_part + '_'):]  # Everything after base_

        # For parametrized dependencies, use a different dependency type to get dashed lines
        parametrized_dep_type = f'parametrized_{dep_type}'

        # For 'before' dependencies, reverse the edge direction
        if dep_type == 'before':
            edge_tuple = (
                matching_service, service_name, 'parametrized_after', f'@{param_value}'
            )
        else:
            edge_tuple = (
                service_name, matching_service, parametrized_dep_type, f'@{param_value}'
            )

        # Since edges is now always a list, just append if not already present
        if edge_tuple not in edges:
            edges.append(edge_tuple)


def build_dependency_graph(service_files):
    """
    Build a dependency graph from service files.

    Args:
        service_files (list): List of service file paths

    Returns:
        tuple: (nodes, edges) where nodes is a dict mapping service names to types and parametric info and
               edges is a list of (source, target, dependency_type) tuples
    """
    # Dictionary to store service name -> (type, has_parameters)
    nodes = {}
    edges = []  # Using list to maintain order, will handle duplicates manually

    # First pass: collect all service names and their types and parametric information
    service_infos = {}
    for service_file in service_files:
        service_info = parse_service_file(service_file)
        service_name = service_info['name']
        service_type = service_info['type']
        has_parameters = service_info['has_parameters']
        nodes[service_name] = (service_type, has_parameters)
        service_infos[service_file] = service_info

    # Second pass: parse dependencies and build edges
    for service_file, service_info in service_infos.items():
        service_name = service_info['name']
        service_dir = os.path.dirname(service_file)
        dependencies = service_info['dependencies']
        parametrized_dependencies = service_info['parametrized_dependencies']

        # Add regular dependency edges
        add_dependency_edges(service_name, dependencies, service_dir, nodes, edges)

        # Add parametrized dependency edges
        add_parametrized_dependency_edges(service_name, parametrized_dependencies, nodes, edges)

    return nodes, sorted(list(edges))


def build_dependency_graph_with_scopes(service_files_with_dir):
    """
    Build a dependency graph from service files with scope information.

    Args:
        service_files_with_dir (list): List of tuples (service_file_path, directory_label)

    Returns:
        tuple: (nodes, edges, scopes) where nodes is a dict mapping service names to types and parametric info,
               edges is a list of (source, target, dependency_type, param_label) tuples,
               scopes is a dict mapping directory labels to sets of service names
    """
    # Dictionary to store service name -> (type, has_parameters)
    nodes = {}
    edges = []  # Using list to maintain order, will handle duplicates manually
    scopes = {}  # Dictionary to store scope information: directory_label -> set of service names

    # First pass: collect all service names and their types and parametric information
    service_infos = {}
    for service_file, dir_label in service_files_with_dir:
        service_info = parse_service_file(service_file)
        service_name = service_info['name']
        service_type = service_info['type']
        has_parameters = service_info['has_parameters']
        nodes[service_name] = (service_type, has_parameters)
        service_infos[service_file] = service_info

        # Add service to its scope
        if dir_label not in scopes:
            scopes[dir_label] = set()
        scopes[dir_label].add(service_name)

    # Second pass: parse dependencies and build edges
    for service_file, dir_label in service_files_with_dir:
        service_info = service_infos[service_file]
        service_name = service_info['name']
        service_dir = os.path.dirname(service_file)
        dependencies = service_info['dependencies']
        parametrized_dependencies = service_info['parametrized_dependencies']

        # Add regular dependency edges
        add_dependency_edges(service_name, dependencies, service_dir, nodes, edges)

        # Add parametrized dependency edges
        add_parametrized_dependency_edges(service_name, parametrized_dependencies, nodes, edges)

    return nodes, sorted(list(edges)), scopes


def generate_hiearch_format(nodes, edges, target_services=None, scopes=None):
    """
    Generate hiearch YAML format from nodes and edges.

    Args:
        nodes (dict): Dictionary of service names to (their types, has_parameters)
        edges (list): List of (source, target, dependency_type, param_label) tuples
        target_services (list): List of target services to create a dedicated view for (None if all services)
        scopes (dict): Dictionary mapping directory labels to sets of service names (optional)

    Returns:
        str: hiearch YAML format string
    """
    # Initialize scopes to None if not provided to maintain backward compatibility
    if scopes is None:
        scopes = {}
    hiearch_data = {
        'nodes': [],
        'edges': [],
        'views': []
    }

    # Add scope nodes if scopes are provided
    if scopes:
        for scope_label in scopes.keys():
            scope_node = {
                'id': [scope_label, f"scope_{scope_label}"],  # [label, unique id] for scope
            }
            # Don't add style_notag for scope nodes to avoid using hh_dinit_scope
            hiearch_data['nodes'].append(scope_node)

    # Add nodes with styles based on service type
    for service_name, (service_type, has_parameters) in sorted(nodes.items()):
        # Add "@" suffix to service name if it supports parameters
        # For services with '@' in the name (instantiated parametric services), we don't add an extra '@'
        # Only add '@' for template services that are truly parametric (not instantiated)
        if has_parameters and '@' not in service_name:
            display_name = service_name + '@'  # Template service that supports parameters
        elif '@' in service_name:
            display_name = service_name  # Instantiated parametric service
        else:
            display_name = service_name  # Regular service

        style = get_style_for_service_type(service_type)

        # Create node with scope information if available
        node_dict = {
            'id': [display_name, service_name],  # [label, unique id] - label shows @ if parametric,
                                                 # id stays the same
            'style_notag': style
        }

        # Associate service with its scope if scopes are provided
        if scopes:
            for scope_label, service_set in scopes.items():
                if service_name in service_set:
                    node_dict['scope'] = f"scope_{scope_label}"  # Reference to the scope node
                    break

        hiearch_data['nodes'].append(node_dict)

    # Add edges with different styles based on dependency type
    for edge_data in edges:
        if len(edge_data) == 4:  # (source, target, dep_type, param_label)
            source, target, dep_type, param_label = edge_data
        else:  # backward compatibility for any 3-tuple edges
            source, target, dep_type = edge_data
            param_label = None

        edge_style = get_edge_style_for_dependency_type(dep_type)
        edge_dict = {
            'link': [source, target],  # Use actual node IDs, not display names
            'style': edge_style
        }

        # Add parameter label if it exists (for parametrized dependencies)
        if param_label:
            edge_dict['label'] = param_label

        hiearch_data['edges'].append(edge_dict)

    # Create view(s) based on whether specific services were selected
    if target_services:
        # Create a dedicated view for the selected services and their dependencies
        hiearch_data['views'].append({
            'id': 'dinit_service_selection',
            'nodes': target_services,
            'neighbours': 'recursive_out',
            'style': 'dinit_service_view'
        })

        # Also create an "all services" view
        hiearch_data['views'].append({
            'id': 'dinit_service_all',
            'style': 'dinit_service_view',
            'tags': ['default']
        })
    else:
        # Create a default view for all services
        hiearch_data['views'].append({
            'id': 'dinit_service_all',
            'style': 'dinit_service_view',
            'tags': ['default']
        })

    # Use safe_dump to avoid issues with special YAML characters
    return yaml.safe_dump(hiearch_data, default_flow_style=False, allow_unicode=True)


def find_common_prefix(directories):
    """Find the common prefix of directory paths considering path components."""
    if not directories:
        return ""

    # Split each directory path into components
    split_dirs = [os.path.normpath(d).split(os.sep) for d in directories]

    # Find the common path components
    common_parts = []
    for i in range(min(len(parts) for parts in split_dirs)):
        if all(parts[i] == split_dirs[0][i] for parts in split_dirs):
            common_parts.append(split_dirs[0][i])
        else:
            break

    # Join the common parts back into a path
    if common_parts:
        return os.sep.join(common_parts)

    # If no common prefix found, return empty string
    return ""


def write_style_file(filename):
    """Write the dinit_service.yaml style content to the specified file."""
    # Use importlib_resources to access the installed style file
    style_path = importlib_resources.files('hiearch_dinit.data.styles') / 'dinit_service.yaml'

    with open(style_path, 'r', encoding='utf-8') as source_file:
        style_content = source_file.read()

    with open(filename, 'w', encoding='utf-8') as target_file:
        target_file.write(style_content)


def find_common_prefix_and_suffix(directories):
    """Find the common prefix and suffix of directory paths considering path components."""
    if not directories:
        return "", ""

    # First, find the common prefix using os.path.commonpath
    common_prefix = os.path.commonpath(directories)

    # For suffix, we need to find common suffix components manually
    # Split each directory path into components
    split_dirs = [os.path.normpath(d).split(os.sep) for d in directories]

    # Normalize the common prefix to components to check for overlaps
    prefix_parts = os.path.normpath(common_prefix).split(os.sep) if common_prefix else []

    # Find the common path components from the end (excluding the common prefix part)
    # We need to look at the remaining parts after removing the common prefix
    remaining_parts_list = []
    for parts in split_dirs:
        if len(parts) >= len(prefix_parts):
            # Get the parts after the common prefix
            remaining_parts = parts[len(prefix_parts):] if len(prefix_parts) > 0 else parts
            remaining_parts_list.append(remaining_parts)

    # Find common suffix in the remaining parts
    common_suffix_parts = []
    if remaining_parts_list and all(len(rp) > 0 for rp in remaining_parts_list):
        min_remaining_len = min(len(rp) for rp in remaining_parts_list)

        for i in range(1, min_remaining_len + 1):
            # Check if all remaining parts lists have the same element at position -i (from the end)
            if all(len(rp) >= i and rp[-i] == remaining_parts_list[0][-i] for rp in remaining_parts_list):
                common_suffix_parts.insert(0, remaining_parts_list[0][-i])  # Insert at beginning to maintain order
            else:
                break

    # Join the common suffix parts back into a path
    common_suffix = os.sep.join(common_suffix_parts) if common_suffix_parts else ""

    # Check for overlap between prefix and suffix
    if prefix_parts and common_suffix_parts:
        # Calculate if prefix and suffix would overlap
        total_path = prefix_parts + common_suffix_parts
        min_total_parts = min(len(parts) for parts in split_dirs)
        if len(total_path) > min_total_parts:
            # There's an overlap, adjust the suffix
            overlap = len(total_path) - min_total_parts
            if overlap > 0:
                common_suffix_parts = common_suffix_parts[overlap:]
                common_suffix = os.sep.join(common_suffix_parts) if common_suffix_parts else ""

    # If there's no common suffix at the path component level, try to find common suffixes
    # within the directory names (last component of each path)
    if not common_suffix:
        # Extract the directory names (last component of each path)
        dir_names = [os.path.basename(d) for d in directories]

        # Find common suffix among directory names
        if len(dir_names) > 1:
            # Find the common suffix string among directory names
            common_suffix_str = ""
            min_len = min(len(name) for name in dir_names)

            # Check from the end of the strings
            for i in range(1, min_len + 1):
                if all(name[-i] == dir_names[0][-i] for name in dir_names):
                    common_suffix_str = dir_names[0][-i] + common_suffix_str
                else:
                    break

            # Only use the common suffix if it appears in all directory names
            if common_suffix_str and all(name.endswith(common_suffix_str) for name in dir_names):
                # Check if the common suffix is meaningful (not just a single character)
                if len(common_suffix_str) > 1:
                    common_suffix = common_suffix_str

    return common_prefix, common_suffix


def main():
    """Parse command line arguments and generate the dependency graph."""
    parser = argparse.ArgumentParser(
        description='Parse dinit service files and generate a dependency graph in hiearch YAML format.'
    )
    parser.add_argument(
        '-d', '--directories',
        nargs='+',
        help='Directories to traverse for dinit service files'
    )
    parser.add_argument(
        '-s', '--services',
        nargs='*',
        help='Optional list of service names to visualize (if not provided, all services are visualized)'
    )

    def output_type(x):
        if x == '-':
            return sys.stdout
        return open(x, 'w', encoding='utf-8')

    parser.add_argument(
        '-o', '--output',
        help='Output file (default: stdout)',
        type=output_type,
        default='-'
    )
    parser.add_argument(
        '-S', '--style',
        help='Output hiearch style to the given input file'
    )

    args = parser.parse_args()

    # If neither directories nor style arguments are specified, print help and exit
    if not args.directories and not args.style:
        parser.print_help()
        sys.exit(1)

    # If style argument is provided, write the style content to the specified file and exit
    if args.style:
        write_style_file(args.style)
        sys.exit(0)  # Exit after writing the style file

    # Find common prefix and suffix of directories
    if len(args.directories) == 1:
        # When only one directory is specified, remove common prefix of this directory and current directory
        current_dir = os.getcwd()
        directory = args.directories[0]

        # Resolve relative paths to absolute before prefix removal
        abs_current_dir = os.path.abspath(current_dir)
        abs_directory = os.path.abspath(directory)

        # Use os.path.commonpath to determine common prefix
        common_prefix = os.path.commonpath([abs_current_dir, abs_directory])

        common_suffix = ""
    else:
        # For multiple directories, use the custom function to find both common prefix and suffix
        resolved_directories = [os.path.abspath(d) for d in args.directories]
        common_prefix, common_suffix = find_common_prefix_and_suffix(resolved_directories)

    # Collect all service files from the provided directories with their directory info
    service_files_with_dir = []
    for directory in args.directories:
        if os.path.isdir(directory):
            service_files = get_services_from_directory(directory)
            # Remove common prefix and suffix from directory path for the scope label
            # Split the directory path into components
            dir_parts = os.path.normpath(directory).split(os.sep)

            # Remove common prefix components
            prefix_parts = os.path.normpath(common_prefix).split(os.sep) if common_prefix else []
            if prefix_parts and dir_parts[:len(prefix_parts)] == prefix_parts:
                dir_parts = dir_parts[len(prefix_parts):]

            # Remove common suffix components (complete path components)
            suffix_parts = os.path.normpath(common_suffix).split(os.sep) if common_suffix else []
            if suffix_parts and dir_parts[-len(suffix_parts):] == suffix_parts:
                dir_parts = dir_parts[:-len(suffix_parts)]

            # Join the remaining parts to form the label
            dir_label = os.sep.join(dir_parts) if dir_parts else directory  # fallback to original
            # if no parts remain

            # If there's still a common suffix that applies to directory names (within components),
            # apply it now
            if common_suffix and len(dir_parts) > 0:
                # Check if the common_suffix is within the last directory component (not a separate component)
                last_part = dir_parts[-1]
                # If common_suffix is part of the last component (not a separate component), remove it
                if last_part != common_suffix and last_part.endswith(common_suffix):
                    modified_last_part = last_part[:-len(common_suffix)]
                    dir_parts[-1] = modified_last_part
                    dir_label = os.sep.join(dir_parts)

            for service_file in service_files:
                service_files_with_dir.append((service_file, dir_label))
        else:
            sys.stderr.write(f'Warning: {directory} is not a directory, skipping.\n')

    # Build the dependency graph
    nodes, edges, scopes = build_dependency_graph_with_scopes(service_files_with_dir)

    # Generate and output the hiearch format to the specified output
    # Service filtering is handled automatically by hiearch based on view parameters
    hiearch_output = generate_hiearch_format(nodes, edges, target_services=args.services, scopes=scopes)

    args.output.write(hiearch_output)

    if args.output != '-':
        args.output.close()
