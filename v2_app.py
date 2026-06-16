import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import plotly.graph_objects as go

# --- 1. CONFIGURATION & DEVICE VIEWPORT WRAPPER ---
st.set_page_config(page_title="Office Climate v2", layout="wide")
st.fragment(run_every=300)

# Bulletproof global CSS injection for borders, layout spacing, and typography scaling
st.markdown("""
    <style>
    /* Force centered desktop alignment at 1000px, while keeping mobile fluid */
    .block-container {
        max-width: 1000px !important;
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.2rem !important; /* Doubled padding for side-refresh safety */
        padding-right: 1.2rem !important;
        margin: 0 auto !important;
    }
    
    /* Target explicit internal Streamlit layout nodes to force card borders */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid #e2e8f0 !important;
        background-color: #ffffff !important;
        border-radius: 16px !important;
        padding: 22px !important;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.02) !important;
        margin-bottom: 1.2rem !important;
    }
    
    /* Lower line-height to completely protect the top metric from clipping */
    .hero-temp-frame {
        text-align: center;
        padding: 5px 0;
    }
    
    .temp-value-display {
        font-size: clamp(3.8rem, 15vw, 5.8rem);
        font-weight: 800;
        line-height: 1.05;
        white-space: nowrap;
        letter-spacing: -2px;
    }
    
    .card-headline-text {
        font-size: 1.1rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #1e293b;
        text-align: center;
        margin-bottom: 18px;
        letter-spacing: 0.05em;
    }
    
    /* Clean interface sanitation */
    footer { visibility: hidden; }
    header { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CLOUD DATABASE INTERFACE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

try:
    # --- 3. EXECUTE DATA PAYLOAD EXTRACTION ---
    recent_resp = supabase.table("sensor_data").select("*").order("created_at", desc=True).limit(288).execute()
    days7_resp = supabase.table("sensor_data").select("*").order("created_at", desc=True).limit(2016).execute()
    min_record_resp = supabase.table("sensor_data").select("*").order("temperature", desc=False).limit(1).execute()
    max_record_resp = supabase.table("sensor_data").select("*").order("temperature", desc=True).limit(1).execute()

    if recent_resp.data and days7_resp.data:
        # Construct and parse localized execution dataframes
        df24 = pd.DataFrame(recent_resp.data)
        df7d = pd.DataFrame(days7_resp.data)
        df24["local_time"] = pd.to_datetime(df24["created_at"]).dt.tz_convert('US/Eastern')
        df7d["local_time"] = pd.to_datetime(df7d["created_at"]).dt.tz_convert('US/Eastern')
        df24 = df24.sort_values(by="local_time")
        
        latest_record = df24.iloc[-1]
        current_temp = float(latest_record["temperature"])
        current_humidity = float(latest_record["humidity"])
        timestamp_str = latest_record["local_time"].strftime("%A, %B %d, %Y, %I:%M %p").replace("AM", "a.m.").replace("PM", "p.m.")

        # Real-time delta trajectory arrow logic
        arrow = "→"
        if len(df24) >= 3:
            prev_avg = (float(df24.iloc[-2]["temperature"]) + float(df24.iloc[-3]["temperature"])) / 2.0
            if current_temp > prev_avg + 0.1: arrow = "↑"
            elif current_temp < prev_avg - 0.1: arrow = "↓"

        # Interpolate a solid text hue mapped to the 50°F - 80°F environmental constraints
        pct = (max(50.0, min(80.0, current_temp)) - 50.0) / (80.0 - 50.0)
        solid_color = f"rgb({int(255 * pct)}, 0, {int(255 * (1 - pct))})"

        # --- CARD 1: HERO DISPLAY ---
        with st.container():
            st.markdown(f"""
                <div class="hero-temp-frame">
                    <div class="temp-value-display" style="color: {solid_color};">
                        {current_temp}°F<span style="font-size: 0.45em; color: #1e293b; margin-left: 8px; vertical-align: middle;">{arrow}</span>
                    </div>
                    <div style="font-size: 1.3rem; font-weight: 700; color: #1e293b; margin-top: 4px;">Humidity {current_humidity}%</div>
                    <div style="font-size: 0.95rem; color: #64748b; margin-top: 6px; font-weight: 400;">{timestamp_str}</div>
                </div>
            """, unsafe_allow_html=True)

        # --- CARD 2: PAST 24 HOURS (WITH NATIVE PLOTLY GRADIENT) ---
        with st.container():
            st.markdown('<div class="card-headline-text">Past 24 Hours</div>', unsafe_allow_html=True)
            
            fig24 = go.Figure()
            fig24.add_trace(go.Scatter(
                x=df24["local_time"], 
                y=df24["temperature"],
                mode='lines',
                line=dict(width=3.5, color='#1e293b', shape='spline'),
                fill='tozeroy',
                # True linear rendering via modern Plotly layout engine properties
                fillgradient=dict(
                    type="vertical",
                    colorscale=[
                        (0.0, "rgba(0, 0, 255, 0.0)"),    # Crisp cold baseline anchor
                        (0.4, "rgba(0, 0, 255, 0.2)"),    # Blue
                        (0.7, "rgba(128, 0, 128, 0.25)"), # Purple transitional vector
                        (1.0, "rgba(255, 0, 0, 0.4)")     # Deep warm upper thermal ceiling
                    ]
                )
            ))
            fig24.update_layout(
                yaxis=dict(range=[50, 90], fixedrange=True, gridcolor='#f1f5f9', zeroline=False, tickfont=dict(color='#64748b', size=11)),
                xaxis=dict(tickformat="%I%p", gridcolor='#f1f5f9', showgrid=True, tickfont=dict(color='#64748b', size=11), nticks=6),
                margin=dict(l=20, r=10, t=5, b=10),
                height=220,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False
            )
            st.plotly_chart(fig24, use_container_width=True, config={'displayModeBar': False})

        # --- CARD 3: PAST 7 DAYS (STRICT VERTICAL CHRONOLOGICAL RANGE WINDOWS) ---
        with st.container():
            st.markdown('<div class="card-headline-text">Past 7 Days</div>', unsafe_allow_html=True)
            
            df7d["day_name"] = df7d["local_time"].dt.strftime("%a")
            agg_7d = df7d.groupby("day_name")["temperature"].agg(["min", "max"]).reset_index()
            day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            agg_7d['day_name'] = pd.Categorical(agg_7d['day_name'], categories=day_order, ordered=True)
            agg_7d = agg_7d.sort_values('day_name')

            # Build a singular trace to completely prevent auto-rotation orientation flips
            fig7d = go.Figure()
            fig7d.add_trace(go.Bar(
                x=agg_7d["day_name"].astype(str),
                y=agg_7d["max"] - agg_7d["min"],
                base=agg_7d["min"],
                marker=dict(
                    color=agg_7d["max"],
                    # Maps a global spatial thermal scale gradient directly through the column geometries
                    colorscale=[
                        [0.0, "rgb(0, 0, 255)"],    # Cold floor
                        [0.5, "rgb(128, 0, 128)"],  # Transitional mid
                        [1.0, "rgb(255, 0, 0)"]     # Warm high ceiling
                    ],
                    line=dict(width=0)
                ),
                text=[f"{round(mx)}°<br><br>{round(mn)}°" for mx, mn in zip(agg_7d["max"], agg_7d["min"])],
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(color="white", size=12, weight="bold"),
                width=0.55
            ))

            fig7d.update_layout(
                yaxis=dict(range=[45, 95], fixedrange=True, showgrid=False, zeroline=False, showticklabels=False),
                xaxis=dict(showgrid=False, type='category', tickfont=dict(size=13, color='#1e293b', weight='bold')),
                margin=dict(l=10, r=10, t=15, b=10),
                height=240,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False
            )
            st.plotly_chart(fig7d, use_container_width=True, config={'displayModeBar': False})

        # --- CARD 4: ALL-TIME RECORDS ---
        with st.container():
            st.markdown('<div class="card-headline-text">All-Time Records</div>', unsafe_allow_html=True)
            
            all_min = float(min_record_resp.data[0]["temperature"]) if min_record_resp.data else current_temp
            all_max = float(max_record_resp.data[0]["temperature"]) if max_record_resp.data else current_temp
            min_date = pd.to_datetime(min_record_resp.data[0]["created_at"]).tz_convert('US/Eastern').strftime("%b %d, %Y")
            max_date = pd.to_datetime(max_record_resp.data[0]["created_at"]).tz_convert('US/Eastern').strftime("%b %d, %Y")
            
            st.markdown(f"""
                <div style="display: flex; justify-content: space-around; text-align: center; padding: 5px 0 10px 0; font-family: sans-serif;">
                    <div style="flex: 1;">
                        <div style="font-size: 0.85rem; color: #64748b; font-weight: 700; letter-spacing: 0.03em;">RECORD MINIMUM</div>
                        <div style="font-size: 1.6rem; font-weight: 800; color: #0000ff; margin-top: 3px;">{all_min}°F</div>
                        <div style="font-size: 0.85rem; color: #64748b; margin-top: 2px;">{min_date}</div>
                    </div>
                    <div style="border-left: 1px solid #e2e8f0; height: 55px; margin-top: 5px;"></div>
                    <div style="flex: 1;">
                        <div style="font-size: 0.85rem; color: #64748b; font-weight: 700; letter-spacing: 0.03em;">RECORD MAXIMUM</div>
                        <div style="font-size: 1.6rem; font-weight: 800; color: #ff0000; margin-top: 3px;">{all_max}°F</div>
                        <div style="font-size: 0.85rem; color: #64748b; margin-top: 2px;">{max_date}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Render pipeline variance logged: {e}")
