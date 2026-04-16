import json
from pathlib import Path

from dentist_agent import _resolve_export_path, _save_transcript


def test_resolve_export_path_prefers_explicit_file(tmp_path: Path) -> None:
    explicit = tmp_path / "manual.json"
    resolved = _resolve_export_path(str(explicit), str(tmp_path))
    assert resolved == str(explicit)


def test_resolve_export_path_uses_directory(tmp_path: Path) -> None:
    resolved = _resolve_export_path(None, str(tmp_path))
    assert resolved is not None
    assert str(tmp_path) in resolved
    assert Path(resolved).name.startswith("cli_transcript_")
    assert Path(resolved).suffix == ".json"


def test_save_transcript_creates_parent_dirs(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "session" / "chat.json"
    _save_transcript(
        str(target),
        messages=[
            {"role": "user", "text": "hello"},
            {"role": "assistant", "text": "hi"},
        ],
    )

    assert target.exists()
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["message_count"] == 2
    assert len(payload["messages"]) == 2
