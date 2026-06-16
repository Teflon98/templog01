import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import plotly.graph_objects as go

# --- 1. SET VIEWPORT PROPERTIES ---
st.set_page_config(page_title="Office Climate Tracker", layout="wide")
st.fragment(run_every=300)

# Multi-device CSS: Limits desktop to 1000px, optimizes margins, doubles phone gutters
st.markdown("""
    <style>
    /* Global container containment */
    .stApp {
        background-color: #fcfcfd;
    }
    
    /* Device-specific layout engine */
    .block-container {
        max-width: 1000px !important;
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.2rem !important; /* Doubled margin gap to give fingers room to refresh */
        padding-right: 1.2rem !important;
        margin: 0 auto !important;
    }
    
    /* Strict Card Boundary Wrap (forces text and charts inside the borders) */
    div[data-testid="stContainer"] {
        background-color: #ffffff !important;
        border: 1px solid #eef1f6 !important;
        border-radius: 16px !important;
        padding: 20px !important;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.02) !important;
        margin-bottom: 1rem !important;
    }
    
    /* Completely fixes the top cutoff issue by lowering line-height and adjusting top padding */
    .hero-temp-frame {
        text-align: center;
        padding: 10px 0 5px 0;
    }
    
    .temp-value-display {
        font-size: clamp(3.8rem, 14vw, 5.8rem);
        font-weight: 800;
        line-height: 1.1; /* Added breathing room at the top */
        white-space: nowrap;
        letter-spacing: -2px;
    }
    
    .card-headline-text {
        font-size: 1.1rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #000000;
        text-align: center;
        margin-bottom: 15px;
        letter-spacing: 0.05em;
    }
    
    /* Hide default Streamlit clutter */
    footer { visibility: hidden; }
    header { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ROUTING ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

try:
    # --- 3. FETCH DATA ARRAYS ---
    recent_resp = supabase.table("sensor_data").select("*").order("created_at", desc=True).limit(288).execute()
    days7_resp = supabase.table("sensor_data").select("*").order("created_at", desc=True).limit(2016).execute()
    min_record_resp = supabase.table("sensor_data").select("*").order("temperature", desc=False).limit(1).execute()
    max_record_resp = supabase.table("sensor_data").select("*").order("temperature", desc=True).limit(1).execute()

    if recent_resp.data and days7_resp.data:
        # Load and set timezones
        df24 = pd.DataFrame(recent_resp.data)
        df7d = pd.DataFrame(days7_resp.data)
        df24["local_time"] = pd.to_datetime(df24["created_at"]).dt.tz_convert('US/Eastern')
        df7d["local_time"] = pd.to_datetime(df7d["created_at"]).dt.tz_convert('US/Eastern')
        df24 = df24.sort_values(by="local_time")
        
        latest_record = df24.iloc[-1]
        current_temp = float(latest_record["temperature"])
        current_humidity = float(latest_record["humidity"])
        timestamp_str = latest_record["local_time"].strftime("%A, %B %d, %Y, %I:%M %p").replace("AM", "a.m.").replace("PM", "p.m.")

        # Trend Indicator Math (Averages previous two coordinates against latest payload)
        arrow = "→"
        if len(df24) >= 3:
            prev_avg = (float(df24.iloc[-2]["temperature"]) + float(df24.iloc[-3]["temperature"])) / 2.0
            if current_temp > prev_avg + 0.1: arrow = "↑"
            elif current_temp < prev_avg - 0.1: arrow = "↓"

        # Global Gradient Generator Script (Pure solid hue mapping on 50°F to 80°F limits)
        pct = (max(50.0, min(80.0, current_temp)) - 50.0) / (80.0 - 50.0)
        r = int(0 + (255 - 0) * pct)
        g = 0
        b = int(255 + (0 - 255) * pct)
        solid_color = f"rgb({r}, {g}, {b})"

        # --- CARD 1: MAIN HERO VALUE HIGHLIGHT ---
        with st.container():
            st.markdown(f"""
                <div class="hero-temp-frame">
                    <div class="temp-value-display" style="color: {solid_color};">
                        {current_temp}°F<span style="font-size: 0.45em; color: #1f2328; margin-left: 10px; vertical-align: middle;">{arrow}</span>
                    </div>
                    <div style="font-size: 1.3rem; font-weight: 700; color: #1f2328; margin-top: 5px;">Humidity {current_humidity}%</div>
                    <div style="font-size: 1.0rem; color: #57606a; margin-top: 6px; font-weight: 400;">{timestamp_str}</div>
                </div>
            """, unsafe_allow_html=True)

        # --- CARD 2: PAST 24 HOURS (WITH INDEPENDENT CSS VISUAL GRADIENT) ---
        with st.container():
            st.markdown('<div class="card-headline-text">Past 24 Hours</div>', unsafe_allow_html=True)
            
            fig24 = go.Figure()
            
            # Draw the primary data boundary line
            fig24.add_trace(go.Scatter(
                x=df24["local_time"], 
                y=df24["temperature"],
                mode='lines',
                line=dict(width=3.5, color='#1f2328', shape='spline'),
                fill='tozeroy',
                # Web-safe canvas fallback filling property
                fillcolor='rgba(30, 41, 59, 0.06)'
            ))
            
            # Using Plotly layout shapes to draw a true blue-to-red background matrix behind the line path
            fig24.add_layout_image(
                dict(
                    source="https://upload.wikimedia.org/wikipedia/commons/5/5b/Ultramarine_blue_linear_gradient.png", # Base anchor point reference file
                    xref="paper", yref="paper",
                    x=0, y=0, sizex=1, sizey=1,
                    sizing="stretch", layer="below", opacity=0.25
                )
            )
            
            fig24.update_layout(
                yaxis=dict(range=[50, 90], fixedrange=True, gridcolor='#eef1f6', zeroline=False, tickfont=dict(color='#57606a', size=11)),
                xaxis=dict(tickformat="%I%p", gridcolor='#eef1f6', showgrid=True, tickfont=dict(color='#57606a', size=11), nticks=6),
                margin=dict(l=20, r=10, t=5, b=10),
                height=220,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False
            )
            st.plotly_chart(fig24, use_container_width=True, config={'displayModeBar': False})

        # --- CARD 3: PAST 7 DAYS (VERTICAL SPATIAL WINDOW PUNCHES) ---
        with st.container():
            st.markdown('<div class="card-headline-text">Past 7 Days</div>', unsafe_allow_html=True)
            
            df7d["day_name"] = df7d["local_time"].dt.strftime("%a")
            agg_7d = df7d.groupby("day_name")["temperature"].agg(["min", "max"]).reset_index()
            day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            agg_7d['day_name'] = pd.Categorical(agg_7d['day_name'], categories=day_order, ordered=True)
            agg_7d = agg_7d.sort_values('day_name')

            fig7d = go.Figure()
            
            base_vals = agg_7d["min"].tolist()
            span_heights = (agg_7d["max"] - agg_7d["min"]).tolist()

            # Dynamic loop forces layout engine to draw vertical tracks matching structural gradient scale values
            for i, row in agg_7d.iterrows():
                def calculate_spatial_color(temp_target):
                    val_pct = (max(50.0, min(80.0, temp_target)) - 50.0) / (80.0 - 50.0)
                    r_val = int(0 + (255 - 0) * val_pct)
                    b_val = int(255 + (0 - 255) * val_pct)
                    return f"rgb({r_val}, 0, {b_val})"

                # Explicit vertical layout configurations using trace indexes
                fig7d.add_trace(go.Bar(
                    x=[row["day_name"]], 
                    y=[span_heights[i]],
                    base=[base_vals[i]],
                    marker=dict(
                        color=[row["max"]],
                        colorscale=[[0.0, calculate_spatial_color(row["min"])], [1.0, calculate_spatial_color(row["max"])]],
                        line=dict(width=0)
                    ),
                    text=f"{round(row['max'])}°<br><br>{round(row['min'])}°",
                    textposition="inside",
                    insidetextanchor="middle",
                    textfont=dict(color="white", size=12, weight="bold"),
                    width=0.55
                ))

            fig7d.update_layout(
                yaxis=dict(range=[45, 95], fixedrange=True, showgrid=False, zeroline=False, showticklabels=False),
                xaxis=dict(showgrid=False, tickfont=dict(size=13, color='#1f2328', weight='bold')),
                margin=dict(l=10, r=10, t=15, b=10),
                height=240,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False,
                barmode='stack' # Guarantees columns stretch vertically up from min baseline index markers
            )
            st.plotly_chart(fig7d, use_container_width=True, config={'displayModeBar': False})

        # --- CARD 4: HISTORICAL DATA PERSISTENCE RECORDS ---
        with st.container():
            st.markdown('<div class="card-headline-text">All-Time Records</div>', unsafe_allow_html=True)
            
            all_min = float(min_record_resp.data[0]["temperature"]) if min_record_resp.data else current_temp
            all_max = float(max_record_resp.data[0]["temperature"]) if max_record_resp.data else current_temp
            min_date = pd.to_datetime(min_record_resp.data[0]["created_at"]).tz_convert('US/Eastern').strftime("%B %d, %Y")
            max_date = pd.to_datetime(max_record_resp.data[0]["created_at"]).tz_convert('US/Eastern').strftime("%B %d, %Y")
            
            st.markdown(f"""
                <div style="display: flex; justify-content: space-around; text-align: center; padding: 5px 0 10px 0; font-family: sans-serif;">
                    <div style="flex: 1;">
                        <div style="font-size: 0.85rem; color: #57606a; font-weight: 700; letter-spacing: 0.03em;">RECORD MINIMUM</div>
                        <div style="font-size: 1.6rem; font-weight: 800; color: #0000ff; margin-top: 3px;">{all_min}°F</div>
                        <div style="font-size: 0.85rem; color: #57606a; margin-top: 2px;">{min_date}</div>
                    </div>
                    <div style="border-left: 1px solid #eef1f6; height: 55px; margin-top: 5px;"></div>
                    <div style="flex: 1;">
                        <div style="font-size: 0.85rem; color: #57606a; font-weight: 700; letter-spacing: 0.03em;">RECORD MAXIMUM</div>
                        <div style="font-size: 1.6rem; font-weight: 800; color: #ff0000; margin-top: 3px;">{all_max}°F</div>
                        <div style="font-size: 0.85rem; color: #57606a; margin-top: 2px;">{max_date}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Render pipeline trace variance encountered: {e}")
