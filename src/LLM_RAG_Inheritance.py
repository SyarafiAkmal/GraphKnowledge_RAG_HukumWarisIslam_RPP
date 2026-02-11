from neo4j import GraphDatabase
from openai import OpenAI
import json
import os

def load_graph():
    URI = "bolt://localhost:7687"
    USERNAME = "neo4j"
    PASSWORD = "neo4jsyarafi"
    return GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))


def get_spouse(deceased_id, driver):
    query = """
    MATCH (x:Person {id: $id})-[:SPOUSE_OF]-(s:Person)
    RETURN x.name AS deceased_name,
           s.id AS id,
           s.name AS name
    """
    with driver.session() as session:
        result = session.run(query, id=deceased_id)
        records = [r.data() for r in result]

    if not records:
        return {"query_data": [], "share": None}

    deceased_name = records[0]["deceased_name"]

    if deceased_name == "Ahmad":
        share = "1/8"
    elif deceased_name == "Fatimah":
        share = "1/4"
    else:
        share = None

    return {
        "spouse": [
            {"id": r["id"], "name": r["name"]}
            for r in records
        ],
        "share": share
    }


def get_children(deceased_id, driver):
    query = """
    MATCH (x:Person {id: $id})-[:PARENT_OF]->(c:Person)
    RETURN c.id AS id, c.name AS name
    """
    with driver.session() as session:
        result = session.run(query, id=deceased_id)
        records = [r.data() for r in result]

    children_with_share = []

    for child in records:
        if child["name"] == "Aisyah":
            share = "1/2"
        elif child["name"] == "Ali":
            share = "T"
        else:
            share = None

        children_with_share.append({
            "id": child["id"],
            "name": child["name"],
            "share": share
        })

    return {"children": children_with_share}


def dispatch(action, db_driver):
    intent = action.get("intent")
    deceased_id = action.get("deceased_id")

    if intent == "GET_SPOUSE":
        return get_spouse(deceased_id, db_driver)
    elif intent == "GET_CHILDREN":
        return get_children(deceased_id, db_driver)
    else:
        return {"error": "Unknown or unsupported intent"}


def intent_classifier(input_text, client):
    prompt = f"""
        You are an intent classifier.

        Family Tree Schema:
        - Ahmad (father)
        - Fatimah (mother)
        - Children:
            - Ali (son)
            - Aisyah (daughter)

        Output ONLY valid JSON.
        No explanation.
        No extra text.

        If the input question is not related to the the deceased and the inheritor (spouse (could be Ahmad or Fatimah) or children (both Ali), respond with:
        {{"intent": "UNKNOWN", "deceased_id": null}}

        Examples:
        Q: Ahmad has passed away. Who is his spouse?
        A: {{"intent": "GET_SPOUSE", "deceased_id": "1"}}

        Q: Ahmad died, what is Fatimah's share of inheritance?
        A: {{"intent": "GET_SPOUSE", "deceased_id": "1"}}

        Q: Fatimah died, what is Ali's share of inheritance?
        A: {{"intent": "GET_CHILDREN", "deceased_id": "2"}}

        Schema:
        {{
        "intent": "GET_SPOUSE | GET_CHILDREN",
        "deceased_id": string
        }}

        User question:
        {input_text}
        """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    print(response.choices[0].message.content)
    return json.loads(response.choices[0].message.content)


def main_pipeline():

    db_driver = load_graph()

    client = OpenAI(api_key="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")

    user_input = input("Question: ")

    action = intent_classifier(user_input, client)

    if action["intent"] == "UNKNOWN":
        print("Question not related to family schema.")
        return

    queried_data = dispatch(action, db_driver)

    print(queried_data)

    final_prompt = f"""
        User question:
        {user_input}

        Data:
        {queried_data}

        You must answer strictly based on the data.
        Do not hallucinate.
        T is the representation of Ta'shib (residual inheritance).
        If answer not found, say:
        "I'm sorry, I cannot process that question."
        """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": final_prompt}
        ],
        temperature=0
    )

    print(response.choices[0].message.content)


if __name__ == "__main__":
    main_pipeline()
