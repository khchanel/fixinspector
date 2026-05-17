from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

from fixinspector.core.models import FieldDefinition, GroupDefinition, MessageDefinition


COMMON_FIELDS: dict[int, tuple[str, str, dict[str, str]]] = {
    1: ("Account", "STRING", {}),
    6: ("AvgPx", "PRICE", {}),
    8: ("BeginString", "STRING", {}),
    9: ("BodyLength", "LENGTH", {}),
    10: ("CheckSum", "STRING", {}),
    11: ("ClOrdID", "STRING", {}),
    14: ("CumQty", "QTY", {}),
    15: ("Currency", "CURRENCY", {}),
    17: ("ExecID", "STRING", {}),
    20: ("ExecTransType", "CHAR", {}),
    21: ("HandlInst", "CHAR", {}),
    22: ("SecurityIDSource", "STRING", {}),
    31: ("LastPx", "PRICE", {}),
    32: ("LastQty", "QTY", {}),
    34: ("MsgSeqNum", "SEQNUM", {}),
    35: (
        "MsgType",
        "STRING",
        {
            "0": "Heartbeat",
            "1": "TestRequest",
            "2": "ResendRequest",
            "3": "Reject",
            "4": "SequenceReset",
            "5": "Logout",
            "6": "IOI",
            "7": "Advertisement",
            "8": "ExecutionReport",
            "9": "OrderCancelReject",
            "A": "Logon",
            "D": "NewOrderSingle",
            "E": "NewOrderList",
            "F": "OrderCancelRequest",
            "G": "OrderCancelReplaceRequest",
            "H": "OrderStatusRequest",
            "j": "BusinessMessageReject",
        },
    ),
    37: ("OrderID", "STRING", {}),
    38: ("OrderQty", "QTY", {}),
    39: (
        "OrdStatus",
        "CHAR",
        {
            "0": "New",
            "1": "PartiallyFilled",
            "2": "Filled",
            "3": "DoneForDay",
            "4": "Canceled",
            "5": "Replaced",
            "6": "PendingCancel",
            "7": "Stopped",
            "8": "Rejected",
            "9": "Suspended",
            "A": "PendingNew",
            "B": "Calculated",
            "C": "Expired",
            "E": "PendingReplace",
        },
    ),
    40: (
        "OrdType",
        "CHAR",
        {"1": "Market", "2": "Limit", "3": "Stop", "4": "StopLimit"},
    ),
    41: ("OrigClOrdID", "STRING", {}),
    44: ("Price", "PRICE", {}),
    48: ("SecurityID", "STRING", {}),
    49: ("SenderCompID", "STRING", {}),
    52: ("SendingTime", "UTCTIMESTAMP", {}),
    54: ("Side", "CHAR", {"1": "Buy", "2": "Sell", "5": "SellShort"}),
    55: ("Symbol", "STRING", {}),
    56: ("TargetCompID", "STRING", {}),
    58: ("Text", "STRING", {}),
    59: ("TimeInForce", "CHAR", {"0": "Day", "1": "GoodTillCancel", "3": "ImmediateOrCancel", "4": "FillOrKill"}),
    60: ("TransactTime", "UTCTIMESTAMP", {}),
    100: ("ExDestination", "EXCHANGE", {}),
    150: (
        "ExecType",
        "CHAR",
        {
            "0": "New",
            "1": "PartialFill",
            "2": "Fill",
            "4": "Canceled",
            "5": "Replace",
            "8": "Rejected",
            "C": "Expired",
            "E": "PendingReplace",
            "F": "Trade",
        },
    ),
    151: ("LeavesQty", "QTY", {}),
    167: ("SecurityType", "STRING", {}),
    207: ("SecurityExchange", "EXCHANGE", {}),
    453: ("NoPartyIDs", "NUMINGROUP", {}),
    448: ("PartyID", "STRING", {}),
    447: ("PartyIDSource", "CHAR", {}),
    452: ("PartyRole", "INT", {}),
}

COMMON_MESSAGES: dict[str, str] = {
    "0": "Heartbeat",
    "1": "TestRequest",
    "2": "ResendRequest",
    "3": "Reject",
    "4": "SequenceReset",
    "5": "Logout",
    "8": "ExecutionReport",
    "9": "OrderCancelReject",
    "A": "Logon",
    "D": "NewOrderSingle",
    "F": "OrderCancelRequest",
    "G": "OrderCancelReplaceRequest",
    "H": "OrderStatusRequest",
    "j": "BusinessMessageReject",
}


class FixDictionary:
    def __init__(
        self,
        fields: dict[int, FieldDefinition] | None = None,
        messages: dict[str, MessageDefinition] | None = None,
        name: str = "Built-in common FIX",
    ) -> None:
        self.fields = fields or {}
        self.messages = messages or {}
        self.name = name

    @classmethod
    def common(cls) -> "FixDictionary":
        fields = {
            number: FieldDefinition(number, name, field_type, enums)
            for number, (name, field_type, enums) in COMMON_FIELDS.items()
        }
        messages = {
            msgtype: MessageDefinition(msgtype, name)
            for msgtype, name in COMMON_MESSAGES.items()
        }
        return cls(fields=fields, messages=messages)

    @classmethod
    def from_xml(cls, path: str | Path) -> "FixDictionary":
        source = Path(path)
        tree = ElementTree.parse(source)
        root = tree.getroot()
        fields_by_name: dict[str, FieldDefinition] = {}
        fields_by_number: dict[int, FieldDefinition] = {}

        fields_node = root.find("fields")
        if fields_node is not None:
            for node in fields_node.findall("field"):
                number_text = node.get("number")
                name = node.get("name")
                if not number_text or not name:
                    continue
                number = int(number_text)
                enums = {
                    value.get("enum", ""): value.get("description", "")
                    for value in node.findall("value")
                    if value.get("enum")
                }
                definition = FieldDefinition(
                    number=number,
                    name=name,
                    type=node.get("type", "STRING"),
                    enums=enums,
                )
                fields_by_name[name] = definition
                fields_by_number[number] = definition

        messages: dict[str, MessageDefinition] = {}
        messages_node = root.find("messages")
        if messages_node is not None:
            for node in messages_node.findall("message"):
                msgtype = node.get("msgtype")
                name = node.get("name")
                if not msgtype or not name:
                    continue
                fields, groups = _parse_message_members(node, fields_by_name)
                messages[msgtype] = MessageDefinition(
                    msgtype=msgtype,
                    name=name,
                    category=node.get("msgcat", ""),
                    fields=tuple(fields),
                    groups=groups,
                )

        merged = cls.common()
        for number, definition in fields_by_number.items():
            existing = merged.fields.get(number)
            if existing:
                merged.fields[number] = FieldDefinition(
                    number=number,
                    name=definition.name,
                    type=definition.type,
                    enums={**existing.enums, **definition.enums},
                )
            else:
                merged.fields[number] = definition
        merged.messages.update(messages)
        merged.name = str(source)
        return merged

    def field(self, tag: int) -> FieldDefinition:
        return self.fields.get(tag, FieldDefinition(tag, f"Unknown({tag})"))

    def message_name(self, msgtype: str | None) -> str | None:
        if msgtype is None:
            return None
        definition = self.messages.get(msgtype)
        if definition:
            return definition.name
        msgtype_field = self.fields.get(35)
        if msgtype_field:
            return msgtype_field.enums.get(msgtype)
        return None

    def enum_label(self, tag: int, value: str) -> str | None:
        definition = self.fields.get(tag)
        if not definition:
            return None
        return definition.enums.get(value)


def _parse_message_members(
    node: ElementTree.Element, fields_by_name: dict[str, FieldDefinition]
) -> tuple[list[int], dict[int, GroupDefinition]]:
    fields: list[int] = []
    groups: dict[int, GroupDefinition] = {}
    for child in list(node):
        if child.tag == "field":
            number = _field_number(child.get("name"), fields_by_name)
            if number is not None:
                fields.append(number)
        elif child.tag == "group":
            group = _parse_group(child, fields_by_name)
            if group is not None:
                fields.append(group.number)
                groups[group.number] = group
    return fields, groups


def _parse_group(
    node: ElementTree.Element, fields_by_name: dict[str, FieldDefinition]
) -> GroupDefinition | None:
    number = _field_number(node.get("name"), fields_by_name)
    if number is None:
        return None
    fields: list[int] = []
    groups: dict[int, GroupDefinition] = {}
    for child in list(node):
        if child.tag == "field":
            child_number = _field_number(child.get("name"), fields_by_name)
            if child_number is not None:
                fields.append(child_number)
        elif child.tag == "group":
            child_group = _parse_group(child, fields_by_name)
            if child_group is not None:
                fields.append(child_group.number)
                groups[child_group.number] = child_group
    return GroupDefinition(
        name=node.get("name", f"Group{number}"),
        number=number,
        fields=tuple(fields),
        groups=groups,
    )


def _field_number(name: str | None, fields_by_name: dict[str, FieldDefinition]) -> int | None:
    if not name:
        return None
    definition = fields_by_name.get(name)
    return definition.number if definition else None
