import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import plotly.graph_objects as go
import datetime

# --- 1. CONFIGURATION & DEVICE VIEWPORT WRAPPER ---
st.set_page_config(page_title="Office Climate v2", layout="wide")
st.fragment(run_every=1) # High-frequency refresh to keep the countdown wick smoothly ticking down

# Deep CSS injection to explicitly lock card borders, structure layout nodes, and format the countdown wick
st.markdown("""
    <style>
    /* Desktop vs Fluid Mobile viewport alignment wrapper */
    .block-container {
        max-width: 1000px !important;
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.2rem !important; /* Side gutter room for touch-pull refresh protection */
        padding-right: 1.2rem !important;
        margin: 0 auto !important;
    }
    
    /* Dual-targeted card grouping properties to force visible borders */
    div[data-testid="stVerticalBlockBorderWrapper"], 
    div[data-testid="stVerticalBlock"] > div:has(div[data-testid="stContainer"]) {
        border: 1px solid #e2e8f0 !important;
        background-color: #ffffff !important;
        border-radius: 16px !important;
        padding: 20px !important;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.02) !important;
        margin-bottom: 1.2rem !important;
    }
    
    /* Clean out conflicting internal container layout paddings */
    div[data-testid="stContainer"] {
        border: none !important;
        padding: 0 !important;
        box-shadow: none !important;
        background: transparent !important;
    }
    
    /* Lower line-height to completely protect the top metric from top-clipping */
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
    
    /* Dynamic Countdown Wick Containers */
    .wick-wrapper {
        width: 80%;
        margin: 10px auto 12px auto;
        background-color: #f1f5f9;
        border-radius: 4px;
        overflow: hidden;
        height: 6px; /* Approximately 1/3 height of typical text line tracking indices */
    }
    
    .wick-bar {
        height: 100%;
        border-radius: 4px;
        transition: width 1s linear, background 1s ease;
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
        
        # Datetime calculations for countdown tracking
        last_reading_time = latest_record["local_time"]
        now_time = datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=-5), 'EST'))
        
        # Calculate seconds elapsed in current 5-minute interval chunk (300 seconds total)
        seconds_elapsed = (now_time - last_reading_time).total_seconds()
        seconds_left = max(0, min(300, 300 - (seconds_elapsed % 300)))
        pct_left = (seconds_left / 300.0)
        
        # Color shifting math: Shifts from pure Blue to Deep Red as time ticks down and recedes
        # High percentage left = Blue dominant; Low percentage left = Red dominant
        wick_r = int(255 * (1.0 - pct_left))
        wick_g = 0
        wick_b = int(255 * pct_left)
        wick_color = f"rgb({wick_r}, {wick_g}, {wick_b})"
        
        timestamp_str = last_reading_time.strftime("%A, %B %d, %Y, %I:%M %p").replace("AM", "a.m.").replace("PM", "p.m.")

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
                    
                    <div class="wick-wrapper">
                        <div class="wick-bar" style="width: {pct_left * 100}%; background: {wick_color};"></div>
                    </div>
                    
                    <div style="font-size: 0.95rem; color: #64748b; font-weight: 400;">{timestamp_str}</div>
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
                fillgradient=dict(
                    type="vertical",
                    colorscale=[
                        (0.0, "rgba(0, 0, 255, 0.0)"),
                        (0.4, "rgba(0, 0, 255, 0.2)"),
                        (0.7, "rgba(128, 0, 128, 0.25)"),
                        (1.0, "rgba(255, 0, 0, 0.4)")
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

        # --- CARD 3: PAST 7 DAYS (EXPLICIT VERTICAL CHRONOLOGICAL MARKERS) ---
        with st.container():
            st.markdown('<div class="card-headline-text">Past 7 Days</div>', unsafe_allow_html=True)
            
            df7d["day_name"] = df7d["local_time"].dt.strftime("%a")
            agg_7d = df7d.groupby("day_name")["temperature"].agg(["min", "max"]).reset_index()
            day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            agg_7d['day_name'] = pd.Categorical(agg_7d['day_name'], categories=day_order, ordered=True)
            agg_7d = agg_7d.sort_values('day_name')

            fig7d = go.Figure()
            
            # Forcing layout engine to parse vertical tracks explicitly by passing orientation keys
            fig7d.add_trace(go.Bar(
                x=agg_7d["day_name"].astype(str),
                y=agg_7d["max"] - agg_7d["min"],
                base=agg_7d["min"],
                orientation='v', # STRICTLY forces vertical mode execution
                marker=dict(
                    color=agg_7d["max"],
                    colorscale=[
                        [0.0, "rgb(0, 0, 255)"],
                        [0.5, "rgb(128, 0, 128)"],
                        [1.0, "rgb(255, 0, 0)"]
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

        # --- CARD 4: RECORDS CELLS ONLY (COMPACT DESIGN SANS HEADING) ---
        with st.container():
            all_min = float(min_record_resp.data[0]["temperature"]) if min_record_resp.data else current_temp
            all_max = float(max_record_resp.data[0]["temperature"]) if max_record_resp.data else current_temp
            min_date = pd.to_datetime(min_record_resp.data[0]["created_at"]).tz_convert('US/Eastern').strftime("%b %d, %Y")
            max_date = pd.to_datetime(max_record_resp.data[0]["created_at"]).tz_convert('US/Eastern').strftime("%b %d, %Y")
            
            st.markdown(f"""
                <div style="display: flex; justify-content: space-around; text-align: center; padding: 5px 0; font-family: sans-serif;">
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
