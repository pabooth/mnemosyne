import pytest

from mnemo_core import __version__
from mnemo_core import evaluation


def test_evaluation_cli_reports_package_version(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["mnemo-evaluate", "--version"])

    with pytest.raises(SystemExit) as exc_info:
        evaluation.main()

    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"mnemo-evaluate {__version__}"
