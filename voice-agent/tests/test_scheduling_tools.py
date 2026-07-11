import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from client_config import CalComConfig, ClientConfig
from scheduling_tools import build_scheduling_tools


def test_build_scheduling_tools_registers_calcom_tools():
    config = ClientConfig(
        phone_number="911171366880",
        client_name="Acme Support",
        client_email_id="acme@example.com",
        greeting_message="Hello.",
        calcom=CalComConfig(
            username="acme-user",
            event_type_slug="30min",
            event_type_id=123,
        ),
    )
    tools = build_scheduling_tools(config, default_timezone="Asia/Kolkata")
    tool_names = sorted(tool.id for tool in tools)
    assert tool_names == ["get_available_meeting_slots", "schedule_meeting"]
