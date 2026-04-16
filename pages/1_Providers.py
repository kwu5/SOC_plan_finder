import pandas as pd
import streamlit as st
from sqlalchemy import select

from db import Provider, session_scope

st.title("Providers")

st.caption(
    "Each provider contributes at most one plan to a combination, "
    "unless `allow_multiple` is enabled."
)

with session_scope() as session:
    providers = session.scalars(select(Provider).order_by(Provider.name)).all()
    rows = [
        {"id": p.id, "name": p.name, "allow_multiple": p.allow_multiple}
        for p in providers
    ]

df = pd.DataFrame(rows, columns=["id", "name", "allow_multiple"])

edited = st.data_editor(
    df,
    num_rows="dynamic",
    column_config={
        "id": st.column_config.NumberColumn("id", disabled=True),
        "name": st.column_config.TextColumn("name", required=True),
        "allow_multiple": st.column_config.CheckboxColumn("allow_multiple"),
    },
    hide_index=True,
    key="providers_editor",
)

if st.button("Save changes", type="primary"):
    try:
        original_by_id = {r["id"]: r for r in rows}
        edited_by_id = {}
        new_rows = []
        for _, row in edited.iterrows():
            rid = row["id"]
            if pd.isna(rid):
                new_rows.append(row)
            else:
                edited_by_id[int(rid)] = row

        with session_scope() as session:
            # Updates
            for rid, row in edited_by_id.items():
                orig = original_by_id.get(rid)
                if orig is None:
                    continue
                if (row["name"] != orig["name"]) or (
                    bool(row["allow_multiple"]) != orig["allow_multiple"]
                ):
                    provider = session.get(Provider, rid)
                    if provider is not None:
                        provider.name = row["name"]
                        provider.allow_multiple = bool(row["allow_multiple"])

            # Deletes
            deleted_ids = set(original_by_id) - set(edited_by_id)
            for rid in deleted_ids:
                provider = session.get(Provider, rid)
                if provider is not None:
                    session.delete(provider)

            # Inserts
            for row in new_rows:
                if not row["name"] or pd.isna(row["name"]):
                    continue
                session.add(
                    Provider(
                        name=str(row["name"]),
                        allow_multiple=bool(row["allow_multiple"])
                        if not pd.isna(row["allow_multiple"])
                        else False,
                    )
                )
        st.success("Saved.")
        st.rerun()
    except Exception as exc:
        st.error(f"Save failed: {exc}")
