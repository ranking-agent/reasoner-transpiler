import csv
import json

entities = []
with open("tests/neo4j_csv/nodes.csv", "r") as infile:
    csv.register_dialect('mydialect', escapechar="\\")
    reader = csv.DictReader(infile,dialect='mydialect')
    for line in reader:
        node = {"id": line["id"], "category": line["category"], "name": line["name"] }
        if line["props"] != "":
            p = line["props"].replace('\\"', "'")
            props = eval(p)
            for key, value in props.items():
                node[key] = value
        entities.append( node )

with open("tests/memgraph_csv/nodes.json", "w") as outfile:
    json.dump(entities, outfile)

entities = []
with open("tests/neo4j_csv/edges.csv", "r") as infile:
    csv.register_dialect('mydialect', escapechar="\\")
    reader = csv.DictReader(infile,dialect='mydialect')
    for line in reader:
        node = {"subject": line["subject"], "predicate": line["predicate"], "object": line["object"] }
        if line["props"] != "":
            p = line["props"].replace('\\"', "'").replace("true", "True").replace("false", "False")
            props = eval(p)
            for key, value in props.items():
                node[key] = value
        entities.append( node )

with open("tests/memgraph_csv/edges.json", "w") as outfile:
    json.dump(entities, outfile)


exit

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
