"""Catalog: titles (movies and series), genres, countries, seasons, episodes."""

from decimal import Decimal

from sqlalchemy import Column, ForeignKey, Numeric, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, enum_column
from app.models.enums import TitleType

title_genres = Table(
    "title_genres",
    Base.metadata,
    Column("title_id", ForeignKey("titles.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)

title_countries = Table(
    "title_countries",
    Base.metadata,
    Column("title_id", ForeignKey("titles.id", ondelete="CASCADE"), primary_key=True),
    Column("country_id", ForeignKey("countries.id", ondelete="CASCADE"), primary_key=True),
)


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int | None] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(2), unique=True)  # ISO 3166-1 alpha-2
    name: Mapped[str] = mapped_column(String(100))


class Title(CreatedAtMixin, Base):
    __tablename__ = "titles"

    id: Mapped[int] = mapped_column(primary_key=True)
    tmdb_id: Mapped[int | None] = mapped_column(unique=True)
    type: Mapped[TitleType] = mapped_column(enum_column(TitleType, "title_type"), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    release_year: Mapped[int | None] = mapped_column(index=True)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    poster_url: Mapped[str | None] = mapped_column(String(500))
    backdrop_url: Mapped[str | None] = mapped_column(String(500))
    duration: Mapped[int | None]  # minutes; for series — typical episode length

    genres: Mapped[list[Genre]] = relationship(secondary=title_genres)
    countries: Mapped[list[Country]] = relationship(secondary=title_countries)
    seasons: Mapped[list["Season"]] = relationship(
        back_populates="title", cascade="all, delete-orphan", order_by="Season.number"
    )


class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = (UniqueConstraint("title_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title_id: Mapped[int] = mapped_column(ForeignKey("titles.id", ondelete="CASCADE"))
    number: Mapped[int]
    name: Mapped[str] = mapped_column(String(255))

    title: Mapped[Title] = relationship(back_populates="seasons")
    episodes: Mapped[list["Episode"]] = relationship(
        back_populates="season", cascade="all, delete-orphan", order_by="Episode.number"
    )


class Episode(Base):
    __tablename__ = "episodes"
    __table_args__ = (UniqueConstraint("season_id", "number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id", ondelete="CASCADE"))
    number: Mapped[int]
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    duration: Mapped[int | None]  # minutes

    season: Mapped[Season] = relationship(back_populates="episodes")
