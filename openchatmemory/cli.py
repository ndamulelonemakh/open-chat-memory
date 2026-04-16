from __future__ import annotations

import argparse
import importlib
import json
import platform
import zipfile
from pathlib import Path

from loguru import logger

from . import SCHEMA_VERSION, __version__
from .memory.mem0 import push_memories as mem0_push_memories
from .parsers.base import ParserRegistry
from .persistence.postgres import load_jsonl_to_postgres


def _resolve_conversations_json(input_path: Path) -> Path:
    if input_path.is_file() and input_path.name == "conversations.json":
        logger.info(f"Using conversations.json directly: {input_path}")
        return input_path

    if input_path.is_dir():
        conversations_file = input_path / "conversations.json"
        if conversations_file.exists():
            logger.info(f"Found conversations.json in directory: {conversations_file}")
            return conversations_file
        msg = f"conversations.json not found in directory: {input_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    if input_path.is_file() and input_path.suffix == ".zip":
        logger.info(f"Extracting zip file: {input_path}")
        extract_dir = input_path.parent / f"{input_path.stem}_extracted"
        extract_dir.mkdir(exist_ok=True)

        with zipfile.ZipFile(input_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        conversations_files = list(extract_dir.rglob("conversations.json"))
        if conversations_files:
            logger.info(f"Found conversations.json in zip: {conversations_files[0]}")
            return conversations_files[0]

        msg = f"conversations.json not found in zip file: {input_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    if not input_path.exists():
        msg = f"Input path does not exist: {input_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    msg = f"Unsupported input format. Expected: conversations.json file, directory, or .zip file. Got: {input_path}"
    logger.error(msg)
    raise ValueError(msg)


def _cmd_parse(ns: argparse.Namespace) -> int:
    parser_cls = ParserRegistry.get(ns.provider)
    if not parser_cls:
        logger.error(f"Unknown provider '{ns.provider}'. Available: {ParserRegistry.available()}")
        return 2
    parser = parser_cls()

    try:
        conversations_path = _resolve_conversations_json(Path(ns.input))
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Failed to resolve input: {e}")
        return 1

    messages = parser.parse(conversations_path)
    out = Path(ns.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fp:
        for msg in messages:
            fp.write(json.dumps(msg.model_dump()) + "\n")
    logger.success(f"Wrote {len(messages)} messages -> {out}")
    return 0


def _configure_logging(log_format: str) -> None:
    if log_format == "json":
        # Reconfigure loguru to emit JSON lines
        from loguru import logger as _logger

        _logger.remove()
        _logger.add(lambda msg: print(msg, end=""), serialize=True)


def _cmd_db_load(ns: argparse.Namespace) -> int:
    return load_jsonl_to_postgres(
        Path(ns.input),
        ns.db_url,
        chatbot_type=ns.provider,
        batch_size=ns.batch_size,
    )


def _cmd_mem_push(ns: argparse.Namespace) -> int:
    return mem0_push_memories(Path(ns.input), user_id=ns.user_id, provider=ns.provider)


def _cmd_diagnose(_ns: argparse.Namespace) -> int:
    """Print environment and optional dependency availability information."""
    info: dict[str, object] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "package_version": __version__,
        "schema_version": SCHEMA_VERSION,
        "optional": {},
    }
    optional_modules = ["mem0", "psycopg", "sqlalchemy", "pandas"]
    for mod in optional_modules:
        try:
            importlib.import_module(mod)
            status = True
        except Exception:  # pragma: no cover - environment dependent
            status = False
        info["optional"][mod] = status  # type: ignore[index]
    print(json.dumps(info, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Chat export parser and loader")
    ap.add_argument("--log-format", choices=["text", "json"], default="text", help="Logging format (default: text)")
    sp = ap.add_subparsers(dest="cmd", required=True)

    ap_parse = sp.add_parser("parse", help="Parse provider export into JSONL messages")
    ap_parse.add_argument("--provider", required=True, help="chatgpt|claude|...")
    ap_parse.add_argument(
        "--input",
        required=True,
        help="Path to conversations.json, directory containing it, or .zip export",
    )
    ap_parse.add_argument("--out", required=True, help="Output JSONL path")
    ap_parse.set_defaults(func=_cmd_parse)

    ap_db = sp.add_parser("db", help="Database operations")
    sdb = ap_db.add_subparsers(dest="db_cmd", required=True)
    ap_db_load = sdb.add_parser("load", help="Load JSONL messages into Postgres")
    ap_db_load.add_argument("--input", required=True)
    ap_db_load.add_argument("--db-url", required=True)
    ap_db_load.add_argument("--provider", default="chatgpt")
    ap_db_load.add_argument("--batch-size", type=int, default=1000, help="Insert batch size (default: 1000)")
    ap_db_load.set_defaults(func=_cmd_db_load)

    ap_mem = sp.add_parser("mem", help="Memory operations")
    smem = ap_mem.add_subparsers(dest="mem_cmd", required=True)
    ap_mem_push = smem.add_parser("push", help="Push grouped memories to Mem0")
    ap_mem_push.add_argument("--input", required=True)
    ap_mem_push.add_argument("--user-id", required=True)
    ap_mem_push.add_argument("--provider", default="chatgpt")
    ap_mem_push.set_defaults(func=_cmd_mem_push)

    ap_diag = sp.add_parser("diagnose", help="Show environment & dependency diagnostics")
    ap_diag.set_defaults(func=_cmd_diagnose)

    return ap


def main(argv: list[str] | None = None) -> None:
    ap = build_parser()
    ns = ap.parse_args(argv)
    _configure_logging(getattr(ns, "log_format", "text"))
    code = ns.func(ns)
    raise SystemExit(code)
