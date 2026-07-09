import os
import sys
from pathlib import Path

import pytest

LAMBDA_DIR = (
    Path(__file__).resolve().parents[1]
    / "terraform"
    / "lambda"
    / "cognito_assign_guest_role"
)
sys.path.insert(0, str(LAMBDA_DIR))

os.environ.setdefault("GUEST_GROUP", "guest-clients")
os.environ.setdefault("ELEVATED_GROUPS", "approved-clients,relaydesk-admins")

import index as lambda_module  # noqa: E402


class FakeCognito:
    def __init__(self) -> None:
        self.groups_by_user: dict[str, set[str]] = {}
        self.add_calls: list[tuple[str, str, str]] = []

    def admin_list_groups_for_user(self, *, UserPoolId, Username):
        return {
            "Groups": [
                {"GroupName": name}
                for name in sorted(self.groups_by_user.get(Username, set()))
            ]
        }

    def admin_add_user_to_group(self, *, UserPoolId, Username, GroupName):
        self.add_calls.append((UserPoolId, Username, GroupName))
        self.groups_by_user.setdefault(Username, set()).add(GroupName)


@pytest.fixture
def fake_cognito(monkeypatch: pytest.MonkeyPatch) -> FakeCognito:
    client = FakeCognito()
    monkeypatch.setattr(lambda_module, "_cognito_client", lambda: client)
    return client


def _event(username: str = "user-1", trigger: str = "PostConfirmation_ConfirmSignUp"):
    return {
        "triggerSource": trigger,
        "userPoolId": "ap-south-1_TestPool",
        "userName": username,
    }


def test_new_user_is_added_to_guest_group(fake_cognito: FakeCognito) -> None:
    result = lambda_module.handler(_event(), None)
    assert result["userName"] == "user-1"
    assert fake_cognito.add_calls == [
        ("ap-south-1_TestPool", "user-1", "guest-clients")
    ]


def test_existing_guest_is_not_duplicated(fake_cognito: FakeCognito) -> None:
    fake_cognito.groups_by_user["user-1"] = {"guest-clients"}
    lambda_module.handler(_event(), None)
    assert fake_cognito.add_calls == []


def test_elevated_user_is_left_unchanged(fake_cognito: FakeCognito) -> None:
    fake_cognito.groups_by_user["user-1"] = {"approved-clients"}
    lambda_module.handler(_event(), None)
    assert fake_cognito.add_calls == []


def test_password_reset_trigger_is_ignored(fake_cognito: FakeCognito) -> None:
    lambda_module.handler(_event(trigger="PostConfirmation_ConfirmForgotPassword"), None)
    assert fake_cognito.add_calls == []
