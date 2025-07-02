with open("tests/neo4j_csv/nodes.csv", "r") as infile, open("tests/memgraph_csv/nodes.csv", "w") as outfile:
    for line in infile:
        line = line.replace('\\"', "'")
        outfile.write(line)

with open("tests/neo4j_csv/edges.csv", "r") as infile, open("tests/memgraph_csv/edges.csv", "w") as outfile:
    for line in infile:
        outfile.write(line)
