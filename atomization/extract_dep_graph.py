#!/usr/bin/env python3
"""
Script to parse renderDot content string and create a depGraph object.
"""

import re
import argparse
from dataclasses import dataclass
from typing import Dict, List, Any
from lxml import html
from pathlib import Path

def parse_attributes(attr_string: str) -> Dict[str, Any]:
    """Parse attribute string like '[color=red, shape=box]' into a dictionary."""
    attrs = {}

    # Remove brackets
    attr_string = attr_string.strip('[]')

    # Split by comma and parse each attribute
    for attr in attr_string.split(','):
        attr = attr.strip()
        if '=' in attr:
            key, value = attr.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"\'')
            attrs[key] = value

    return attrs

def get_node_info(dom):
    """
    Extract all IDs of div elements with class "dep-modal-container".

    Args:
        dom: The parsed DOM object (lxml.html.HtmlElement)

    Returns:
        list: List of IDs found
    """
    try:
        # Find all div elements with class "dep-modal-container"
        modal_divs = dom.xpath('//div[@class="dep-modal-container"]')

        ids = {}
        for div in modal_divs:
            div_id = div.get('id')
            # Get the content of the div, stripping away the div container itself
            if len(div) != 1:
                raise ValueError(f"Div has {len(div)} children, expected 1")
            div_content = html.tostring(div[0], pretty_print=True, encoding='unicode')
            # check that div_id ends with "_modal"
            if div_id.endswith('_modal'):
                div_id = div_id.replace('_modal', '')
                ids[div_id] = div_content
            else:
                raise ValueError(f"Div ID does not end with _modal: {div_id}")

            print(f"Div ID: {div_id}")
            print(f"Div content: {div_content}")
            if div_id:
                ids[div_id] = div_content
            else:
                raise ValueError(f"Div ID is None: {div_id}")

        return ids

    except Exception as e:
        print(f"Error extracting modal IDs: {e}")
        return []


def get_dep_graph_string(dom) -> str:
    """
    Extract the renderDot content string from the DOM object.

    Args:
        dom: The parsed DOM object (lxml.html.HtmlElement)

    Returns:
        str: The renderDot content string, or None if not found
    """
    try:
        # Find the script element containing the renderDot call
        script_elements = dom.xpath('//script')

        for script in script_elements:
            script_text = script.text_content() if script.text else ""
            if ".renderDot(`strict digraph" in script_text:
                # Extract the part starting with ".renderDot(`strict digraph"
                start_pattern = r"\.renderDot\(`strict digraph"
                match = re.search(start_pattern, script_text)
                if match:
                    start_pos = match.start()
                    # Extract from the start of the pattern to the end of the script
                    extracted_content = script_text[start_pos:]

                    # Extract just the DOT content between backticks
                    dot_pattern = r"\.renderDot\(`([^`]*)`\)"
                    dot_match = re.search(dot_pattern, extracted_content)
                    if dot_match:
                        return dot_match.group(1)

        return None

    except Exception as e:
        print(f"Error processing DOM: {e}")
        return None


def get_dep_graph(dom, node_info: List[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Parse the renderDot content from DOM and create a dictionary of nodes with ID as key and attributes as value.

    Args:
        dom: The parsed DOM object (lxml.html.HtmlElement)
        node_info (List[str], optional): List of dep-modal-container IDs

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of nodes with ID as key and attributes as value
    """
    # Extract renderDot content from DOM
    renderdot_string = get_dep_graph_string(dom)

    if not renderdot_string:
        print("Could not extract renderDot content from DOM")
        return {}

    # Remove the outer structure and extract the content
    # The content starts with "strict digraph "" {" and ends with "}"
    if not renderdot_string.startswith('strict digraph "" {'):
        print("Content doesn't start with expected pattern")
        print("First 100 characters:", repr(renderdot_string[:100]))
        return {}

    # Extract content between the braces
    start_pos = len('strict digraph "" {')
    end_pos = renderdot_string.rfind('}')

    if end_pos == -1:
        print("Could not find closing brace")
        return {}

    content = renderdot_string[start_pos:end_pos]

    # The content is all on one line with tabs, so we need to split it properly
    # Split by semicolons to get individual elements
    elements = content.split(';')
    edges = {}
    nodes = {}

    # Process each element
    for element in elements:
        element = element.strip()
        if not element:
            continue

        # Skip graph, node, and edge attribute declarations as they are no longer stored
        if element.startswith('graph [') or element.startswith('node [') or element.startswith('edge ['):
            continue

        # Parse individual nodes (format: "node_id" [attributes] or node_id [attributes])
        if '[' in element and ']' in element and '->' not in element:
            node_attr = parse_node_element(element)
            if node_attr:
                attributes = node_attr['attributes']
                attributes['kind'] = ""
                attributes['content'] = ""
                attributes['type-status'] = ""
                attributes['term-status'] = ""
                attributes['type-dependencies'] = []
                attributes['term-dependencies'] = []
                if 'shape' in attributes:
                    if 'shape' in attributes and attributes['shape'] == 'ellipse':
                        attributes['kind'] = 'theorem'
                    elif attributes['shape'] == 'box':
                        attributes['kind'] = 'definition'
                    else:
                        raise ValueError(f"Unknown shape: {attributes['shape']}")
                    attributes.pop('shape')
                else:
                    raise ValueError(f"Unknown shape: {attributes['shape']}")
                if 'color' in attributes:
                    if attributes['color'] == 'green':
                        attributes['type-status'] = 'stated'
                    elif attributes['color'] == 'blue':
                        attributes['type-status'] = 'can-state'
                    elif attributes['color'] == '#FFAA33':
                        attributes['type-status'] = 'not-ready'
                    elif attributes['color'] == 'darkgreen':
                        attributes['type-status'] = 'mathlib'
                    else:
                        attributes['type-status'] = 'unrecognized'
                    attributes.pop('color')
                else:
                     attributes['type-status'] = 'unknown'
                if 'fillcolor' in attributes:
                    if attributes['fillcolor'] == '#9CEC8B':
                        attributes['term-status'] = 'proved'
                    elif attributes['fillcolor'] == '#B0ECA3':
                        attributes['term-status'] = 'defined'
                    elif attributes['fillcolor'] == '#A3D6FF':
                        attributes['term-status'] = 'can-prove'
                    elif attributes['fillcolor'] == '#1CAC78':
                        attributes['term-status'] = 'fully-proved'
                    else:
                        attributes['term-status'] = 'unrecognized'
                    attributes.pop('fillcolor')
                else:
                    attributes['term-status'] = 'unknown'
                if 'label' in attributes:
                    if attributes['label'] != node_attr['id']:
                        raise ValueError(f"Node label mismatch: {attributes['label']} != {node_attr['id']}")
                    attributes.pop('label')
                else:
                    raise ValueError(f"No label found in node attributes: {attributes}")
                if 'style' in attributes:
                    if attributes['style'] != 'filled':
                        raise ValueError(f"Unknown style: {attributes['style']}")
                    attributes.pop('style')
                nodes[node_attr['id']] = attributes

        # Parse individual edges (format: source -> target [attributes])
        elif '->' in element:
            edge_info = parse_edge_element(element)
            if edge_info:
                edges[edge_info['id']] = edge_info['attributes']

    # Merge node_info with nodes
    if node_info:
        for node_id, content in node_info.items():
            if node_id not in nodes:
                raise ValueError(f"Node ID '{node_id}' from node_info not found in parsed nodes")
            nodes[node_id]['content'] = content

    if edges:
        for _, attributes in edges.items():
            source = attributes['source']
            target = attributes['target']
            if source not in nodes or target not in nodes:
                raise ValueError(f"Source or target node not found in nodes: {source} or {target}")
            if 'style' in attributes and attributes['style'] == 'dashed':
                if 'type-dependencies' not in nodes[source]:
                    nodes[source]['type-dependencies'] = [target]
                else:
                    nodes[source]['type-dependencies'].append(target)
            else:
                if 'term-dependencies' not in nodes[source]:
                    nodes[source]['term-dependencies'] = [target]
                else:
                    nodes[source]['term-dependencies'].append(target)
    return nodes


def parse_node_element(line: str) -> Dict[str, Any]:
    """Parse a node element line and return node information."""
    # Pattern: "node_id" [attributes] or node_id [attributes]
    # Handle both quoted and unquoted node IDs

    # Find the first bracket
    bracket_pos = line.find('[')
    if bracket_pos == -1:
        return None

    # Extract node ID (everything before the first '[')
    node_id_part = line[:bracket_pos].strip()

    # Remove quotes if present
    node_id = node_id_part.strip('"\'')

    # Extract attributes
    attr_start = line.find('[')
    attr_end = line.rfind(']')
    if attr_start == -1 or attr_end == -1:
        return {'id': node_id, 'attributes': {}}

    attr_string = line[attr_start:attr_end + 1]
    attributes = parse_attributes(attr_string)

    return {
        'id': node_id,
        'attributes': attributes
    }


def parse_edge_element(line: str) -> Dict[str, Any]:
    """Parse an edge element line and return edge information."""
    # Pattern: source -> target [attributes]

    # Find the arrow
    arrow_pos = line.find('->')
    if arrow_pos == -1:
        return None

    # Extract source and target
    source = line[:arrow_pos].strip().strip('"\'')
    remaining = line[arrow_pos + 2:].strip()

    # Find attributes
    attr_start = remaining.find('[')
    if attr_start != -1:
        target = remaining[:attr_start].strip().strip('"\'')
        attr_end = remaining.rfind(']')
        if attr_end != -1:
            attr_string = remaining[attr_start:attr_end + 1]
            attributes = parse_attributes(attr_string)
        else:
            attributes = {}
    else:
        target = remaining.strip('"\'')
        attributes = {}

    attributes['source'] = source
    attributes['target'] = target
    return {
        'id': f"{source}->{target}",
        'attributes': attributes
    }

def save_depgraph_to_json(nodes: Dict[str, Dict[str, Any]], output_file: str):
    """Save the dependency graph to a JSON file."""
    import json

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(nodes, f, indent=2, ensure_ascii=False)

    print(f"✓ Dependency graph saved to {output_file}")


def main():
    """Main function with command-line argument parsing."""
    parser = argparse.ArgumentParser(
        description="Extract and parse renderDot content from HTML files into structured JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Use default HTML file
  %(prog)s /path/to/file.html                 # Use custom HTML file
  %(prog)s -o my_output.json file.html        # Custom output file
  %(prog)s --quiet file.html                  # Quiet mode (minimal output)
        """
    )

    parser.add_argument(
        'html_file',
        nargs='?',
        default='blueprint/web/dep_graph_document.html',
        help='Path to the HTML file containing renderDot content (default: %(default)s)'
    )

    parser.add_argument(
        '-o', '--output',
        default='atomization/dep_graph.json',
        help='Output JSON file path (default: %(default)s)'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Quiet mode - minimal output'
    )

    parser.add_argument(
        '--no-analysis',
        action='store_true',
        help='Skip detailed analysis output'
    )

    args = parser.parse_args()

    # Check if file exists
    if not Path(args.html_file).exists():
        print(f"Error: File '{args.html_file}' does not exist.")
        return 1

    if not args.quiet:
        print(f"Extracting renderDot content from: {args.html_file}")

    # Read the HTML file and parse it into a DOM object
    with open(args.html_file, 'r', encoding='utf-8') as file:
        html_content = file.read()

    # Parse the HTML content into a DOM object
    dom = html.fromstring(html_content)

    # Extract node info from DOM
    node_info = get_node_info(dom)
    if not args.quiet:
        print(f"✓ Found {len(node_info)} dep-modal-container elements")
        if node_info:
            print(f"Sample modal container IDs: {list(node_info.keys())[:3]}{'...' if len(node_info) > 3 else ''}")

    # Parse the renderDot content from DOM
    if not args.quiet:
        print("Parsing renderDot content from DOM...")
    nodes = get_dep_graph(dom, node_info)

    # Save the structured data to JSON
    save_depgraph_to_json(nodes, args.output)

    return 0


if __name__ == "__main__":
    main()
