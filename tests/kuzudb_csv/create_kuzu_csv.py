from collections import defaultdict
import json

# THE SOURCE OF TRUE TEST DATA IS THE NEO4J CSV FILES

# Read the neo4j files and create equivalent CSV files for KuzuDB

# For the node files, this means creating a different CSV for each cateogory.
# And we need to break out the properties into separate columns.

# First, read in all the nodes from the Neo4j file
# use csv to handle the double quotes
import csv
import os

delim = "\t"

# If the nodes and edge directories don't exist, create them
if not os.path.exists("tests/kuzudb_csv/nodes"):
    os.makedirs("tests/kuzudb_csv/nodes")
if not os.path.exists("tests/kuzudb_csv/edges"):
    os.makedirs("tests/kuzudb_csv/edges")

#Now on to the nodes files
csv.register_dialect("myalect", escapechar="\\")
with open("tests/neo4j_csv/nodes.csv", "r") as f:
    csv_reader = csv.reader(f, dialect="myalect")
    lines = list(csv_reader)

# Create a dictionary to hold the nodes by category
nodes_by_category = defaultdict(list)
node_to_category = {}
for line in lines[1:]:  # Skip the header
    category = line[1]
    nodes_by_category[category].append(line)
    node_id = line[0]
    node_to_category[node_id] = category

# Now, write each category to a separate KuzuDB CSV file
for category, nodes in nodes_by_category.items():
    #figure out the properties for this category
    category_props = set()
    for node in nodes:
        if len(node) > 3:
            props = node[3]
            props_dict = json.loads(props)
            category_props.update(props_dict.keys())
    props = list(category_props)
    with open(f"tests/kuzudb_csv/nodes/{category}.csv", "w") as f:
        # Write the header
        header = ["id", "name"] + props
        f.write(delim.join(header) + "\n")
        for node in nodes:
            node_id = node[0]
            name = node[2]
            props_dict = json.loads(node[3]) if len(node) > 3 else {}
            # Create a row with the properties
            row = [node_id, name] + [str(props_dict.get(prop, "")) for prop in props]
            f.write(delim.join(row) + "\n")

# And now the edges file.
# The header is edge_id,subject,predicate, object, props
with open("tests/neo4j_csv/edges.csv", "r") as f:
    csv_reader = csv.reader(f, dialect="myalect")
    next(csv_reader)  # Skip the header
    lines = list(csv_reader)


edges_by_file= defaultdict(list)
# We need to create a CSV file for each (predicate, subject_category, object_category) combination
# we have the node_to_category dictionary to help us
for line in lines:
    edge_id = line[0]
    subject_id = line[1]
    predicate = line[2]
    object_id = line[3]
    props = json.loads(line[4]) if len(line) > 4 else {}

    subject_category = node_to_category[subject_id]
    object_category = node_to_category[object_id]

    # Create a filename based on the categories and predicate
    filename = f"tests/kuzudb_csv/edges/{predicate}_{subject_category}_{object_category}.csv"

    edges_by_file[filename].append(line)

# Now write each edge to the appropriate file
for filename, lines in edges_by_file.items():
    # Create a set of all properties for this edge file
    props = set()
    for line in lines:
        if len(line) > 4:
            props.update(json.loads(line[4]).keys())
    propnames = list(props)
    with open(filename, "w") as f:
        header = ["subject", "object"] + propnames
        f.write(delim.join(header) + "\n")
        for line in lines:
            edge_id = line[0]
            subject_id = line[1]
            predicate = line[2]
            object_id = line[3]
            props = json.loads(line[4]) if len(line) > 4 else {}
            # Create a row with the properties
            row = [subject_id, object_id] + [str(props.get(prop, "")) for prop in propnames]
            f.write(delim.join(row) + "\n")