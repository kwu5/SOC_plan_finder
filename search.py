from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


@dataclass(frozen=True)
class SearchProvider:
    id: int
    name: str
    allow_multiple: bool


@dataclass(frozen=True)
class SearchPlan:
    id: int
    name: str
    provider_id: int
    premium: Decimal


@dataclass(frozen=True)
class ExclusionPair:
    plan_a_id: int
    plan_b_id: int


@dataclass(frozen=True)
class Combination:
    plans: tuple[SearchPlan, ...]
    total: Decimal


def find_combinations(
    plans: Iterable[SearchPlan],
    providers: Iterable[SearchProvider],
    exclusions: Iterable[ExclusionPair],
    y: Decimal,
    x: Decimal,
) -> list[Combination]:
    """Return all plan combinations whose summed premium is in (y, y + x], subject to rules.

    Rules:
      1. y < sum(p.premium) <= y + x
      2. For any two plans sharing a provider, that provider must have allow_multiple=True.
      3. No two plans may both appear if an exclusion pair links them.
    """
    if x <= 0:
        return []

    plans_sorted: list[SearchPlan] = sorted(plans, key=lambda p: p.premium)
    ceiling: Decimal = y + x

    provider_allows_multiple: dict[int, bool] = {
        p.id: p.allow_multiple for p in providers
    }

    exclusion_map: dict[int, set[int]] = {}
    for pair in exclusions:
        exclusion_map.setdefault(pair.plan_a_id, set()).add(pair.plan_b_id)
        exclusion_map.setdefault(pair.plan_b_id, set()).add(pair.plan_a_id)

    results: list[Combination] = []

    def dfs(
        start: int,
        combo: list[SearchPlan],
        running_sum: Decimal,
        blocked: frozenset[int],
        used_single_providers: frozenset[int],
    ) -> None:
        if combo and y < running_sum <= ceiling:
            results.append(Combination(plans=tuple(combo), total=running_sum))
        if running_sum >= ceiling:
            return

        for i in range(start, len(plans_sorted)):
            plan = plans_sorted[i]
            if plan.id in blocked:
                continue
            allow_multi = provider_allows_multiple.get(plan.provider_id, False)
            if not allow_multi and plan.provider_id in used_single_providers:
                continue
            new_sum = running_sum + plan.premium
            if new_sum > ceiling:
                break  # plans are sorted ascending; later premiums only grow
            new_blocked = blocked | exclusion_map.get(plan.id, frozenset())
            new_used = (
                used_single_providers
                if allow_multi
                else used_single_providers | {plan.provider_id}
            )
            combo.append(plan)
            dfs(i + 1, combo, new_sum, new_blocked, new_used)
            combo.pop()

    dfs(0, [], Decimal(0), frozenset(), frozenset())
    return results
