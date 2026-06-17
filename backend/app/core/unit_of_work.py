# app/core/unit_of_work.py
from sqlmodel import Session


class UnitOfWork:
    """
    Gestiona el ciclo de vida de la transacción.
    Único responsable de commit() y rollback().

    Uso:
        with UnitOfWork(session) as uow:
            uow.repo.add(entity)
        # commit automático; rollback si hay excepción
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self._session.commit()
        else:
            self._session.rollback()
        self._session.close()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
