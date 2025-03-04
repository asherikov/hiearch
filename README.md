Introduction
============

`hiearch` is a CLI utility that generates diagrams from textual descriptions,
a.k.a., "diagrams as code". Unlike many other generators like `graphviz` it is
designed to support hierarchical decomposition and multiple views, in which
sense it is similar to <https://structurizr.com>. In other words, `hiearch`
generates multiple diagrams (views) from a single description, where each node
is a hierarchy of nodes, that is automatically expanded, collapsed, or hidden,
depending on configuration of each particular view. Currently, `hiearch` uses
`graphviz` to generate individual diagrams corresponding to views, but other
backends may be added in the future.

The main purpose of `hiearch` is graphical representation of complex systems,
but it is meant to be generic and may find other applications.

Why would anyone need another system diagram generator when there is a
multitude of tools that support UML, C4, etc? I believe that the most important
aspects of the system are its decomposition into components and connections
between them, `hiearch` provides just that, nothing more, so that you can focus
on documenting your system rather than fitting it into a specific design
framework.


Features
========

- `hiearch` does not use a DSL, but rather parses a set of input `yaml` files
  in arbitrary order. The file contents get composed into a single description,
  which, in turn, gets decomposed into views.

- Description files have flat structure without nesting or inclusion and
  contain lists of the following objects: nodes, edges, and views. Hierarchical
  relations between nodes are specified using node parameters.

- Unlike `graphviz`, `hiearch` does not have a concept of subgraphs: each node
  may automatically become a subgraph depending on a view.

- `hiearch` is also somewhat stricter than `graphviz`: for example, all nodes
  must be defined explicitly and cannot be deduced from edge definitions.

- View is not the same thing as `graphviz` layer
  <https://graphviz.org/docs/attrs/layer/>: `graphviz` places all nodes on each
  layer and simply makes some of them invisible, which results in awkward
  spacing.

- `hiearch` allows nodes to have multiple parent nodes, which is referenced
  here as 'multiscoping'. The idea is, of course, to show parents in different
  views, for example, to outline system from logical or hardware point of view.
  However, it is possible to visualize all parents in the same diagram, which
  may be a bit kinky.

- `hiearch` supports label templates, which facilitates automatic generation of
  URLs, tables, icon inclusions, etc.


Examples
========

Command line options
--------------------

```
usage: hiearch [-h] [-o OUTPUT] [-f FORMAT] <filename> [<filename> ...]

Generates diagrams

positional arguments:
  <filename>            Input files

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output directory [hiearch]
  -f FORMAT, --format FORMAT
                        Output format [SVG]
```


Trivial
-------

<table>
    <tr>
        <td>
            <pre>
-----------------------------------------------------------
nodes:
    - id: ["Test 1", test1]  # [label, unique id]
edges:
    - link: [test1, test1]   # [from node id, to node id]
views:
    - id: view1              # unique id / output filename
      nodes: [test1]         # nodes to include
            </pre>
        </td>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/07_trivial/view1.svg" alt="view1" />
            <br />
            view1
        </td>
    </tr>
</table>


Node relations
--------------

<table>
    <tr>
        <td rowspan="3">
            <pre>
-----------------------------------------------------------
nodes:
    - id: ["Test 1", test1]
      graphviz:  # set graphviz attributes directly
        fillcolor: grey
        style: filled
    - id: ["Test 2", test2]
      graphviz:  # set graphviz attributes directly
        fillcolor: aqua
        style: filled
    - id: ["Test 3", test3]
      scope: test1  # test3 is contained in test1
      style: test2  # test3 inherits all test2 attributes
edges:
    - link: [test3, test3]
views:
    - id: view1
      nodes: [test2, test3]
    - id: view2  # test1 is shown as subgraph
      nodes: [test1, test3]
    - id: view3
      nodes: [test1, test2]
            </pre>
        </td>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/08_node_realations/view1.svg" alt="view1" />
            <br />
            view1
        </td>
    </tr>
    <tr>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/08_node_realations/view2.svg" alt="view2" />
            <br />
            view2
        </td>
    </tr>
    <tr>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/08_node_realations/view3.svg" alt="view3" />
            <br />
            view3
        </td>
    </tr>
</table>


Node selection using tags
-------------------------

<table>
    <tr>
        <td rowspan="2">
            <pre>
-----------------------------------------------------------
nodes:
    - id: ["Test 1", test1]
      # tags: ["default"] if not specified
    - id: ["Test 2", test2]
      tags: ["test2_tag"]
edges:
    - link: [test1, test1]
    - link: [test2, test2]
views:
    - id: view1
      tags: ["test2_tag"]
    - id: view2
      tags: ["default"]
            </pre>
        </td>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/09_tags/view1.svg" alt="view1" />
            <br />
            view1
        </td>
    </tr>
    <tr>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/09_tags/view2.svg" alt="view2" />
            <br />
            view2
        </td>
    </tr>
</table>

<table>
    <tr>
        <td>
            <pre>
-----------------------------------------------------------
nodes:
    - id: ["Test 1", test1]
# if no views are specified explicitly, a default one is
# added with 'tags: ["default"]'
            </pre>
        </td>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/10_minimal/default.svg" alt="default" />
            <br />
            default
        </td>
    </tr>
</table>



Neighbour node selection
------------------------

<table>
    <tr>
        <td rowspan="4">
            <pre>
-----------------------------------------------------------
nodes:
    - id: ["Test 1", test1]
    - id: ["Test 2", test2]
    - id: ["Test 3", test3]
      scope: test2
edges:
    - link: [test1, test3]
views:
    - id: view1
      nodes: [test1]
      # nodes must be specified explicitly
      # neighbours: explicit
    - id: view2
      nodes: [test1]
      # add connected nodes
      neighbours: direct
    - id: view3
      nodes: [test1]
      # add top most parents of connected nodes
      neighbours: parent
    - id: view4
      # all three together
      tags: ["default"]
            </pre>
        </td>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/11_neighbors/view1.svg" alt="view1" />
            <br />
            view1
        </td>
    </tr>
    <tr>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/11_neighbors/view2.svg" alt="view2" />
            <br />
            view2
        </td>
    </tr>
    <tr>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/11_neighbors/view3.svg" alt="view3" />
            <br />
            view3
        </td>
    </tr>
    <tr>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/11_neighbors/view4.svg" alt="view4" />
            <br />
            view4
        </td>
    </tr>
</table>



View styles
-----------

<table>
    <tr>
        <td rowspan="2">
            <pre>
-----------------------------------------------------------
nodes:
    - id: ["Test 1", test1]
edges:
    - link: [test1, test1]
views:
    - id: style
      nodes: []  # explicitly empty view is not rendered
      # defaults, overriden by node/edge attributes
      graphviz:
          graph:
              style: filled
              bgcolor: coral
          node:
              fontsize: "24"
              fontname: times
          edge:
              dir: both
    - id: styled
      nodes: [test1]
      style: style  # inherit style from another view
    - id: plain
      nodes: [test1]
            </pre>
        </td>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/12_view_style/styled.svg" alt="styled" />
            <br />
            styled
        </td>
    </tr>
    <tr>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/12_view_style/plain.svg" alt="plain" />
            <br />
            plain
        </td>
    </tr>
</table>


Edge labels
-----------

<table>
    <tr>
        <td rowspan="2">
            <pre>
-----------------------------------------------------------
nodes:
    - id: ["Test 1", test1]
    - id: ["Test 2", test2]
edges:
    - link: [test1, test1]
      label: 'test1_edge'
    - link: [test2, test2]
      label: ['tail', 'middle', 'head']
views:
    - id: view1
      nodes: [test1]
    - id: view2
      nodes: [test2]
            </pre>
        </td>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/13_edge_labels/view1.svg" alt="view1" />
            <br />
            view1
        </td>
    </tr>
    <tr>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/13_edge_labels/view2.svg" alt="view2" />
            <br />
            view2
        </td>
    </tr>
</table>


Edge styles
-----------

<table>
    <tr>
        <td rowspan="3">
            <pre>
-----------------------------------------------------------
nodes:
    - id: ["Test 1", test1]
    - id: ["Test 2", test2]
    - id: ["Test 3", test3]
    # helper node to define "invisible" edges used purely
    # as style templates
    - id: ["StyleNode", stylenode]
      # invisible unless this tag is requested in a view
      tags: ["mystyle"]
edges:
    # "pure" style link
    - link: [stylenode, stylenode, stylelink]
      graphviz:
        color: red
    - link: [test1, test1]
      label: 'test1'
      style: stylelink
    # optional third link parameter introduces an explicit
    # id, which must be unique
    - link: [test2, test2, edge2]
      # style can be referenced by link attribute
      style: [test1, test1]
      graphviz:
        dir: both
    - link: [test3, test3]
      # style can also be an explicit id
      style: edge2
      graphviz:
        color: blue
views:
    - id: view1
      nodes: [test1]
    - id: view2
      nodes: [test2]
    - id: view3
      nodes: [test3]
            </pre>
        </td>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/14_edge_style/view1.svg" alt="view1" />
            <br />
            view1
        </td>
    </tr>
    <tr>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/14_edge_style/view2.svg" alt="view2" />
            <br />
            view2
        </td>
    </tr>
    <tr>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/14_edge_style/view3.svg" alt="view3" />
            <br />
            view3
        </td>
    </tr>
</table>



Formatted labels
----------------

```
nodes:
    - id: ["Test 1", test1]
      # https://www.svgrepo.com/svg/479843/duck-toy-illustration-3
      # https://www.svgrepo.com/svg/479405/casa-pictogram-5
      graphviz:
        node_label_format: '<<table><tr><td><img src="https://raw.githubusercontent.com/asherikov/hiearch/master/icon_{id}.svg"/></td><td>{label}</td></tr></table>>'
        scope_label_format: '<<table><tr><td><img src="https://raw.githubusercontent.com/asherikov/hiearch/master/icon_{id}.svg"/></td><td>Scope: {label}</td></tr></table>>'
    - id: ["Test 2", test2]
      scope: test1
    - id: ["Test 3", test3]
      tags: []
      substitutions:
        suffix: '!'
      graphviz:
        node_label_format: '<<table><tr><td><img src="https://raw.githubusercontent.com/asherikov/hiearch/master/icon_{style}.svg"/></td><td>{label}{suffix}</td></tr></table>>'
    - id: ["Test 4", test4]
      style: test3
views:
    - id: view1
      nodes: [test1]
    - id: view2
      nodes: [test1, test2]
    - id: view3
      nodes: [test4]
```

Note that SVG with other embedded SVG is not always rendered properly, and
embedded pictures may get lost during conversion to other formats. The PNG
files below were generated with `rsvg-convert view1.svg --format=png
--output=view1.png`, exporting directly to PNG using graphviz won't work. Also,
the included images must be present in the output directory.

<table>
    <tr>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/15_formatted_labels/view1.png" alt="view1" />
            <br />
            view1
        </td>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/15_formatted_labels/view2.png" alt="view2" />
            <br />
            view2
        </td>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/15_formatted_labels/view3.png" alt="view3" />
            <br />
            view3
        </td>
    </tr>
</table>



Multiscoping
------------
<table>
    <tr>
        <td>
            <pre>
-----------------------------------------------------------
nodes:
    # root nodes
    - id: ["Test 1", test1]
    - id: ["Test 2", test2]
    # child nodes
    - id: ["Test 3", test3]
      # a child of both root nodes: if both scopes are
      # present in a view they are automatically ranked
      # to form a hierarchy
      scope: [test1, test2]
    # Both root nodes also include non-shared nodes.
    # Since is not possible to visualize overlaping
    # subgraphs with graphviz, one of them is going to be
    # divided into two parts.
    - id: ["Test 4", test4]
      scope: test2
    - id: ["Test 5", test5]
      scope: [test1]
            </pre>
        </td>
        <td align="center">
            <img src="https://raw.githubusercontent.com/asherikov/hiearch/master/test/06_multiscope/default.svg" alt="default" />
            <br />
            default
        </td>
    </tr>
</table>


