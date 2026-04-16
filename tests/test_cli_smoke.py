from openchatmemory.cli import build_parser


def test_cli_builds():
    ap = build_parser()
    assert ap is not None
