from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.engine import Dialect
from sqlalchemy.types import TypeDecorator, TypeEngine


class DecimalExato(TypeDecorator[Decimal]):
    """Decimal sem perda: o Numeric do SQLite converte via float, então lá o valor é gravado como texto."""

    impl = Numeric
    cache_ok = True

    def __init__(self, precisao: int = 18, escala: int = 2):
        super().__init__()
        self.precisao = precisao
        self.escala = escala

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine:
        if dialect.name == "sqlite":
            return dialect.type_descriptor(String(40))
        return dialect.type_descriptor(Numeric(self.precisao, self.escala, asdecimal=True))

    def process_bind_param(self, value, dialect: Dialect):
        if value is None:
            return None
        valor = Decimal(value).quantize(Decimal(1).scaleb(-self.escala))
        return str(valor) if dialect.name == "sqlite" else valor

    def process_result_value(self, value, dialect: Dialect):
        if value is None:
            return None
        return value if isinstance(value, Decimal) else Decimal(value)
