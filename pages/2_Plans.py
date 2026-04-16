from decimal import Decimal

import pandas as pd
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db import Plan, Provider, session_scope

st.title("Plans")

with session_scope() as session:
    providers = session.scalars(select(Provider).order_by(Provider.name)).all()
    plans = session.scalars(
        select(Plan).options(selectinload(Plan.provider)).order_by(Plan.id)
    ).all()
    provider_choices = {p.name: p.id for p in providers}
    plan_rows = [
        {
            "id": p.id,
            "name": p.name,
            "provider": p.provider.name,
            "premium": float(p.premium),
            "enabled": p.enabled,
        }
        for p in plans
    ]

if not provider_choices:
    st.warning("Add at least one provider on the Providers page before adding plans.")
    st.stop()

st.subheader("Add plan")
with st.form("add_plan", clear_on_submit=True):
    name = st.text_input("Name")
    provider_name = st.selectbox("Provider", list(provider_choices.keys()))
    premium = st.number_input("Premium", min_value=0.0, step=0.01, format="%.2f")
    enabled = st.checkbox("Enabled", value=True)
    submitted = st.form_submit_button("Add")
    if submitted:
        if not name.strip():
            st.error("Name is required.")
        else:
            with session_scope() as session:
                session.add(
                    Plan(
                        name=name.strip(),
                        provider_id=provider_choices[provider_name],
                        premium=Decimal(str(premium)),
                        enabled=enabled,
                    )
                )
            st.success(f"Added plan '{name}'.")
            st.rerun()

st.subheader("Existing plans")
df = pd.DataFrame(
    plan_rows, columns=["id", "name", "provider", "premium", "enabled"]
)

edited = st.data_editor(
    df,
    num_rows="dynamic",
    column_config={
        "id": st.column_config.NumberColumn("id", disabled=True),
        "name": st.column_config.TextColumn("name", required=True),
        "provider": st.column_config.SelectboxColumn(
            "provider", options=list(provider_choices.keys()), required=True
        ),
        "premium": st.column_config.NumberColumn("premium", min_value=0.0, step=0.01, format="%.2f"),
        "enabled": st.column_config.CheckboxColumn("enabled"),
    },
    hide_index=True,
    key="plans_editor",
)

if st.button("Save changes", type="primary"):
    try:
        original_by_id = {r["id"]: r for r in plan_rows}
        edited_by_id = {}
        new_rows = []
        for _, row in edited.iterrows():
            rid = row["id"]
            if pd.isna(rid):
                new_rows.append(row)
            else:
                edited_by_id[int(rid)] = row

        with session_scope() as session:
            for rid, row in edited_by_id.items():
                orig = original_by_id.get(rid)
                if orig is None:
                    continue
                plan = session.get(Plan, rid)
                if plan is None:
                    continue
                plan.name = str(row["name"])
                plan.provider_id = provider_choices[row["provider"]]
                plan.premium = Decimal(str(row["premium"]))
                plan.enabled = bool(row["enabled"])

            deleted_ids = set(original_by_id) - set(edited_by_id)
            for rid in deleted_ids:
                plan = session.get(Plan, rid)
                if plan is not None:
                    session.delete(plan)

            for row in new_rows:
                if pd.isna(row["name"]) or not str(row["name"]).strip():
                    continue
                if pd.isna(row.get("provider")):
                    continue
                session.add(
                    Plan(
                        name=str(row["name"]).strip(),
                        provider_id=provider_choices[row["provider"]],
                        premium=Decimal(str(row["premium"] or 0)),
                        enabled=bool(row["enabled"]) if not pd.isna(row["enabled"]) else True,
                    )
                )
        st.success("Saved.")
        st.rerun()
    except Exception as exc:
        st.error(f"Save failed: {exc}")
