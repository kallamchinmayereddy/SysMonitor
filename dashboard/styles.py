"""
SysMonitor Dashboard UI Theme & Visual Styling
Provides custom dark-themed CSS, responsive metric card components,
and standardized Plotly figure templates.
"""
import plotly.graph_objects as go
import streamlit as st


DARK_THEME_CSS = """
<style>
    /* Global App Container */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }

    /* Professional Metric Cards */
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        border-color: #58a6ff;
        transform: translateY(-2px);
    }
    .metric-title {
        color: #8b949e;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .metric-value {
        color: #f0f6fc;
        font-size: 1.8rem;
        font-weight: 700;
        line-height: 1.2;
    }
    .metric-sub {
        color: #8b949e;
        font-size: 0.8rem;
        margin-top: 6px;
    }

    /* Status Badges */
    .badge {
        display: inline-block;
        padding: 3px 8px;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 12px;
        text-transform: uppercase;
    }
    .badge-optimal { background-color: rgba(46, 160, 67, 0.2); color: #3fb950; border: 1px solid #238636; }
    .badge-warning { background-color: rgba(210, 153, 34, 0.2); color: #d29922; border: 1px solid #9e6a03; }
    .badge-critical { background-color: rgba(248, 81, 73, 0.2); color: #f85149; border: 1px solid #da3633; }
    .badge-info { background-color: rgba(88, 166, 255, 0.2); color: #58a6ff; border: 1px solid #1f6feb; }

    /* Headers and Dividers */
    h1, h2, h3, h4 {
        color: #f0f6fc !important;
        font-weight: 600 !important;
    }
    hr {
        border-color: #30363d !important;
    }

    /* DataFrame Table Styling */
    div[data-testid="stDataFrame"] {
        border: 1px solid #30363d;
        border-radius: 6px;
        background-color: #161b22;
    }
</style>
"""


def apply_custom_css():
    """Injects high-fidelity dark styling into the Streamlit app."""
    st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)


def render_metric_card(
    title: str,
    value: str,
    subtext: str = "",
    badge_text: str = "",
    badge_type: str = "info",
) -> str:
    """Returns HTML for a responsive dashboard metric card without markdown indentation."""
    s_subtext = str(subtext).replace("<", "&lt;").replace(">", "&gt;")
    s_val = str(value).replace("<", "&lt;").replace(">", "&gt;")
    s_title = str(title).replace("<", "&lt;").replace(">", "&gt;")
    badge_html = f'<span class="badge badge-{badge_type}">{badge_text}</span>' if badge_text else ""
    return (
        f'<div class="metric-card">'
        f'<div style="display: flex; justify-content: space-between; align-items: center;">'
        f'<div class="metric-title">{s_title}</div>{badge_html}'
        f'</div>'
        f'<div class="metric-value">{s_val}</div>'
        f'<div class="metric-sub">{s_subtext}</div>'
        f'</div>'
    )


def get_plotly_layout(
    title: str = "",
    height: int = 350,
    xaxis_title: str = "",
    yaxis_title: str = "",
    show_legend: bool = True,
) -> dict:
    """Returns standardized dark theme layout settings for Plotly graphs."""
    return dict(
        title=dict(text=title, font=dict(color="#f0f6fc", size=14)),
        height=height,
        paper_bgcolor="#161b22",
        plot_bgcolor="#0d1117",
        font=dict(color="#8b949e", family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto"),
        margin=dict(l=40, r=20, t=40, b=40),
        legend=dict(
            font=dict(color="#c9d1d9"),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ) if show_legend else dict(visible=False),
        xaxis=dict(
            title=xaxis_title,
            gridcolor="#21262d",
            zerolinecolor="#30363d",
            color="#8b949e",
        ),
        yaxis=dict(
            title=yaxis_title,
            gridcolor="#21262d",
            zerolinecolor="#30363d",
            color="#8b949e",
        ),
    )
