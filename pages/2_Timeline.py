"""Streamlit page for Andrew Ng timeline events."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import get_settings
from src.timeline.timeline_loader import load_timeline


st.set_page_config(page_title="Andrew Ng Timeline", page_icon="Timeline", layout="wide")

settings = get_settings()
st.title("Andrew Ng Timeline")

events = load_timeline(settings.timeline_file)
if not settings.timeline_file.exists():
    st.warning("Timeline file not found. Please add data/timeline/andrew_ng_timeline.json.")
elif not events:
    st.warning("No valid timeline events are available.")
else:
    df = pd.DataFrame(events)
    categories = ["All"] + sorted(df["category"].unique().tolist())
    category = st.selectbox("Category filter", categories)
    search_query = st.text_input("Search timeline", value="")

    filtered = df
    if category != "All":
        filtered = filtered[filtered["category"] == category]
    if search_query:
        query = search_query.lower()
        filtered = filtered[
            filtered["event"].str.lower().str.contains(query)
            | filtered["category"].str.lower().str.contains(query)
            | filtered["source"].str.lower().str.contains(query)
        ]

    st.dataframe(filtered[["year", "event", "category", "source", "confidence"]], use_container_width=True, hide_index=True)

    for event in filtered.to_dict("records"):
        st.markdown(
            f"**{event['year']}** - {event['event']}  \n"
            f"Category: `{event['category']}` | Source: `{event['source']}` | Confidence: `{event['confidence']}`"
        )
