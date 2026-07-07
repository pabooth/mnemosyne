import httpx
import pytest

from mnemo_curator import cli


class FailingService:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    async def scan(self, resolve: bool = False):
        raise self.exc


def service_factory(exc: Exception):
    class FakeCuratorService:
        def __init__(self, settings) -> None:
            self.settings = settings

        async def scan(self, resolve: bool = False):
            return await FailingService(exc).scan(resolve=resolve)

    return FakeCuratorService


async def test_scan_reports_configuration_failure(monkeypatch, capsys):
    monkeypatch.setattr(cli, "CuratorService", service_factory(RuntimeError("GITHUB_TOKEN and GITHUB_REPO are required")))

    with pytest.raises(SystemExit) as exc_info:
        await cli._scan(resolve=False)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "mnemo-curator scan failed: configuration error: GITHUB_TOKEN and GITHUB_REPO are required" in captured.err


async def test_scan_reports_network_failure(monkeypatch, capsys):
    request = httpx.Request("GET", "https://api.github.com/repos/example/repo")
    monkeypatch.setattr(cli, "CuratorService", service_factory(httpx.ConnectError("connection failed", request=request)))

    with pytest.raises(SystemExit) as exc_info:
        await cli._scan(resolve=True)

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "mnemo-curator scan failed: network error:" in captured.err
    assert "connection failed" in captured.err
