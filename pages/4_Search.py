from decimal import Decimal

import pandas as pd
import streamlit as st
from sqlalchemy import select

from db import ExclusionRule, Plan, Provider, session_scope
from search import (
    ExclusionPair,
    SearchPlan,
    SearchProvider,
    find_combinations,
)

st.title("Search combinations")

st.caption("Returns combinations where `y < total premium <= y + x`, subject to provider and exclusion rules.")

col_y, col_x = st.columns(2)
with col_y:
    y_input = st.number_input("Minimum premium (y)", min_value=0.0, step=0.01, format="%.2f")
with col_x:
    use_x = st.checkbox("Adjust ceiling (x)", value=True)
    if use_x:
        x_input = st.number_input(
            "Ceiling extension (x)",
            min_value=0.0,
            value=100.0,
            step=0.01,
            format="%.2f",
            help="Combination total must be <= y + x. Must be > 0 to return results.",
        )
    else:
        x_input = 0.0

run = st.button("Find combinations", type="primary")

if run:
    y = Decimal(str(y_input))
    x = Decimal(str(x_input))

    if x <= 0:
        st.warning("`x` must be greater than 0 — otherwise the range `y < total <= y + x` is empty.")
        st.stop()

    with session_scope() as session:
        providers = session.scalars(select(Provider)).all()
        plans = session.scalars(select(Plan).where(Plan.enabled.is_(True))).all()
        rules = session.scalars(
            select(ExclusionRule).where(ExclusionRule.enabled.is_(True))
        ).all()

        search_providers = [
            SearchProvider(id=p.id, name=p.name, allow_multiple=p.allow_multiple)
            for p in providers
        ]
        search_plans = [
            SearchPlan(id=p.id, name=p.name, provider_id=p.provider_id, premium=p.premium)
            for p in plans
        ]
        search_exclusions = [
            ExclusionPair(plan_a_id=r.plan_a_id, plan_b_id=r.plan_b_id) for r in rules
        ]
        plan_name_by_id = {p.id: p.name for p in plans}
        provider_name_by_id = {p.id: p.name for p in providers}
        plan_provider = {p.id: provider_name_by_id[p.provider_id] for p in plans}
        plan_premium_by_id = {p.id: p.premium for p in plans}

    combos = find_combinations(
        plans=search_plans,
        providers=search_providers,
        exclusions=search_exclusions,
        y=y,
        x=x,
    )

    rows = []
    for c in combos:
        labels = [f"{plan_name_by_id[p.id]} ({plan_provider[p.id]})" for p in c.plans]
        text = "".join(
            f"{plan_provider[p.id]}{plan_premium_by_id[p.id]:.2f}," for p in c.plans
        )
        rows.append(
            {
                "plans": ", ".join(labels),
                "size": len(c.plans),
                "total": float(c.total),
                "overshoot (total - y)": float(c.total - y),
                "text": text,
            }
        )
    st.session_state["search_rows"] = rows

if "search_rows" in st.session_state:
    rows = st.session_state["search_rows"]
    st.write(f"Found **{len(rows)}** combinations.")

    if rows:
        sort_col, order_col = st.columns([2, 1])
        with sort_col:
            sort_by = st.selectbox(
                "Sort by",
                options=["overshoot (total - y)", "size", "total"],
                index=0,
            )
        with order_col:
            order = st.radio("Order", ["Ascending", "Descending"], horizontal=True)
        ascending = order == "Ascending"

        df = (
            pd.DataFrame(rows)
            .sort_values(sort_by, ascending=ascending, kind="stable")
            .reset_index(drop=True)
        )
        st.dataframe(
            df.drop(columns=["text"]),
            use_container_width=True,
            hide_index=True,
            column_config={
                "total": st.column_config.NumberColumn("total", format="%.2f"),
                "overshoot (total - y)": st.column_config.NumberColumn(
                    "overshoot (total - y)", format="%.2f"
                ),
            },
        )

        if st.button("Generate a text"):
            st.code("\n".join(df["text"]), language=None)
