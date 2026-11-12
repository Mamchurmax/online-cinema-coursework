"""Errors of admin operations; the API maps them to HTTP status codes."""


class AdminNotFoundError(Exception):
    """404: the object does not exist."""


class AdminConflictError(Exception):
    """409: the change contradicts existing data (duplicate number, payments, self-demotion...)."""


class AdminUnavailableError(Exception):
    """503: an external dependency is not configured (e.g. no TMDB token)."""
