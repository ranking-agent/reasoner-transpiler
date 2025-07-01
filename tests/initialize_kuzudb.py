from collections import defaultdict
import os

"""Load the kuzudb"""

# KuzuDB is different from Neo4j -- it's an in memory database.  So we load it in the fixture.  The fixture
# calls this code to load it at test time.

# Now, the tests need to run in two configurations
# 1. In github actions
# 2. In local development

# In the neo4j case, the github version pulls the files from github.  But I don't
# see the point, since the repo is checked out.  So its easier to look at the files that are
# already there.  This lets us not have to hard code file names.

# The main thing we need to tell kuzudb are the types of the properties.  So we'll have a little dict here
column_types = { "id": "STRING",
                 "name": "STRING",
                 "length": "INT64",
                 "chromosome": "STRING",
                 "primary_knowledge_source": "STRING",
                 "object_aspect_qualifier": "STRING",
                 "object_direction_qualifier": "STRING",
                 "qualified_predicate": "STRING",
                 "bogus_knowledge_source": "STRING",
                 "p_value": "FLOAT",
                 "non_biolink_attribute": "STRING",
                 "aggregator_knowledge_source": "STRING[]",
                 "fda_approved": "BOOLEAN",
                 "publications": "STRING[]",
                 "attributes": "STRING[]",
}

def get_header(file_name, delim="\t"):
    """Get the header of a file."""
    with open(file_name, "r") as f:
        header = f.readline().strip().split(delim)
    return header

def get_node_table_string(category, header):
    create_string = f"CREATE NODE TABLE `{category}` ("
    for col in header:
        create_string += f"{col} {column_types[col]}, "
    create_string += "PRIMARY KEY(id))"
    return create_string

def get_edge_table_string(predicate, sub_ob_file, header):
    """Get the edge table string for a predicate."""
    create_string = f"CREATE REL TABLE `{predicate}` ("
    from_tos = [ f"FROM `{sub}` TO `{ob}`" for sub, ob, file in sub_ob_file]
    create_string += ", ".join(from_tos)
    for col in header[2:]:
        create_string += f", {col} {column_types[col]} "
    create_string += ");"
    return create_string

def load_kuzu(conn):
    d = "\t"
    node_files = [ f"tests/kuzudb_csv/nodes/{f}" for f in os.listdir("tests/kuzudb_csv/nodes")]
    edge_files = [ f"tests/kuzudb_csv/edges/{f}" for f in os.listdir("tests/kuzudb_csv/edges")]
    for node_file in node_files:
        category = node_file.split(".")[0].split("/")[-1]
        header = get_header(node_file, d)
        conn.execute(get_node_table_string(category, header))
        conn.execute(f'COPY `{category}` from "{node_file}" (HEADER=true, DELIM="\t")')
    # now the edges. There might be multiple files for the same predicate. (there is for subclass_of)
    # One thing that we're not super careful about is that if there are these multiple files, they
    # should have the same header.  But we don't check that. Oh well
    edge_map = defaultdict(list)
    for edge_file in edge_files:
        parts = edge_file[:-4].split("/")[-1].split("_biolink:")
        predicate = parts[0]
        subject_category = f"biolink:{parts[1]}"
        object_category  = f"biolink:{parts[2]}"
        edge_map[predicate].append((subject_category, object_category, edge_file))
    for predicate in edge_map:
        # Create the edge table
        header = get_header(edge_map[predicate][0][2])
        cstring = get_edge_table_string(predicate, edge_map[predicate], header)
        result = conn.execute(cstring)
        for sub, ob, edge_file in edge_map[predicate]:
            x =f"COPY `{predicate}` FROM '{edge_file}' (FROM='{sub}', TO='{ob}', HEADER=true,  DELIM='\t')"
            conn.execute(x)

if __name__ == "__main__":
    import kuzu
    db = kuzu.Database()
    conn = kuzu.Connection(db)
    load_kuzu(conn)
