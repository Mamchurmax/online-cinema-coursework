"""Builds the event bus for one unit of work (one request or script run).

All observers are subscribed here, so this file is the single place that shows
who reacts to which event.
"""

from sqlalchemy.orm import Session

from app.repositories.catalog_repository import TitleRepository
from app.services.events.bus import EventBus
from app.services.events.events import TitleWatched
from app.services.events.listeners import StatisticsListener


def build_event_bus(db: Session) -> EventBus:
    bus = EventBus()

    statistics = StatisticsListener(TitleRepository(db))
    bus.subscribe(TitleWatched, statistics.on_title_watched)

    return bus
