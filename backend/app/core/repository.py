# app/core/repository.py
from typing import Generic, TypeVar, Type, Optional, Sequence
from sqlmodel import Session, SQLModel, select

ModelT = TypeVar("ModelT", bound=SQLModel)


class BaseRepository(Generic[ModelT]):
    """
    Repositorio genérico con CRUD básico.
    Solo habla con la DB — nunca levanta HTTPException.
    model es opcional porque los repositorios concretos sobreescriben
    get_by_id y get_all con referencias directas a su modelo.
    """

    def __init__(self, session: Session, model: Optional[Type[ModelT]] = None) -> None:
        self.session = session
        self.model   = model

    def get_by_id(self, record_id: int) -> ModelT | None:
        return self.session.get(self.model, record_id)

    def get_all(self, offset: int = 0, limit: int = 20) -> Sequence[ModelT]:
        return self.session.exec(
            select(self.model).offset(offset).limit(limit)
        ).all()

    def add(self, instance: ModelT) -> ModelT:
        """Persiste sin hacer commit. El UoW decide cuándo commitear."""
        self.session.add(instance)
        self.session.flush()
        self.session.refresh(instance)
        return instance

    def delete(self, instance: ModelT) -> None:
        """Elimina sin hacer commit. El UoW decide cuándo commitear."""
        self.session.delete(instance)
        self.session.flush()
