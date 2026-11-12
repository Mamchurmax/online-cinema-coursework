"""Pattern: Strategy (GoF) — playback rules of a subscription plan.

- Strategy:          `PlaybackPolicy` — what a viewer may watch and whether an ad is shown.
- Concrete strategies:
    `FreePolicy`    — ad-supported plans: qualities up to the plan limit (720p for Free)
                      and a pre-roll ad before the video;
    `PremiumPolicy` — ad-free plans: qualities up to the plan limit (1080p), no ads.
- Context:           `StreamAccessProxy` / `PlaybackService` — they ask the policy and never
                     check the plan code themselves, so a new plan (e.g. "Family") means one
                     new class plus a line in `policy_for_plan`, not edits all over the code.
"""

from abc import ABC, abstractmethod

from app.models import Plan


def quality_height(quality: str) -> int:
    """'720p' -> 720. Unknown labels sort first, so they are never treated as high quality."""
    digits = quality.rstrip("pP")
    return int(digits) if digits.isdigit() else 0


class PlaybackPolicy(ABC):
    """Strategy interface."""

    def __init__(self, plan: Plan) -> None:
        self.plan = plan

    @property
    def max_quality(self) -> str:
        return self.plan.max_quality

    def allowed_qualities(self, available: list[str]) -> list[str]:
        """Qualities of a video this plan may stream, lowest first."""
        limit = quality_height(self.max_quality)
        allowed = [q for q in available if 0 < quality_height(q) <= limit]
        return sorted(allowed, key=quality_height)

    @abstractmethod
    def requires_preroll_ad(self) -> bool:
        """Whether an ad must be played before the video starts."""


class FreePolicy(PlaybackPolicy):
    """Concrete strategy for the Free plan."""

    def requires_preroll_ad(self) -> bool:
        return True


class PremiumPolicy(PlaybackPolicy):
    """Concrete strategy for the Premium plan."""

    def requires_preroll_ad(self) -> bool:
        return False


def policy_for_plan(plan: Plan) -> PlaybackPolicy:
    """Choose the strategy from the plan settings (an admin may change them later)."""
    return FreePolicy(plan) if plan.has_ads else PremiumPolicy(plan)
