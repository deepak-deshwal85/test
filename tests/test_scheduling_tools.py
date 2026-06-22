import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from client_config import load_client_config
from scheduling_tools import build_scheduling_tools


def test_build_scheduling_tools_registers_calcom_tools():
    config = load_client_config("911171366880")
    tools = build_scheduling_tools(config, default_timezone="Asia/Kolkata")
    tool_names = sorted(tool.id for tool in tools)
    assert tool_names == ["get_available_meeting_slots", "schedule_meeting"]
