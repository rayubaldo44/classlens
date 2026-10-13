import os
from contextlib import contextmanager
from functools import lru_cache
from threading import Lock
from typing import Any, Iterator


class DatabaseError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = True, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details or {}


class Database:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._pool = None
        self._pool_lock = Lock()

    def _get_pool(self):
        if not self.database_url:
            raise DatabaseError(
                "database_not_configured",
                "Persistent storage is not configured. Set SUPABASE_DB_URL on the FastAPI server.",
                retryable=False,
            )
        if self._pool is None:
            with self._pool_lock:
                if self._pool is None:
                    try:
                        from psycopg_pool import ConnectionPool

                        # Supabase's transaction pooler can assign a different server session to
                        # each transaction. Psycopg's automatic prepared statements are session
                        # scoped and can therefore collide with statements prepared by another
                        # pooled client. Keep statements unnamed for reliable pooler operation.
                        self._pool = ConnectionPool(
                            self.database_url,
                            min_size=0,
                            max_size=5,
                            open=True,
                            kwargs={"prepare_threshold": None},
                        )
                    except Exception as error:
                        raise DatabaseError(
                            "database_unavailable",
                            "Persistent storage is unavailable.",
                            details={"database_error": type(error).__name__},
                        ) from error
        return self._pool

    @contextmanager
    def connection(self) -> Iterator[Any]:
        try:
            with self._get_pool().connection() as connection:
                yield connection
        except DatabaseError:
            raise
        except Exception as error:
            if type(error).__name__ in {"ForeignKeyViolation", "UniqueViolation", "CheckViolation"}:
                raise DatabaseError(
                    "database_invalid_relationship",
                    "The requested persistent record conflicts with an existing relationship or constraint.",
                    retryable=False,
                    details={"database_error": type(error).__name__},
                ) from error
            raise DatabaseError(
                "database_operation_failed",
                "The persistent storage operation failed.",
                details={"database_error": type(error).__name__},
            ) from error


@lru_cache(maxsize=1)
def get_database() -> Database:
    return Database(os.getenv("SUPABASE_DB_URL", "").strip())
