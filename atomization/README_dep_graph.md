# Dependency Graph Extraction Tool

This command-line tool extracts and parses renderDot content from HTML files into structured JSON format. It's designed to analyze dependency graphs from mathematical theorem systems.

## Features

The script extracts and categorizes:

- **Graph attributes**: Global graph properties
- **All nodes**: Complete list of nodes with their attributes
- **All edges**: Complete list of edges with their attributes
- **Ellipse nodes**: Nodes with `shape=ellipse` (theorems and lemmas)
- **Box nodes**: Nodes with `shape=box` (definitions)
- **Dashed edges**: Edges with `style=dashed`
- **Other style edges**: Edges with other styles
- **Modal container IDs**: All dep-modal-container element IDs

## Installation

Make sure you have the required dependencies:

```bash
pip install lxml
```

Also install Lean Blueprint.

```bash
pip install leanblueprint
```

Run the following to generate the web blueprint before running the extraction script.

```bash
leanblueprint web
```

## Usage

### Basic Usage

From the repo root, run

```bash
python3 atomization/extract_dep_graph.py
```

This will use the default HTML file (`blueprint/web/dep_graph_document.html`) and save output to `dep_graph.json`.

### Custom HTML File

```bash
python3 extract_dep_graph.py /path/to/your/file.html
```

### Custom Output File

```bash
python3 extract_dep_graph.py -o my_output.json file.html
```

### Quiet Mode

```bash
python3 extract_dep_graph.py --quiet file.html
```

### Skip Analysis

```bash
python3 extract_dep_graph.py --no-analysis file.html
```

### Command Line Options

```bash
python3 extract_dep_graph.py --help
```

Available options:
- `html_file`: Path to HTML file (optional, has default)
- `-o, --output`: Output JSON file path (default: `dep_graph.json`)
- `--quiet`: Quiet mode - minimal output
- `--no-analysis`: Skip detailed analysis output

## Output JSON Structure

The generated JSON file contains:

```json
{
  "graph": { /* Global graph attributes */ },
  "node": { /* Default node attributes */ },
  "edge": { /* Default edge attributes */ },
  "nodes": [
    {
      "id": "node_id",
      "attributes": { /* node-specific attributes */ }
    }
  ],
  "edges": [
    {
      "id": "source->target",
      "source": "source_node",
      "target": "target_node",
      "attributes": { /* edge-specific attributes */ }
    }
  ],
  "node_info": [ /* List of dep-modal-container IDs */ ]
}
```

### Using the Structured Data

```python
import json

# Load the structured data
with open('dep_graph.json', 'r') as f:
    data = json.load(f)

# Access different components
print(f"Total nodes: {len(data['nodes'])}")
print(f"Total edges: {len(data['edges'])}")
print(f"Modal containers: {len(data['node_info'])}")

# Analyze node types
ellipse_nodes = [n for n in data['nodes'] if n['attributes'].get('shape') == 'ellipse']
box_nodes = [n for n in data['nodes'] if n['attributes'].get('shape') == 'box']
print(f"Ellipse nodes: {len(ellipse_nodes)}")
print(f"Box nodes: {len(box_nodes)}")

# Analyze edge types
dashed_edges = [e for e in data['edges'] if e['attributes'].get('style') == 'dashed']
print(f"Dashed edges: {len(dashed_edges)}")
```

## Examples

### Basic Analysis

```bash
# Extract from default file
python3 extract_dep_graph.py

# Extract from custom file with custom output
python3 extract_dep_graph.py -o analysis.json /path/to/graph.html
```

### Batch Processing

```bash
# Process multiple files quietly
for file in *.html; do
    python3 extract_dep_graph.py --quiet -o "${file%.html}.json" "$file"
done
```

### Advanced Analysis

```python
import json
import networkx as nx

# Load the extracted data
with open('dep_graph.json', 'r') as f:
    data = json.load(f)

# Create a NetworkX graph for analysis
G = nx.DiGraph()

# Add nodes
for node in data['nodes']:
    G.add_node(node['id'], **node['attributes'])

# Add edges
for edge in data['edges']:
    G.add_edge(edge['source'], edge['target'], **edge['attributes'])

# Analyze the graph
print(f"Nodes: {G.number_of_nodes()}")
print(f"Edges: {G.number_of_edges()}")
print(f"Strongly connected components: {nx.number_strongly_connected_components(G)}")
```

## Dependencies

- `lxml`: For HTML parsing and DOM manipulation
- `json`: For data serialization (built-in)
- `dataclasses`: For structured data representation (built-in)
- `argparse`: For command-line argument parsing (built-in)

## Output Files

- `dep_graph.json` (default): Complete structured data in JSON format
- Console output: Detailed analysis and sample data (unless `--quiet` is used)

## Use Cases

This tool is useful for:
- **Graph Analysis**: Understanding mathematical theorem dependencies
- **Visualization**: Creating custom graph visualizations
- **Data Mining**: Extracting patterns and relationships
- **Research**: Analyzing formal mathematical systems
- **Documentation**: Generating reports about dependency structures
- **Automation**: Batch processing of multiple graph files

## Troubleshooting

### Common Issues

1. **File not found**: Ensure the HTML file path is correct
2. **No renderDot content**: The HTML file must contain `.renderDot()` calls
3. **Permission errors**: Ensure write permissions for output directory

### Debug Mode

For debugging, you can examine the intermediate steps:

```python
# In the script, you can add debug prints to see:
# - Extracted renderDot string length
# - Number of elements found
# - Parsing progress
```
