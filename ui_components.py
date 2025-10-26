import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import base64
from typing import Dict, List, Optional

# Modern UI Components and Styling

def set_custom_theme():
    """Set modern theme with dark/light mode support."""
    theme = st.session_state.get("theme", "light")

    if theme == "dark":
        st.markdown("""
        <style>
        .stApp {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        .stSidebar {
            background-color: #2d2d2d;
        }
        .stButton>button {
            background-color: #4a4a4a;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #5a5a5a;
            transform: translateY(-2px);
        }
        .stSelectbox>div>div {
            background-color: #3a3a3a;
        }
        .stTextInput>div>div>input {
            background-color: #3a3a3a;
            color: white;
        }
        .dataframe {
            background-color: #2d2d2d;
            color: white;
        }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
        .stButton>button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }
        .metric-card {
            background: white;
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            border-left: 4px solid #667eea;
            margin-bottom: 1rem;
            transition: transform 0.2s ease;
        }
        .metric-card:hover {
            transform: translateY(-2px);
        }
        .patient-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }
        .patient-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        }
        .alert-success {
            background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
            border-radius: 12px;
            padding: 1rem;
            color: #0d5d2e;
            font-weight: 500;
        }
        .alert-warning {
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
            border-radius: 12px;
            padding: 1rem;
            color: #8b4513;
            font-weight: 500;
        }
        .alert-error {
            background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
            border-radius: 12px;
            padding: 1rem;
            color: #721c24;
            font-weight: 500;
        }
        .header-gradient {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 16px;
            margin-bottom: 2rem;
            text-align: center;
        }
        </style>
        """, unsafe_allow_html=True)

def modern_metric_card(title: str, value: str, delta: Optional[str] = None,
                      icon: Optional[str] = None, color: str = "blue"):
    """Create a modern metric card with icon and gradient."""
    colors = {
        "blue": "#667eea",
        "green": "#48bb78",
        "red": "#f56565",
        "purple": "#9f7aea",
        "orange": "#ed8936"
    }

    icon_html = f"📊" if icon else ""

    st.markdown(f"""
    <div class="metric-card" style="border-left-color: {colors.get(color, '#667eea')};">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-size: 0.875rem; color: #718096; margin-bottom: 0.25rem;">{title}</div>
                <div style="font-size: 1.875rem; font-weight: 700; color: #1a202c;">{value}</div>
                {f'<div style="font-size: 0.875rem; color: #48bb78;">{delta}</div>' if delta else ''}
            </div>
            <div style="font-size: 2rem; opacity: 0.7;">{icon_html}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def patient_summary_card(patient_data: Dict, last_encounter: Optional[Dict] = None):
    """Create a patient summary card with key information."""
    age = datetime.now().year - patient_data['dob'].year if patient_data['dob'] else 'N/A'

    # Use container to create a card-like appearance
    with st.container():
        # Header with name and gender
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(patient_data['name'])
            st.caption(f"Patient ID: {patient_data['id']}")
        with col2:
            gender_color = get_gender_color(patient_data['gender'])
            st.markdown(f"""
            <div style="background: {gender_color}; color: white; padding: 0.5rem 1rem;
                        border-radius: 20px; font-size: 0.875rem; font-weight: 600; text-align: center;">
                {patient_data['gender']}
            </div>
            """, unsafe_allow_html=True)

        # Patient details in columns
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Age", f"{age} years")
        with col2:
            st.metric("Contact", patient_data['contact'])
        with col3:
            last_visit = last_encounter['date'].strftime('%Y-%m-%d') if last_encounter else 'No visits'
            st.metric("Last Visit", last_visit)

        # Address
        with st.expander("📍 Address", expanded=False):
            st.info(patient_data['address'])

def get_gender_color(gender: str) -> str:
    """Get color based on gender."""
    colors = {
        "Male": "#4299e1",
        "Female": "#ed64a6",
        "Other": "#9f7aea"
    }
    return colors.get(gender, "#718096")

def create_activity_timeline(encounters_df: pd.DataFrame):
    """Create an interactive timeline of patient encounters."""
    if encounters_df.empty:
        st.info("No encounters to display")
        return

    # Create timeline figure
    fig = make_subplots(
        rows=1, cols=1,
        subplot_titles=["Patient Journey Timeline"],
        vertical_spacing=0.1
    )

    # Color mapping for encounter types
    colors = {
        "Consultation": "#667eea",
        "Follow-up": "#48bb78",
        "Emergency": "#f56565",
        "Procedure": "#ed8936"
    }

    for i, (_, encounter) in enumerate(encounters_df.iterrows()):
        fig.add_trace(
            go.Scatter(
                x=[encounter['date']],
                y=[i],
                mode='markers+text',
                marker=dict(
                    size=20,
                    color=colors.get(encounter['type'], '#718096'),
                    symbol='circle',
                    line=dict(width=2, color='white')
                ),
                text=f"{encounter['type']}<br>{encounter['date'].strftime('%b %d, %Y')}<br>Dr. {encounter['doctor']}",
                textposition="top center",
                hovertemplate=f"<b>{encounter['type']}</b><br>"
                             f"Date: {encounter['date'].strftime('%Y-%m-%d')}<br>"
                             f"Doctor: {encounter['doctor']}<br>"
                             f"Notes: {encounter['notes'][:100]}...<extra></extra>",
                name=encounter['type']
            ),
            row=1, col=1
        )

    fig.update_layout(
        height=400,
        showlegend=False,
        yaxis=dict(showticklabels=False),
        xaxis=dict(title="Date"),
        title={
            'text': "Patient Journey Timeline",
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        plot_bgcolor='rgba(0,0,0,0)'
    )

    st.plotly_chart(fig, use_container_width=True)

def create_health_dashboard(vitals_df: pd.DataFrame, patient_age: int):
    """Create a comprehensive health dashboard with vitals trends."""
    if vitals_df.empty:
        st.info("No vitals data available")
        return

    # Create subplots for multiple vitals
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Heart Rate Trend", "Blood Pressure Trend", "Temperature Trend", "Vitals Summary"),
        specs=[[{"secondary_y": False}, {"secondary_y": False}],
               [{"secondary_y": False}, {"type": "bar"}]]
    )

    # Heart Rate
    fig.add_trace(
        go.Scatter(x=vitals_df['timestamp'], y=vitals_df['heart_rate'],
                  mode='lines+markers', name='Heart Rate',
                  line=dict(color='#f56565', width=3)),
        row=1, col=1
    )

    # Blood Pressure (split systolic/diastolic)
    if 'bp' in vitals_df.columns:
        vitals_df[['systolic', 'diastolic']] = vitals_df['bp'].str.split('/', expand=True).astype(float)
        fig.add_trace(
            go.Scatter(x=vitals_df['timestamp'], y=vitals_df['systolic'],
                      mode='lines+markers', name='Systolic',
                      line=dict(color='#4299e1', width=3)),
            row=1, col=2
        )
        fig.add_trace(
            go.Scatter(x=vitals_df['timestamp'], y=vitals_df['diastolic'],
                      mode='lines+markers', name='Diastolic',
                      line=dict(color='#48bb78', width=3)),
            row=1, col=2
        )

    # Temperature
    if 'temp' in vitals_df.columns:
        fig.add_trace(
            go.Scatter(x=vitals_df['timestamp'], y=vitals_df['temp'],
                      mode='lines+markers', name='Temperature',
                      line=dict(color='#ed8936', width=3)),
            row=2, col=1
        )

    # Summary statistics
    latest_vitals = vitals_df.iloc[-1]
    fig.add_trace(
        go.Bar(x=['Heart Rate', 'Temperature'],
               y=[latest_vitals['heart_rate'], latest_vitals['temp'] if 'temp' in latest_vitals else 0],
               name='Latest Vitals',
               marker_color=['#f56565', '#ed8936']),
        row=2, col=2
    )

    fig.update_layout(
        height=800,
        title_text="Health Analytics Dashboard",
        showlegend=True,
        plot_bgcolor='rgba(0,0,0,0.02)'
    )

    st.plotly_chart(fig, use_container_width=True)

def smart_search_bar(data: pd.DataFrame, search_columns: List[str], key: str):
    """Create an intelligent search bar with autocomplete."""
    search_term = st.text_input("🔍 Search", key=f"search_{key}", placeholder="Type to search...")

    if search_term:
        mask = data[search_columns].apply(
            lambda x: x.astype(str).str.contains(search_term, case=False, na=False)
        ).any(axis=1)
        filtered_data = data[mask]
    else:
        filtered_data = data

    return filtered_data, search_term

def notification_system():
    """Display real-time notifications and alerts."""
    if "notifications" not in st.session_state:
        st.session_state.notifications = []

    # Add some sample notifications
    if not st.session_state.notifications:
        st.session_state.notifications = [
            {"type": "success", "message": "Patient John Doe scheduled for follow-up", "time": datetime.now()},
            {"type": "warning", "message": "Lab results pending for Jane Smith", "time": datetime.now() - timedelta(hours=2)},
            {"type": "info", "message": "System backup completed successfully", "time": datetime.now() - timedelta(hours=4)}
        ]

    # Display notifications
    for notification in st.session_state.notifications[-3:]:  # Show last 3
        time_str = notification["time"].strftime("%H:%M")

        if notification["type"] == "success":
            st.markdown(f"""
            <div class="alert-success">
                ✅ {notification["message"]} <span style="float: right; opacity: 0.7;">{time_str}</span>
            </div>
            """, unsafe_allow_html=True)
        elif notification["type"] == "warning":
            st.markdown(f"""
            <div class="alert-warning">
                ⚠️ {notification["message"]} <span style="float: right; opacity: 0.7;">{time_str}</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background: #e3f2fd; border-radius: 8px; padding: 0.75rem; margin-bottom: 0.5rem;">
                ℹ️ {notification["message"]} <span style="float: right; opacity: 0.7;">{time_str}</span>
            </div>
            """, unsafe_allow_html=True)

def theme_toggle():
    """Add theme toggle button to sidebar."""
    current_theme = st.session_state.get("theme", "light")
    new_theme = "dark" if current_theme == "light" else "light"

    if st.sidebar.button(f"🌙 {new_theme.title()} Mode"):
        st.session_state.theme = new_theme
        st.rerun()

def loading_animation(message: str = "Loading..."):
    """Show modern loading animation."""
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem;">
        <div style="display: inline-block; width: 50px; height: 50px; border: 3px solid #f3f3f3;
                    border-top: 3px solid #667eea; border-radius: 50%; animation: spin 1s linear infinite;"></div>
        <p style="margin-top: 1rem; color: #718096;">{message}</p>
    </div>
    <style>
    @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
    }}
    </style>
    """, unsafe_allow_html=True)

def progress_bar_with_percentage(current: int, total: int, label: str = "Progress"):
    """Create a modern progress bar with percentage."""
    percentage = (current / total) * 100 if total > 0 else 0

    st.markdown(f"""
    <div style="margin-bottom: 1rem;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
            <span style="font-weight: 600; color: #2d3748;">{label}</span>
            <span style="color: #718096;">{current}/{total} ({percentage:.1f}%)</span>
        </div>
        <div style="background: #e2e8f0; border-radius: 10px; height: 8px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
                        height: 100%; width: {percentage}%; transition: width 0.3s ease;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)