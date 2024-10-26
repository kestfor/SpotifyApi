from sqlalchemy import BigInteger, String, DateTime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'user'

    user_id = mapped_column(BigInteger, primary_key=True)


class Auth(Base):
    __tablename__ = 'auth'

    id = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    access_token = mapped_column(String(255))
    refresh_token = mapped_column(String(255))
    created_at = mapped_column(DateTime)
    token_type = mapped_column(String(255))
    expires_in = mapped_column(DateTime)
    expires_at = mapped_column(DateTime)
    scope = mapped_column(String(255))

    def as_dict(self):
        tmp = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        tmp["created_at"] = tmp["created_at"].isoformat()
        tmp["expires_at"] = tmp["expires_at"].isoformat()
        return tmp