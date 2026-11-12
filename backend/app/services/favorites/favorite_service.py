""""Favorites": titles a user wants to keep at hand."""

from collections.abc import Sequence

from app.models import Favorite, Title, User
from app.repositories.catalog_repository import TitleRepository
from app.repositories.favorite_repository import FavoriteRepository


class TitleNotFoundError(Exception):
    pass


class FavoriteService:
    def __init__(self, favorites: FavoriteRepository, titles: TitleRepository) -> None:
        self._favorites = favorites
        self._titles = titles

    def add(self, user: User, title_id: int) -> None:
        """Idempotent: adding a title twice keeps one entry."""
        if self._titles.get(title_id) is None:
            raise TitleNotFoundError(title_id)
        if self._favorites.get(user.id, title_id) is None:
            self._favorites.add(Favorite(user_id=user.id, title_id=title_id))

    def remove(self, user: User, title_id: int) -> None:
        """Idempotent: removing a title that is not there is not an error."""
        favorite = self._favorites.get(user.id, title_id)
        if favorite is not None:
            self._favorites.delete(favorite)

    def titles(self, user: User) -> Sequence[Title]:
        return self._favorites.list_titles(user.id)

    def title_ids(self, user: User) -> list[int]:
        return list(self._favorites.list_title_ids(user.id))
