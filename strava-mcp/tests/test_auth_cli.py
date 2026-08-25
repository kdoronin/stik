import pytest

from strava_mcp.auth_cli import parse_callback


def test_parse_callback_accepts_matching_state():
    code = parse_callback("/callback?code=abc&state=nonce", expected_state="nonce")
    assert code == "abc"


def test_parse_callback_rejects_wrong_state():
    with pytest.raises(ValueError, match="state"):
        parse_callback("/callback?code=abc&state=wrong", expected_state="nonce")


def test_parse_callback_reports_strava_denial():
    with pytest.raises(ValueError, match="access_denied"):
        parse_callback("/callback?error=access_denied&state=nonce", expected_state="nonce")
