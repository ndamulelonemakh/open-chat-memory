# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-05-02

### Added
- Initial release of `openchatmemory` (formerly `chatmemory`)
- Support for parsing ChatGPT and Claude conversation exports
- PostgreSQL persistence layer for storing chat histories
- Mem0 memory integration for AI-powered knowledge graphs
- CLI tool (`ocmem`) with `parse`, `db`, and `mem` subcommands
- Extensible parser registry for adding new chat providers
- Pydantic-based message schema validation
- Structured logging with loguru

### Changed
- Renamed package from `chatmemory` to `openchatmemory`
- Renamed CLI from `chatmemory` to `ocmem`
- Refactored `db_loader` module to `persistence` for clarity
- Refactored `memory_loader` module to `memory` for simplicity
- Extracted `MessageModel` to new `schemas` subpackage for better separation of concerns
- Enhanced PyPI metadata with comprehensive classifiers and project URLs

### Technical
- Python 3.11+ required
- Dependencies: pandas, pydantic 2.11+, SQLAlchemy 2.0+, loguru
- Optional extras: `db` (PostgreSQL), `mem0` (memory integration)
- Testing with pytest

[0.1.0]: https://github.com/ndamulelonemakhavhani/open-chat-memory/releases/tag/v0.1.0
