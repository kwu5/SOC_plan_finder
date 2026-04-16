import streamlit as st

st.set_page_config(page_title="SOC Plan Finder", page_icon=":mag:", layout="wide")

st.title("SOC Plan Finder")

st.markdown(
    """
    Find combinations of insurance plans whose total premium falls in a target range.

    **Use the sidebar to navigate:**

    1. **Providers** — manage providers (and whether multiple plans under one provider may be combined).
    2. **Plans** — add, edit, enable or disable individual plans.
    3. **Rules** — define mutual-exclusion rules between specific plans.
    4. **Search** — enter minimum premium `y` and optional ceiling extension `x`; get combinations with `y < total <= y + x`.
    """
)
