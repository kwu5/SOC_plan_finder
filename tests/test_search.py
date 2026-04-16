from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from search import (
    Combination,
    ExclusionPair,
    SearchPlan,
    SearchProvider,
    find_combinations,
)


D = Decimal


def _combo_ids(combos: list[Combination]) -> set[frozenset[int]]:
    return {frozenset(p.id for p in c.plans) for c in combos}


def test_empty_when_x_is_zero():
    providers = [SearchProvider(1, "A", False)]
    plans = [SearchPlan(1, "p1", 1, D("100"))]
    result = find_combinations(plans, providers, [], y=D("50"), x=D("0"))
    assert result == []


def test_basic_range_filter():
    providers = [SearchProvider(1, "A", True)]  # allow_multiple so provider rule doesn't interfere
    plans = [
        SearchPlan(1, "p1", 1, D("100")),
        SearchPlan(2, "p2", 1, D("150")),
        SearchPlan(3, "p3", 1, D("400")),
    ]
    result = find_combinations(plans, providers, [], y=D("200"), x=D("100"))
    # Valid sums in (200, 300]:
    # {p1} = 100 -> no
    # {p2} = 150 -> no
    # {p1, p2} = 250 -> yes
    # {p3} = 400 -> no
    # {p1, p3} = 500 -> no
    # {p2, p3} = 550 -> no
    # {p1, p2, p3} = 650 -> no
    assert _combo_ids(result) == {frozenset({1, 2})}


def test_provider_single_rule_blocks_same_provider_pair():
    providers = [SearchProvider(1, "A", False)]  # cannot repeat
    plans = [
        SearchPlan(1, "p1", 1, D("100")),
        SearchPlan(2, "p2", 1, D("150")),
    ]
    # {p1, p2} = 250 would be in (200, 300] but same provider, allow_multiple=False => blocked
    result = find_combinations(plans, providers, [], y=D("200"), x=D("100"))
    assert result == []


def test_provider_allow_multiple_permits_same_provider_pair():
    providers = [SearchProvider(1, "A", True)]
    plans = [
        SearchPlan(1, "p1", 1, D("100")),
        SearchPlan(2, "p2", 1, D("150")),
    ]
    result = find_combinations(plans, providers, [], y=D("200"), x=D("100"))
    assert _combo_ids(result) == {frozenset({1, 2})}


def test_exclusion_rule_blocks_pair():
    providers = [
        SearchProvider(1, "A", False),
        SearchProvider(2, "B", False),
    ]
    plans = [
        SearchPlan(1, "p1", 1, D("100")),
        SearchPlan(2, "p2", 2, D("150")),
    ]
    # Without exclusion, {p1, p2} = 250 is valid.
    result_no_rule = find_combinations(plans, providers, [], y=D("200"), x=D("100"))
    assert _combo_ids(result_no_rule) == {frozenset({1, 2})}

    # With an exclusion rule, combo is blocked.
    result_with_rule = find_combinations(
        plans,
        providers,
        [ExclusionPair(1, 2)],
        y=D("200"),
        x=D("100"),
    )
    assert result_with_rule == []


def test_exclusion_rule_reverse_order_blocks_too():
    providers = [
        SearchProvider(1, "A", False),
        SearchProvider(2, "B", False),
    ]
    plans = [
        SearchPlan(1, "p1", 1, D("100")),
        SearchPlan(2, "p2", 2, D("150")),
    ]
    result = find_combinations(
        plans,
        providers,
        [ExclusionPair(2, 1)],  # reverse
        y=D("200"),
        x=D("100"),
    )
    assert result == []


def test_overshoot_pruning_terminates():
    providers = [SearchProvider(i, f"P{i}", False) for i in range(1, 11)]
    plans = [SearchPlan(i, f"p{i}", i, D("1000")) for i in range(1, 11)]
    # ceiling = 500, every plan is already 1000 -> no valid combos, search should return fast.
    result = find_combinations(plans, providers, [], y=D("100"), x=D("400"))
    assert result == []


def test_boundary_lower_exclusive_upper_inclusive():
    providers = [SearchProvider(1, "A", True)]
    plans = [
        SearchPlan(1, "exact_y", 1, D("100")),      # sum == y, excluded
        SearchPlan(2, "just_over", 1, D("101")),    # sum == y + 1, included
        SearchPlan(3, "at_ceiling", 1, D("150")),   # sum == y + x, included (upper inclusive)
    ]
    result = find_combinations(plans, providers, [], y=D("100"), x=D("50"))
    ids = _combo_ids(result)
    # {1} = 100 -> no (not strictly greater than y)
    # {2} = 101 -> yes
    # {3} = 150 -> yes
    # Larger combos exceed ceiling
    assert frozenset({1}) not in ids
    assert frozenset({2}) in ids
    assert frozenset({3}) in ids


def test_mixed_providers_complex():
    # Three providers; one allows multiple. One exclusion rule.
    providers = [
        SearchProvider(1, "A", False),
        SearchProvider(2, "B", True),
        SearchProvider(3, "C", False),
    ]
    plans = [
        SearchPlan(1, "a1", 1, D("50")),
        SearchPlan(2, "b1", 2, D("60")),
        SearchPlan(3, "b2", 2, D("70")),
        SearchPlan(4, "c1", 3, D("40")),
    ]
    # exclude a1 with c1
    exclusions = [ExclusionPair(1, 4)]
    result = find_combinations(plans, providers, exclusions, y=D("100"), x=D("50"))
    # ceiling = 150, need sum in (100, 150]
    # Single plans: 50,60,70,40 -> none > 100
    # Pairs:
    #   a1+b1 = 110 yes
    #   a1+b2 = 120 yes
    #   a1+c1 = 90 no (also excluded by rule anyway)
    #   b1+b2 = 130 yes (provider B allow_multiple)
    #   b1+c1 = 100 no (not strictly greater)
    #   b2+c1 = 110 yes
    # Triples:
    #   a1+b1+b2 = 180 > 150 no
    #   a1+b1+c1 blocked (a1-c1 exclusion)
    #   a1+b2+c1 blocked
    #   b1+b2+c1 = 170 > 150 no
    expected = {
        frozenset({1, 2}),
        frozenset({1, 3}),
        frozenset({2, 3}),
        frozenset({3, 4}),
    }
    assert _combo_ids(result) == expected


def test_empty_plans():
    result = find_combinations([], [], [], y=D("100"), x=D("100"))
    assert result == []


def test_no_empty_combination_emitted():
    providers = [SearchProvider(1, "A", False)]
    plans = [SearchPlan(1, "p1", 1, D("50"))]
    # y is negative so empty combo (sum=0) would satisfy 0 > -10 and 0 <= -10 + 100 = 90.
    # But empty combos must not be emitted.
    result = find_combinations(plans, providers, [], y=D("-10"), x=D("100"))
    for combo in result:
        assert len(combo.plans) > 0
