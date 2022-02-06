from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql.expression import text
from sqlalchemy.sql.sqltypes import TIMESTAMP
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, nullable=False)
    username = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False,
                        server_default=text("now()"))
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True)


class Token(Base):
    __tablename__ = "tokens"
    id = Column(Integer, primary_key=True, nullable=False)
    token = Column(String, nullable=False)
    email = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False,
                        server_default=text("now()"))
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False,
                        default=datetime.now() + timedelta(hours=24))


class Manipulation(Base):
    __tablename__ = "manipulations"
    id = Column(Integer, primary_key=True, nullable=False)
    token_id = Column(
        Integer, ForeignKey("tokens.id", ondelete="CASCADE"),
        nullable=False
    )
    manipulation = Column(String, nullable=False)
    token = relationship(
        "Token",
        backref=backref("manipulations", uselist=False)
    )
