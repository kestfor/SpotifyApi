from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    __repr_attrs__ = []

    def __repr__(self):
        return (f"<{self.__class__.__name__} "
                f"{', '.join([f'{attr}={getattr(self, attr)}' for attr in self.__repr_attrs__])}>")
