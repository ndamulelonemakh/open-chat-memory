import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_EXAMPLE_ROOT = REPO_ROOT / "docs" / "examples"
PUBLIC_EXAMPLE_FILES = [
    PUBLIC_EXAMPLE_ROOT / "openai-export-sample" / "conversations.json",
    PUBLIC_EXAMPLE_ROOT / "openai-export-sample" / "users.json",
    PUBLIC_EXAMPLE_ROOT / "claude-export-sample" / "conversations.json",
    PUBLIC_EXAMPLE_ROOT / "claude-export-sample" / "users.json",
    PUBLIC_EXAMPLE_ROOT / "claude-export-sample" / "projects.json",
]

BLOCKED_PATTERNS = [
    "preferred name:",
    "user profile:",
    "user_instructions",
    "about_user_message",
    "about_model_message",
    "machine learning engineer",
    "aspiring techpreneur",
    "version control: github",
]


def _flatten(value: object) -> str:
    return json.dumps(value, ensure_ascii=True).lower()


def test_public_example_files_are_valid_json():
    for path in PUBLIC_EXAMPLE_FILES:
        with path.open(encoding="utf-8") as handle:
            json.load(handle)


def test_public_example_files_do_not_contain_sensitive_patterns():
    for path in PUBLIC_EXAMPLE_FILES:
        content = _flatten(json.loads(path.read_text(encoding="utf-8")))
        for pattern in BLOCKED_PATTERNS:
            assert pattern not in content, f"Blocked pattern {pattern!r} found in public example file: {path}"


def test_public_example_files_only_use_example_com_email_addresses():
    for path in PUBLIC_EXAMPLE_FILES:
        content = _flatten(json.loads(path.read_text(encoding="utf-8")))
        if "@" not in content:
            continue
        assert "@example.com" in content, f"Non-example email address found in public example file: {path}"


def test_public_example_files_do_not_publish_phone_numbers():
    for path in PUBLIC_EXAMPLE_FILES:
        content = _flatten(json.loads(path.read_text(encoding="utf-8")))
        assert "+27" not in content
        assert 'phone_number": "' not in content
        assert 'verified_phone_number": "' not in content
