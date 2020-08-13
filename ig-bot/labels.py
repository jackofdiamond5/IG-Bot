import json
import requests

from util import build_payload
from static import graphql_endpoint


async def add_labels_to_labelable(label_ids, labelable_id, headers):
    "adds an arbitrary amount of labels to an issue"
    schema = open("Schemas/add_labels_to_labelable.graphql", "r").read()
    variables = json.dumps({
        "label_ids": label_ids,
        "labelable_id": labelable_id
    })
    payload = build_payload(schema, variables)
    response = requests.post(graphql_endpoint, payload, headers=headers)
    return json.loads(response.content.decode())


async def get_label_by_name(label_name, login, headers):
    "returns a list of all matched labels for a set of repositories"
    schema = open("Schemas/get_label_by_name.graphql", "r").read()
    variables = json.dumps({"login": login, "label_name": label_name})
    payload = build_payload(schema, variables)
    response = requests.post(graphql_endpoint, payload, headers=headers)
    return json.loads(response.content.decode())
