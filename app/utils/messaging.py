import json
from spade.message import Message


def build_message(
    to: str,
    performative: str,
    conversation: str | None,
    content: dict,
) -> Message:
    msg = Message(to=to)
    msg.set_metadata("performative", performative)  # FIPA ACL
    if conversation:
        msg.set_metadata("conversation", conversation)
    msg.set_metadata("language", "json")
    msg.set_metadata("ontology", "hen_house")
    msg.body = json.dumps(content)
    return msg


def parse_content(msg: Message) -> dict:
    if not msg.body:
        return {}
    try:
        return json.loads(msg.body)
    except json.JSONDecodeError:
        return {"raw": msg.body}
