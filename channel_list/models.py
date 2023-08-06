from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship

from channel_list.database import db


class Base(DeclarativeBase):
    pass


class ChannelModel(Base):
    __tablename__ = 'channels'
    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str]
    name: Mapped[str]
    category_id: Mapped[int] = mapped_column(ForeignKey('categories.id'))
    category: Mapped['CategoryModel'] = relationship(back_populates='channels')


class CategoryModel(Base):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    channels: Mapped['ChannelModel'] = relationship(
        back_populates='category',
        cascade='all,delete-orphan',
    )


Base.metadata.create_all(db)
