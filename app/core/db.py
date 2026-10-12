from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def criar_engine(url: str) -> Engine:
    if not url.startswith("sqlite"):
        return create_engine(url, pool_pre_ping=True)
    engine = create_engine(url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _ativar_chaves_estrangeiras(conexao, _registro):
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def criar_fabrica(url: str) -> sessionmaker[Session]:
    return sessionmaker(bind=criar_engine(url), autoflush=False, expire_on_commit=False)


@lru_cache
def _fabrica_padrao() -> sessionmaker[Session]:
    return criar_fabrica(get_settings().database_url)


def get_db() -> Iterator[Session]:
    with _fabrica_padrao()() as sessao:
        yield sessao
