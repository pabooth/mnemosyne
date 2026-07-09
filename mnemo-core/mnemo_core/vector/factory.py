from ..config import Settings, get_settings
from .base import VectorIndex
from .sqlite_vec import SqliteVecIndex


def get_vector_index(cfg: Settings | None = None) -> VectorIndex:
    settings = get_settings() if cfg is None else cfg
    match settings.vector_store:
        case "sqlite-vec":
            return SqliteVecIndex(
                path=settings.vector_db_path or settings.state_db_path,
                dimension=settings.vector_embedding_dim,
            )
        case _:
            raise ValueError(
                f"Unknown VECTOR_STORE: {settings.vector_store!r}. "
                "Valid options: sqlite-vec"
            )
