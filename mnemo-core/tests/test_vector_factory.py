import pytest

from mnemo_core.config import Settings
from mnemo_core.vector.factory import get_vector_index
from mnemo_core.vector.sqlite_vec import SqliteVecIndex


def test_vector_factory_returns_sqlite_vec_by_default(tmp_path):
    settings = Settings(state_db_path=str(tmp_path / "mnemosyne.db"))
    index = get_vector_index(settings)
    assert isinstance(index, SqliteVecIndex)
    assert index.path == str(tmp_path / "mnemosyne.db")


def test_vector_factory_prefers_dedicated_vector_db_path(tmp_path):
    settings = Settings(
        state_db_path=str(tmp_path / "mnemosyne.db"),
        vector_db_path=str(tmp_path / "vectors.db"),
    )
    index = get_vector_index(settings)
    assert index.path == str(tmp_path / "vectors.db")


def test_vector_factory_rejects_unknown_store(tmp_path):
    settings = Settings(vector_store="unknown", state_db_path=str(tmp_path / "mnemosyne.db"))
    with pytest.raises(ValueError, match="Unknown VECTOR_STORE"):
        get_vector_index(settings)
