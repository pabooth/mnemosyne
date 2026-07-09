from mnemo_core.api.deps import get_dedup_checker
from mnemo_core.config import Settings
from mnemo_core.pipeline.dedup import DuplicateChecker


def test_get_dedup_checker_disabled_by_default(tmp_path):
    settings = Settings(state_db_path=str(tmp_path / "mnemosyne.db"))
    assert get_dedup_checker(settings) is None


def test_get_dedup_checker_builds_checker_when_enabled(tmp_path):
    settings = Settings(
        dedup_enabled=True,
        state_db_path=str(tmp_path / "mnemosyne.db"),
        openai_api_key="test",
    )
    assert isinstance(get_dedup_checker(settings), DuplicateChecker)
