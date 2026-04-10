---
name: hiearch
description: Generate hierarchical decomposition diagrams and views using the hiearch tool. Use when creating architecture diagrams, package dependency visualizations, state machine diagrams, use case diagrams, or any hierarchical structure visualization. Supports Graphviz output in SVG and other formats.
---

# Hiearch

## Overview

Hiearch is a diagram generator that creates hierarchical decomposition visualizations from YAML configuration files. It processes input files to generate structured diagrams showing relationships between entities (nodes and edges) with customizable views and styling.

## When to Use This Skill

This skill should be used when:
- Generating architecture diagrams showing package hierarchies
- Creating state machine visualizations
- Building use case diagrams
- Visualizing hierarchical decomposition of systems
- Creating structured views of complex relationships
- Generating documentation diagrams with consistent styling

## Core Concepts

### Input Files
Hiearch processes YAML files that define:
- **Views**: Different perspectives on the hierarchy for selective node visualization
- **Nodes**: Entities in the hierarchy with IDs, labels, and properties
- **Edges**: Relationships between nodes
- **Styles**: Visual formatting options for nodes and edges (colors, shapes, fonts)

### Views
Views define which nodes are visualized and how they are selected:
- **hh_state_machine_view**: State machine diagrams
- **hh_use_case_view**: Use case diagrams
- **default**: Fallback view

Views are primarily intended for selective visualization of nodes. Visualization style is a secondary feature.

### Node Selection

Nodes can be selected using several methods:

#### Tags
Assign tags to nodes and reference them in views:
```yaml
nodes:
    - id: mynode
      tags: [important, core]

views:
    - id: core_view
      tags: [core]
```

#### Explicit Node IDs
List specific node IDs in the view:
```yaml
views:
    - id: specific
      nodes: [node1, node2, node3]
```

#### Neighbour Selection
Control which connected nodes are included:
- `explicit`: Only explicitly listed nodes
- `direct`: Nodes directly connected to selected nodes
- `parent`: Parent nodes up the hierarchy
- `recursive_in`: Recursively select nodes connected inward
- `recursive_out`: Recursively select nodes connected outward
- `recursive_all`: Both recursive_in and recursive_out

#### View Expansion
Automatically generate expanded views for specific nodes:
```yaml
views:
    - id: packages
      nodes: [root_node]
      expand: [recursive_all]
```

This generates separate diagrams for each node showing its subtree.

### Output Formats
- **SVG**: Scalable Vector Graphics (default)
- **svg:cairo**: SVG with embedded images (recommended when nodes include external image files)
- Other Graphviz-supported formats (PNG, PDF, etc.)

## Usage

### Basic Command

```bash
hiearch <input-file.yaml> [options]
```

### Options

- `-o OUTPUT`, `--output OUTPUT`: Output directory (default: current directory)
- `-f FORMAT`, `--format FORMAT`: Output format (default: svg)
- `-t TEMP_DIR`, `--temp-dir TEMP_DIR`: Temporary files output directory (defaults to output directory)
- `-r DIR`, `--resource-dirs DIR`: Directories to search for graphical resources (can be specified multiple times)
- `-i [DIR]`, `--install-skill [DIR]`: Install hiearch skill to coding agent skill directory
- `-h`, `--help`: Show help message

### Examples

Generate diagram from a YAML configuration:
```bash
hiearch config.yaml -o ./diagrams
```

Generate self-contained SVG with embedded images:
```bash
hiearch config.yaml -o ./diagrams -f svg:cairo
```

Install skill to default directory:
```bash
hiearch -i
```

Install skill to custom directory:
```bash
hiearch -i /custom/path/.qwen/skills/hiearch
```

Generate in PNG format:
```bash
hiearch config.yaml -o ./output -f png
```

Process multiple input files:
```bash
hiearch file1.yaml file2.yaml -o ./diagrams
```

## Input File Structure

### Basic View Definition

```yaml
views:
    - id: my_view
      nodes: [root_node]
      neighbours: recursive_all
      expand: [recursive_all]
```

### Node and Edge Definitions

```yaml
nodes:
    - id: root
      label: Root Node
      tags: [core]
    - id: child1
      label: Child One
      scope: root

edges:
    - in: root
      out: child1
      label: connects to
```

### Node and Edge Styles

Prefer setting style of nodes and edges using node and edge styles instead of styling options provided in the views:

```yaml
nodes:
    - id: mynode
      label: My Node
      graphviz:
          shape: box
          style: "rounded,filled"
          fillcolor: lightblue

edges:
    - in: node1
      out: node2
      graphviz:
          color: blue
          style: bold
```

## Installation

Hiearch should be installed with pipx:

```bash
pipx install hiearch
```

Verify installation:
```bash
hiearch --help
```

### Installing Coding Agent Skill

To install the hiearch skill for coding agents:

```bash
hiearch -i
```

This will install the skill to the default agent skill directory. Restart the coding agent to activate it.

For custom installation paths:
```bash
hiearch -i /path/to/agent/skills/hiearch
```

## Best Practices

1. **Define Clear Views**: Each view should have a distinct purpose and not be empty
2. **Use Node and Edge Styles**: Prefer setting style of nodes and edges using node and edge styles instead of styling options provided in the views
3. **Organize Input Files**: Keep YAML configuration files in a dedicated directory (e.g., `diagrams/` or `docs/diagrams/`)
4. **Use Meaningful IDs**: Node and view IDs should be descriptive and follow naming conventions
5. **Leverage Node Selection Features**: Use tags, explicit IDs, neighbour selection, and expansion options to control which nodes appear in each view
6. **Output Organization**: Use the `-o` flag to organize generated diagrams in a dedicated directory
7. **Use svg:cairo for Embedded Images**: When node styles include other image files, use svg:cairo format to embed them in the output

## Common Patterns

### State Machine Diagram

State machine views are built-in and can be referenced in input files to generate state transition diagrams.

### Use Case Diagram

Use case views are built-in and can be referenced to generate use case relationship diagrams.

## Troubleshooting

### "All views are empty" Error
This occurs when no nodes match the view definitions. Ensure your input files define entities that match the view criteria.

### Missing Output Files
Check that the output directory exists and is writable. Use `-t` to specify a separate temp directory if needed.

### Format Issues
Verify the output format is supported by Graphviz. SVG is the most reliable and recommended format. Use svg:cairo when nodes include external image files.
