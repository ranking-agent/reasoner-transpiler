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

# we're going to have a lot of edges with null props this way, which isn't what most graphs will look like but it shouldn't affect the tests
with open("tests/neo4j_csv/edges.csv", "r") as infile, open("tests/memgraph_csv/edges.csv", "w") as outfile:
    header = infile.readline().split(',')[:-1]
    newprops = ["primary_knowledge_source", "fda_approved", "aggregator_knowledge_source",
               "publications", "p_value", "non_biolink_attribute", "attributes",
               "qualified_predicate", "object_aspect_qualiier", "object_direction_qualifier",
               "bogus_knowledge_source"]
    newprops = []
    header += newprops
    header = '\t'.join(header) + '\n'  # remove the last comma and add newline
    outfile.write(header)
    for line in infile:
        parts = line.strip().split(',')
        props = ','.join(parts[4:])[1:-1] \
            .replace('\\\\\\"', "'") \
            .replace('\\', "") \
            .replace("false","False") \
            .replace("true", "True")
        if len(props) == 0:
            props_dict = {}
        else:
            props_dict = eval(props)
        outparts = parts[:4]
        outparts[2] = outparts[2].replace("biolink:", "")
        for prop in newprops:
            if prop in props_dict:
                outparts.append(str(props_dict[prop]))
            else:
                outparts.append('')
        outfile.write("\t".join(outparts) + '\n')
