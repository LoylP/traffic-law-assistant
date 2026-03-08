import json
from neo4j import GraphDatabase

URI="bolt://localhost:7687"
USER="neo4j"
PASSWORD="password"

driver = GraphDatabase.driver(URI, auth=(USER,PASSWORD))

def load_corpus():
    with open("data/structured/law_corpus.jsonl","r",encoding="utf8") as f:
        for line in f:
            yield json.loads(line)

def create_nodes(tx, row):

    tx.run("""
    MERGE (d:Decree {id:$decree_id})
    SET d.number=$decree_no,
        d.issue_date=$issue_date
    """,row)

    tx.run("""
    MERGE (u:LegalUnit {citation_id:$citation_id})
    SET u.article=$article,
        u.clause=$clause,
        u.point=$point,
        u.text=$text
    """,row)

    tx.run("""
    MATCH (d:Decree {id:$decree_id})
    MATCH (u:LegalUnit {citation_id:$citation_id})
    MERGE (u)-[:PART_OF]->(d)
    """,row)

def create_nodes(tx, row):

    tx.run("""
    MERGE (d:Decree {id:$decree_id})
    SET d.number=$decree_no,
        d.issue_date=$issue_date
    """,row)

    tx.run("""
    MERGE (u:LegalUnit {citation_id:$citation_id})
    SET u.article=$article,
        u.clause=$clause,
        u.point=$point,
        u.text=$text
    """,row)

    tx.run("""
    MATCH (d:Decree {id:$decree_id})
    MATCH (u:LegalUnit {citation_id:$citation_id})
    MERGE (u)-[:PART_OF]->(d)
    """,row)

def create_structure(tx,row):

    if row["clause"]:

        tx.run("""
        MERGE (a:Article {id:$decree_id+"-D"+toString($article)})
        MERGE (c:Clause {id:$citation_id})

        MERGE (a)-[:HAS_CLAUSE]->(c)
        """,row)

    if row["point"]:

        tx.run("""
        MERGE (c:Clause {id:$decree_id+"-D"+toString($article)+"-K"+$clause})
        MERGE (p:Point {id:$citation_id})

        MERGE (c)-[:HAS_POINT]->(p)
        """,row)

def load_amendments(tx):

    amap=json.load(open("data/structured/amendment_map.json",encoding="utf8"))

    for cid, recs in amap.items():

        for r in recs:

            tx.run("""
            MATCH (d:Decree {id:$amender})
            MATCH (u:LegalUnit {citation_id:$target})

            MERGE (d)-[:AMENDS {action:$action}]->(u)
            """,
            amender=r["amending_decree_id"],
            target=cid,
            action=r["action"]
            )

with driver.session() as session:

    for row in load_corpus():
        session.execute_write(create_nodes,row)
        session.execute_write(create_structure,row)

    session.execute_write(load_amendments)