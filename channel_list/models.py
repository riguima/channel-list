from typing import List

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from channel_list.database import db


class Base(DeclarativeBase):
    pass


class Channel(Base):
    __tablename__ = 'channels'
    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    url: Mapped[str]
    title: Mapped[str]
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id'))
    category: Mapped['Category'] = relationship(back_populates='channels')


class Category(Base):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    channels: Mapped[List['Channel']] = relationship(
        back_populates='category',
        cascade='all,delete-orphan',
    )


Base.metadata.create_all(db)
