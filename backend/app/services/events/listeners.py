"""Observers of domain events. Each listener does one job (Single Responsibility)."""

from app.repositories.catalog_repository import TitleRepository
from app.services.events.events import DomainEvent, TitleWatched


class StatisticsListener:
    """Counts finished views per title (used by popularity reports and recommendations)."""

    def __init__(self, titles: TitleRepository) -> None:
        self._titles = titles

    def on_title_watched(self, event: DomainEvent) -> None:
        assert isinstance(event, TitleWatched)
        self._titles.increment_watch_count(event.title_id)
