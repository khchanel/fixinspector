from __future__ import annotations

from pathlib import Path

from fixinspector.core.dictionary import FixDictionary
from fixinspector.core.parser import decode_fix_message

from tests.conftest import make_fix


def test_loads_custom_quickfix_dictionary(tmp_path: Path) -> None:
    dictionary_path = tmp_path / "CUSTOM.xml"
    dictionary_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<fix type="FIX" major="4" minor="4">
  <fields>
    <field number="35" name="MsgType" type="STRING">
      <value enum="Z" description="CUSTOM_FLOW"/>
    </field>
    <field number="9006" name="AwesomeField" type="STRING">
      <value enum="Y" description="YES_VALUE"/>
    </field>
  </fields>
  <messages>
    <message name="CustomFlow" msgtype="Z" msgcat="app">
      <field name="AwesomeField" required="N"/>
    </message>
  </messages>
</fix>
""",
        encoding="utf-8",
    )

    dictionary = FixDictionary.from_xml(dictionary_path)
    message = decode_fix_message(make_fix([(35, "Z"), (49, "S"), (56, "T"), (9006, "Y")]), dictionary)

    assert message.summary.msg_name == "CustomFlow"
    assert dictionary.enum_label(35, "D") == "NewOrderSingle"
    awesome = next(field for field in message.fields if field.tag == 9006)
    assert awesome.name == "AwesomeField"
    assert awesome.enum_label == "YES_VALUE"


def test_marks_numingroup_fields_as_group_context() -> None:
    message = decode_fix_message(make_fix([(35, "D"), (453, "1"), (448, "PARTY"), (447, "D"), (452, "1")]))

    grouped = [field for field in message.fields if field.group_path]
    assert grouped[0].tag == 453
    assert grouped[0].group_path == ("NoPartyIDs",)
