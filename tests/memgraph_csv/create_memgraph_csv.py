#The CSV loader for memgraph needs some help, this isn't idea, but ok for tests
with open("tests/neo4j_csv/nodes.csv", "r") as infile, open("tests/memgraph_csv/nodes.csv", "w") as outfile, open("tests/memgraph_csv/gene_nodes.csv","w") as outgenes:
    header = infile.readline()
    outfile.write(header)
    geneheader = header.replace("props", "length,chromosome")
    outgenes.write(geneheader)
    for line in infile:
        if 'biolink:Gene' in line:
            # This is a gene node, we need to extract length and chromosome
            parts = line.strip().split(',')
            props = ','.join(parts[3:])[1:-1].replace("\\","")
            if len(props) == 0:
                props_dict= {}
            else:
                props_dict = eval(props)
            length = props_dict.get('length', 'null')
            chromosome = props_dict.get('chromosome', 'null')
            outline = ','.join(parts[:3]) + f',{length},{chromosome}\n'
            outgenes.write(outline)
        else:
            outfile.write(line)

with open("tests/neo4j_csv/edges.csv", "r") as infile, open("tests/memgraph_csv/edges.csv", "w") as outfile:
    for line in infile:
        outfile.write(line)
