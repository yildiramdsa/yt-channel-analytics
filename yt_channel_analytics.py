import streamlit as st
import pandas as pd
from datetime import timedelta, datetime

st.set_page_config(page_title="YT Channel Analytics", layout="wide")

# Load dataset with caching
@st.cache_data
def load_youtube_data():
    df = pd.read_csv("youtube_channel_data.csv")
    df['DATE'] = pd.to_datetime(df['DATE'])
    df['NET_SUBSCRIBERS'] = df['SUBSCRIBERS_GAINED'] - df['SUBSCRIBERS_LOST']
    return df

# Custom function to define YouTube-style quarterly periods
def get_custom_quarter(date):
    month, year = date.month, date.year
    if month in [2, 3, 4]:
        return pd.Period(year=year, quarter=1, freq='Q')
    elif month in [5, 6, 7]:
        return pd.Period(year=year, quarter=2, freq='Q')
    elif month in [8, 9, 10]:
        return pd.Period(year=year, quarter=3, freq='Q')
    else:  # Nov-Jan (shift Jan back to previous year's Q4)
        return pd.Period(year=year if month != 1 else year - 1, quarter=4, freq='Q')

# Function to aggregate metrics based on time frequency
def aggregate_metrics(df, freq):
    if freq == 'Q':  # Custom quarterly aggregation
        df['CUSTOM_QUARTER'] = df['DATE'].apply(get_custom_quarter)
        return df.groupby('CUSTOM_QUARTER').agg({
            'VIEWS': 'sum', 'WATCH_HOURS': 'sum', 'NET_SUBSCRIBERS': 'sum',
            'LIKES': 'sum', 'COMMENTS': 'sum', 'SHARES': 'sum'
        })
    else:
        return df.resample(freq, on='DATE').agg({
            'VIEWS': 'sum', 'WATCH_HOURS': 'sum', 'NET_SUBSCRIBERS': 'sum',
            'LIKES': 'sum', 'COMMENTS': 'sum', 'SHARES': 'sum'
        })

# Functions to get different time-based aggregations
def get_weekly_metrics(df): return aggregate_metrics(df, 'W-MON')
def get_monthly_metrics(df): return aggregate_metrics(df, 'M')
def get_quarterly_metrics(df): return aggregate_metrics(df, 'Q')

# Helper function to format numbers with commas
def format_number(value):
    return f"{value:,}"

# Function to create charts for YouTube metrics
def render_metric_chart(df, metric_column, color, chart_type, height=150, time_frame='Daily'):
    chart_data = df[[metric_column]].copy()
    if time_frame == 'Quarterly':
        chart_data.index = chart_data.index.strftime('%Y Q%q ')
    if chart_type == 'Bar':
        st.bar_chart(chart_data, y=metric_column, color=color, height=height)
    if chart_type == 'Area':
        st.area_chart(chart_data, y=metric_column, color=color, height=height)

# Function to check if a reporting period is complete
def is_period_complete(report_date, freq):
    today = datetime.now()
    if freq == 'D':  # Daily
        return report_date.date() < today.date()
    elif freq == 'W':  # Weekly
        return report_date + timedelta(days=6) < today
    elif freq == 'M':  # Monthly
        next_month = report_date.replace(day=28) + timedelta(days=4)
        return next_month.replace(day=1) <= today
    elif freq == 'Q':  # Quarterly
        return report_date < get_custom_quarter(today)

# Function to compute week-over-week, month-over-month changes
def compute_metric_change(df, metric_column):
    if len(df) < 2:
        return 0, 0
    latest_value, previous_value = df[metric_column].iloc[-1], df[metric_column].iloc[-2]
    delta = latest_value - previous_value
    delta_percent = (delta / previous_value) * 100 if previous_value != 0 else 0
    return delta, delta_percent

# Function to display key metrics
def display_key_metric(col, title, value, df, metric_column, color, time_frame):
    with col:
        with st.container(border=True):
            delta, delta_percent = compute_metric_change(df, metric_column)
            st.metric(title, format_number(value), delta=f"{delta:+,.0f} ({delta_percent:+.2f}%)")
            render_metric_chart(df, metric_column, color, time_frame=time_frame, chart_type=chart_selection)

            last_period = df.index[-1]
            freq_mapping = {'Daily': 'D', 'Weekly': 'W', 'Monthly': 'M', 'Quarterly': 'Q'}
            if not is_period_complete(last_period, freq_mapping[time_frame]):
                st.caption(f"Note: The last {time_frame.lower()} is incomplete.")

df = load_youtube_data()

st.logo(image="yt_logo_lg.png", icon_image="yt_logo_sm.png")

# Sidebar configuration
with st.sidebar:
    st.title("YT Channel Analytics")
    st.header("⚙️ Settings")

    max_date = df['DATE'].max().date()
    default_start_date = max_date - timedelta(days=365)
    start_date = st.date_input("Start Date", default_start_date, min_value=df['DATE'].min().date(), max_value=max_date)
    end_date = st.date_input("End Date", max_date, min_value=df['DATE'].min().date(), max_value=max_date)
    time_frame = st.selectbox("Select Time Frame", ["Daily", "Weekly", "Monthly", "Quarterly"])
    chart_selection = st.selectbox("Select Chart Type", ["Bar", "Area"])

# Prepare data based on selected time frame
if time_frame == 'Daily':
    df_display = df.set_index('DATE')
elif time_frame == 'Weekly':
    df_display = get_weekly_metrics(df)
elif time_frame == 'Monthly':
    df_display = get_monthly_metrics(df)
elif time_frame == 'Quarterly':
    df_display = get_quarterly_metrics(df)

st.subheader("All-Time Metrics")

metrics = [
    ("Total Subscribers", "NET_SUBSCRIBERS", '#028283'),
    ("Total Views", "VIEWS", '#df336b'),
    ("Total Watch Hours", "WATCH_HOURS", '#e7541e'),
    ("Total Likes", "LIKES", '#e0b15f')
]

cols = st.columns(4)
for col, (title, metric_column, color) in zip(cols, metrics):
    total_value = df[metric_column].sum()
    display_key_metric(col, title, total_value, df_display, metric_column, color, time_frame)

st.subheader("Metrics for Selected Period")

if time_frame == 'Quarterly':
    start_quarter, end_quarter = get_custom_quarter(start_date), get_custom_quarter(end_date)
    df_filtered = df_display.loc[(df_display.index >= start_quarter) & (df_display.index <= end_quarter)]
else:
    df_filtered = df_display.loc[(df_display.index >= pd.Timestamp(start_date)) & (df_display.index <= pd.Timestamp(end_date))]

cols = st.columns(4)
for col, (title, metric_column, color) in zip(cols, metrics):
    display_key_metric(col, title.split()[-1], df_filtered[metric_column].sum(), df_filtered, metric_column, color, time_frame)

with st.expander("View Data (Selected Time Frame)"):
    st.dataframe(df_filtered)