import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import plotly.graph_objects as go
import datetime

# --- 1. CONFIGURATION & VIEWPORT ENGINE ---
st.set_page_config(page_title="Office Climate v2", layout="centered")
st.fragment(run_every=1) # High-frequency tick for smooth wick animation

# Bulletproof structural CSS for crisp card wrappers and mobile touch padding
st.markdown("""
    <style>
    /* Centers on desktop at 1000px, expands dynamically on the Pixel 9 Pro */
    .block-container {
        max-width: 1000px !important;
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.2rem !important; /* Doubled side gutters for touch-pull refresh safety */
        padding-right: 1.2rem !important;
    }
    
    /* Strict target for Streamlit container nodes to guarantee matching card borders */
    div[data-testid="stContentBlock"] {
        border: 1px solid #e2e8f0 !important;
        background-color: #ffffff !important;
        border-radius: 16px !important;
        padding: 22px !important;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.015) !important;
        margin-bottom: 1.2rem !important;
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
        margin: 12px auto 12px auto;
        background-color: #f1f5f9;
        border-radius: 10px;
        overflow: hidden;
        height: 6px; /* Exactly 1/3 height of data text line indices */
    }
    
    .wick-bar {
        height: 100%;
        border-radius: 10px;
    }
    
    /* Interface sanitation */
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
        df24 = pd.DataFrame(recent_resp.data)
        df7d = pd.DataFrame(days7_resp.data)
        df24["local_time"] = pd.to_datetime(df24["created_at"]).dt.tz_convert('US/Eastern')
        df7d["local_time"] = pd.to_datetime(df7d["created_at"]).dt.tz_convert('US/Eastern')
        df24 = df24.sort_values(by="local_time")
        
        latest_record = df24.iloc[-1]
        current_temp = float(latest_record["temperature"])
        current_humidity = float(latest_record["humidity"])
        
        # Datetime math for the countdown bar
        last_reading_time = latest_record["local_time"]
        now_time = datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=-5), 'EST'))
        
        # Check remaining seconds inside the 5-minute interval chunk (300 seconds total)
        seconds_elapsed = (now_time - last_reading_time).total_seconds()
        seconds_left = max(0, min(300, 300 - (seconds_elapsed % 300)))
        pct_left = (seconds_left / 300.0)
        
        # Smoothly interpolating wick color from Blue (fresh reading) to Red (imminent reading)
        wick_r = int(255 * (1.0 - pct_left))
        wick_g = 0
        wick_b = int(255 * pct_left)
        wick_color = f"rgb({wick_r}, {wick_g}, {wick_b})"
        
        timestamp_str = last_reading_time.strftime("%A, %B %d, %Y, %I:%M %p").replace("AM", "a.m.").replace("PM", "p.m.")

        # Delta arrow calculations
        arrow = "→"
        if len(df24) >= 3:
            prev_avg = (float(df24.iloc[-2]["temperature"]) + float(df24.iloc[-3]["temperature"])) / 2.0
            if current_temp > prev_avg + 0.1: arrow = "↑"
            elif current_temp < prev_avg - 0.1: arrow = "↓"

        # Global thermal spectrum map for main text color
        pct = (max(50.0, min(80.0, current_temp)) - 50.0) / (80.0 - 50.0)
        solid_color = f"rgb({int(255 * pct)}, 0, {int(255 * (1 - pct))})"

        # --- CARD 1: CURRENT ENVIRONMENT HERO DISPLAY ---
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

        # --- CARD 2: PAST 24 HOURS ---
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
                        (0.4, "rgba(0, 0, 255, 0.15)"),
                        (0.7, "rgba(128, 0, 128, 0.2)"),
                        (1.0, "rgba(255, 0, 0, 0.35)")
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

        # --- CARD 3: PAST 7 DAYS (LOCKED VERTICAL RANGE WINDOWS) ---
        with st.container():
            st.markdown('<div class="card-headline-text">Past 7 Days</div>', unsafe_allow_html=True)
            
            df7d["day_name"] = df7d["local_time"].dt.strftime("%a")
            agg_7d = df7d.groupby("day_name")["temperature"].agg(["min", "max"]).reset_index()
            day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            agg_7d['day_name'] = pd.Categorical(agg_7d['day_name'], categories=day_order, ordered=True)
            agg_7d = agg_7d.sort_values('day_name')

            fig7d = go.Figure()
            
            # Using absolute coordinates for X forces Plotly to render vertically
            fig7d.add_trace(go.Bar(
                x=[1, 2, 3, 4, 5, 6, 7],
                y=agg_7d["max"] - agg_7d["min"],
                base=agg_7d["min"],
                orientation='v', 
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
                xaxis=dict(
                    showgrid=False,
                    tickvals=[1, 2, 3, 4, 5, 6, 7],
                    ticktext=day_order, # Beautifully swap the math keys back out for weekdays
                    tickfont=dict(size=13, color='#1e293b', weight='bold')
                ),
                margin=dict(l=10, r=10, t=15, b=10),
                height=240,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False
            )
            st.plotly_chart(fig7d, use_container_width=True, config={'displayModeBar': False})

        # --- CARD 4: COMPACT RECORDS PANEL ---
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
