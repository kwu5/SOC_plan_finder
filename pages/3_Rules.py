import pandas as pd
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db import ExclusionRule, Plan, session_scope

st.title("Exclusion rules")
st.caption(
    "Plans linked by an enabled rule may not appear in the same combination. "
    "The default 'one plan per provider' rule is handled automatically on the Providers page."
)

with session_scope() as session:
    plans = session.scalars(
        select(Plan).options(selectinload(Plan.provider)).order_by(Plan.id)
    ).all()
    plans_by_id = {p.id: p for p in plans}
    rules = session.scalars(select(ExclusionRule).order_by(ExclusionRule.id)).all()
    rule_rows = [
        {
            "id": r.id,
            "plan_a": f"{plans_by_id[r.plan_a_id].name} ({plans_by_id[r.plan_a_id].provider.name})"
            if r.plan_a_id in plans_by_id else f"#{r.plan_a_id}",
            "plan_b": f"{plans_by_id[r.plan_b_id].name} ({plans_by_id[r.plan_b_id].provider.name})"
            if r.plan_b_id in plans_by_id else f"#{r.plan_b_id}",
            "enabled": r.enabled,
        }
        for r in rules
    ]

plan_labels = {
    f"{p.name} ({p.provider.name})": p.id for p in plans
}

if len(plans) < 2:
    st.info("Add at least two plans before defining exclusion rules.")
else:
    st.subheader("Add rule")
    with st.form("add_rule", clear_on_submit=True):
        a = st.selectbox("Plan A", list(plan_labels.keys()), key="rule_a")
        b = st.selectbox("Plan B", list(plan_labels.keys()), key="rule_b")
        if st.form_submit_button("Add"):
            if a == b:
                st.error("Plan A and Plan B must be different.")
            else:
                try:
                    with session_scope() as session:
                        session.add(
                            ExclusionRule(
                                plan_a_id=plan_labels[a],
                                plan_b_id=plan_labels[b],
                                enabled=True,
                            )
                        )
                    st.success("Rule added.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not add (duplicate pair?): {exc}")

st.subheader("Existing rules")
if not rule_rows:
    st.write("_No rules defined._")
else:
    df = pd.DataFrame(rule_rows, columns=["id", "plan_a", "plan_b", "enabled"])
    edited = st.data_editor(
        df,
        num_rows="fixed",
        column_config={
            "id": st.column_config.NumberColumn("id", disabled=True),
            "plan_a": st.column_config.TextColumn("plan_a", disabled=True),
            "plan_b": st.column_config.TextColumn("plan_b", disabled=True),
            "enabled": st.column_config.CheckboxColumn("enabled"),
        },
        hide_index=True,
        key="rules_editor",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save enable/disable", type="primary"):
            try:
                enabled_map = {int(r["id"]): bool(r["enabled"]) for _, r in edited.iterrows()}
                with session_scope() as session:
                    for rid, enabled in enabled_map.items():
                        rule = session.get(ExclusionRule, rid)
                        if rule is not None and rule.enabled != enabled:
                            rule.enabled = enabled
                st.success("Saved.")
                st.rerun()
            except Exception as exc:
                st.error(f"Save failed: {exc}")

    with col2:
        delete_id = st.selectbox("Delete rule #", [""] + [r["id"] for r in rule_rows])
        if st.button("Delete"):
            if delete_id == "":
                st.warning("Select a rule id.")
            else:
                try:
                    with session_scope() as session:
                        rule = session.get(ExclusionRule, int(delete_id))
                        if rule is not None:
                            session.delete(rule)
                    st.success(f"Deleted rule #{delete_id}.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Delete failed: {exc}")
