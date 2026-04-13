from app.chat_history import ChatHistory
from app.time_utils import utc_now


def test_utc_now_is_timezone_aware() -> None:
    now = utc_now()
    assert now.tzinfo is not None
    assert now.utcoffset() is not None


def test_chat_history_uses_utc_iso_timestamps() -> None:
    history = ChatHistory()
    history.add_message("user", "hello")
    payload = history.to_dict()

    assert payload["timestamp"].endswith("+00:00")
    assert payload["messages"][0]["timestamp"].endswith("+00:00")
