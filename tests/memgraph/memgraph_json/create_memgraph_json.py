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

with open("tests/memgraph_json/nodes.json", "w") as outfile:
    json.dump(entities, outfile)

entities = []
with open("tests/neo4j_csv/edges.csv", "r") as infile:
    csv.register_dialect('mydialect', escapechar="\\")
    reader = csv.DictReader(infile,dialect='mydialect')
    for line in reader:
        node = {"id": line["id"], "subject": line["subject"], "predicate": line["predicate"], "object": line["object"] }
        if line["props"] != "":
            #p = line["props"].replace('\\"', "'").replace("true", "True").replace("false", "False")
            p = line["props"].replace("true", "True").replace("false", "False")
            props = eval(p)
            for key, value in props.items():
                node[key] = value
        entities.append( node )

with open("tests/memgraph_json/edges.json", "w") as outfile:
    json.dump(entities, outfile, indent=4)

