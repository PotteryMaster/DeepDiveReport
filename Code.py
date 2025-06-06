import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Deep Dive Report", layout="wide")
st.title("Deep Dive Report")

# --- Initialize session state
if "uploaded_df" not in st.session_state:
    st.session_state.uploaded_df = pd.DataFrame()
if "site_notes" not in st.session_state:
    st.session_state.site_notes = {}
if "last_checked_df" not in st.session_state:
    st.session_state.last_checked_df = pd.DataFrame()





# --- Sidebar: Upload Section ---
st.sidebar.header("Upload Data")
uploaded_file = st.sidebar.file_uploader(
    "Upload Main CSV File", 
    type=["csv"], 
    help="Must include 'SiteName', 'Date', 'Energy kWh', 'Baseline kWh'."
)

st.sidebar.markdown("---")

# --- Sidebar: Previous Notes Upload ---
st.sidebar.header("Import Previous Notes")
notes_file = st.sidebar.file_uploader("Upload Notes CSV", type=["csv"], key="notes_upload")

if notes_file:
    try:
        notes_df = pd.read_csv(notes_file)
        required_note_cols = {"Site Name", "Comments", "Dates", "Free Text Note"}
        if not required_note_cols.issubset(notes_df.columns):
            st.sidebar.error(f"Notes CSV must contain: {', '.join(required_note_cols)}")
        else:
            def parse_dates_range(dates_str):
                if pd.isna(dates_str) or dates_str.strip() == "":
                    return (None, None)
                try:
                    parts = dates_str.split("to")
                    start = parts[0].strip()
                    end = parts[1].strip() if len(parts) > 1 else start
                    start_date = datetime.datetime.strptime(start, "%d/%m/%Y").date()
                    end_date = datetime.datetime.strptime(end, "%d/%m/%Y").date()
                    return (start_date, end_date)
                except Exception:
                    return (None, None)

            for _, row in notes_df.iterrows():
                site = row["Site Name"]
                comment = row["Comments"]
                start_date, end_date = parse_dates_range(row["Dates"])
                free_text = row["Free Text Note"] if not pd.isna(row["Free Text Note"]) else ""
                st.session_state.site_notes[site] = {
                    "comment": comment,
                    "date_range": (start_date, end_date),
                    "free_text": free_text,
                }
            st.sidebar.success("Notes imported.")
    except Exception as e:
        st.sidebar.error(f"Error reading notes file: {e}")

# --- Handle uploaded main CSV ---
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)
        required_cols = {"SiteName", "Date", "Energy kWh", "Baseline kWh"}
        if not required_cols.issubset(df.columns):
            st.error(f"CSV must contain: {', '.join(required_cols)}")
        else:
            df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
            df = df.dropna(subset=["Date"])
            df["Optimization Date"] = pd.to_datetime(df.get("Optimization Date"), errors='coerce')
            st.session_state.uploaded_df = df
            st.success("Main data uploaded and processed.")
    except Exception as e:
        st.error(f"Error reading file: {e}")

# --- Upload the new "Last Checked" file ---
st.sidebar.markdown("---")
st.sidebar.header("Upload Last Checked Data (Optional)")
last_checked_file = st.sidebar.file_uploader(
    "Upload CSV with Last Checked", type=["csv"], key="last_checked_upload",
    help="Must include 'Site Name', 'Comments', 'Dates', 'Free Text Note', and 'Last Checked'."
)

if last_checked_file:
    try:
        last_checked_df = pd.read_csv(last_checked_file)
        required_last_checked_cols = {"Site Name", "Comments", "Dates", "Free Text Note", "Last Checked"}
        if not required_last_checked_cols.issubset(last_checked_df.columns):
            st.sidebar.error(f"Last Checked CSV must contain: {', '.join(required_last_checked_cols)}")
        else:
            def parse_dates_range(dates_str):
                if pd.isna(dates_str) or dates_str.strip() == "":
                    return (None, None)
                try:
                    parts = dates_str.split("to")
                    start = parts[0].strip()
                    end = parts[1].strip() if len(parts) > 1 else start
                    start_date = datetime.datetime.strptime(start, "%d/%m/%Y").date()
                    end_date = datetime.datetime.strptime(end, "%d/%m/%Y").date()
                    return (start_date, end_date)
                except Exception:
                    return (None, None)

            last_checked_df["Parsed Date Range"] = last_checked_df["Dates"].apply(parse_dates_range)
            last_checked_df["Last Checked"] = pd.to_datetime(last_checked_df["Last Checked"], errors='coerce')

            st.session_state.last_checked_df = last_checked_df
            st.sidebar.success("Last Checked data uploaded and processed.")
    except Exception as e:
        st.sidebar.error(f"Error reading Last Checked file: {e}")

df = st.session_state.uploaded_df
last_checked_df = st.session_state.last_checked_df


if not df.empty:
    all_sites = list(df["SiteName"].unique())
    done_sites = [site for site in st.session_state.site_notes if site in all_sites]
    sites_without_notes = [site for site in all_sites if site not in done_sites]
    if not last_checked_df.empty:
        sites_with_last_checked = set(last_checked_df["Site Name"].dropna().unique())
        not_checked = [site for site in all_sites if site not in sites_with_last_checked]
    else:
        not_checked = []
else:
    all_sites = done_sites = sites_without_notes = []

# --- Sidebar: Filtering Options ---
st.sidebar.markdown("---")
st.sidebar.header("Filter Sites")
graph_done_sites = st.sidebar.checkbox("Show Sites with Notes", value=True)
graph_undone_sites = st.sidebar.checkbox("Show Sites without Notes", value=True)
show_sites_not_checked = st.sidebar.checkbox("Show Sites Not Previously Checked", value=False)

if show_sites_not_checked:
    sites_to_graph = not_checked
else:
    sites_to_graph = []
    if graph_done_sites:
        sites_to_graph += done_sites
    if graph_undone_sites:
        sites_to_graph += sites_without_notes


# --- Main View ---
if not df.empty and sites_to_graph:
    st.subheader("View and Comment on Site")
    col1, col2, col3 = st.columns([2, 2, 4])  # Adjusted for horizontal layout

    with col1:
        selected_site = st.selectbox("Select Site", sites_to_graph)

    with col2:
        current_note = st.session_state.site_notes.get(selected_site, {})
        current_comment = current_note.get("comment", "")
        adjustment_options = ["No Issue", "Missing Energy Data", "Remove 0's", "Consumption Profile Required", "Energy Data appears fabircated", "Significant change in profile", "Spike in Energy Consumption", "Drop in Energy Consumption", "Insignificant Variables", "Insignificant R^2/Sig F"]
        default_adjustments = [c.strip() for c in current_comment.split(",")] if current_comment else []
        selected_adjustments = st.multiselect(
            "Adjustment Type(s)",
            adjustment_options,
            default=default_adjustments
        )

    with col3:
        jan_1 = datetime.date(2022, 1, 1)
        dec_31 = datetime.date(2028, 12, 31)
        stored_range = current_note.get("date_range", (None, None))

        if (
            isinstance(stored_range, tuple)
            and len(stored_range) == 2
            and all(isinstance(d, (datetime.date, datetime.datetime)) for d in stored_range)
        ):
            current_range = tuple(d.date() if isinstance(d, datetime.datetime) else d for d in stored_range)
        else:
            current_range = (jan_1, jan_1)

        current_free_text = current_note.get("free_text", "")

        if any(adj in selected_adjustments for adj in ["Consumption Profile Required", "Spike in Energy Consumption", "Drop in Energy Consumption"]):
            col_date, col_note = st.columns([2, 3])
            with col_date:
                start_date, end_date = st.date_input(
                    "Date Range",
                    value=current_range,
                    min_value=jan_1,
                    max_value=dec_31,
                    format="DD/MM/YYYY",
                )
            with col_note:
                free_text = st.text_input("Additional Notes", value=current_free_text)
        else:
            start_date, end_date = (None, None)
            free_text = st.text_input("Additional Notes", value=current_free_text)

    site_df = df[df["SiteName"] == selected_site].sort_values("Date")

    if st.button("Save Note"):
        selected_comment = ", ".join(selected_adjustments) if selected_adjustments else ""
        latest_date = site_df["Date"].max() if not site_df.empty else None

        st.session_state.site_notes[selected_site] = {
            "comment": selected_comment,
            "date_range": (start_date, end_date),
            "free_text": free_text,
            "latest_data": latest_date,
        }
        st.success(f"Note saved for {selected_site}")


    # --- Plot and Table Section ---
    st.subheader(f"Energy Usage for {selected_site}")
    col_plot, col_table = st.columns([4, 1.33])

    with col_plot:
        fig = px.line(
            site_df,
            x="Date",
            y=["Energy kWh", "Baseline kWh"],
            title=f"{selected_site} – Energy vs Baseline",
            labels={"value": "Energy (kWh)", "variable": "Legend"},
        )
        fig.update_layout(hovermode="x unified")

        optimization_dates = site_df["Optimization Date"].dropna().unique()
        if len(optimization_dates) > 0:
            opt_date = optimization_dates[0]
            fig.add_shape(
                type="line",
                x0=opt_date,
                x1=opt_date,
                y0=0,
                y1=1,
                xref="x",
                yref="paper",
                line=dict(color="Red", width=2, dash="dash")
            )
            fig.add_annotation(
                x=opt_date,
                y=1,
                xref="x",
                yref="paper",
                text="Optimization Date",
                showarrow=True,
                arrowhead=2,
                ax=0,
                ay=-40,
            )

        if not last_checked_df.empty:
            lc_site_rows = last_checked_df[last_checked_df["Site Name"] == selected_site]
            for _, row in lc_site_rows.iterrows():
                last_checked_date = row["Last Checked"]
                if pd.notna(last_checked_date):
                    fig.add_shape(
                        type="line",
                        x0=last_checked_date,
                        x1=last_checked_date,
                        y0=0,
                        y1=1,
                        xref="x",
                        yref="paper",
                        line=dict(color="Orange", width=2, dash="dot")
                    )
                    fig.add_annotation(
                        x=last_checked_date,
                        y=1,
                        xref="x",
                        yref="paper",
                        text="Last Checked",
                        showarrow=True,
                        arrowhead=2,
                        ax=0,
                        ay=-30,
                    )

        st.plotly_chart(fig, use_container_width=True)

    if not last_checked_df.empty:
        with col_table:
            selected_last_checked = last_checked_df[last_checked_df["Site Name"] == selected_site]
            if not selected_last_checked.empty:
                with st.expander("Last Checked Info", expanded=True):
                    transposed = selected_last_checked.iloc[0][["Comments", "Dates", "Free Text Note", "Last Checked"]].to_frame()
                    transposed.columns = ["Value"]
                    transposed.index.name = "Field"
                    st.dataframe(transposed, use_container_width=True, hide_index=True)

    # --- Notes Table ---
    if st.session_state.site_notes:
        st.subheader("All Site Comments")
        notes_df = pd.DataFrame(
            [
                (
                    site,
                    note.get("comment", ""),
                    f"{note['date_range'][0].strftime('%d/%m/%Y')} to {note['date_range'][1].strftime('%d/%m/%Y')}"
                    if note.get("date_range") and note["date_range"][0] and note["date_range"][1]
                    else "",
                    note.get("free_text", ""),
                    note.get("latest_data").strftime('%d/%m/%Y') if note.get("latest_data") else ""
                )
                for site, note in st.session_state.site_notes.items()
            ],
            columns=["Site Name", "Comments", "Dates", "Free Text Note", "Latest Data Point"]
        )
        st.dataframe(notes_df, use_container_width=True, hide_index=True)

else:
    st.info("Upload a CSV file to begin. It must include 'SiteName', 'Date', 'Energy kWh', and 'Baseline kWh' columns.")
