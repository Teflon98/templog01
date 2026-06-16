import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import plotly.graph_objects as go
import datetime

# --- 1. SET VIEWPORT PROFILE & WINDOW CLEANER ---
st.set_page_config(page_title="Office Climate Tracker", layout="centered")

# Smooth interface structure configurations
st.markdown("""
    <style>
    /* Force responsive 1000px container canvas constraints */
    .block-container {
        max-width: 1000px !important;
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.2rem !important; /* Touch gutter margins */
        padding-right: 1.2rem !important;
    }

    /* Custom CSS Card Component Architecture */
    .custom-card-wrapper {
        border: 1px solid #e2e8f0 !important;
        background-color: #ffffff !important;
        border-radius: 16px !important;
        padding: 22px !important;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.015) !important;
        margin-bottom: 1.2rem !important;
    }

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
        margin-bottom: 14px;
        letter-spacing: 0.05em;
    }

    /* Dynamic Countdown Wick Grid Elements */
    .wick-outer-container {
        width: 100%;
        padding: 4px 0 12px 0;
        box-sizing: border-box;
    }

    .wick-track {
        width: 80%;
        margin: 0 auto;
        background-color: #f1f5f9;
        border-radius: 10px;
        height: 6px;
        overflow: hidden;
        position: relative;
    }

    .wick-fill {
        position: absolute;
        left: 0;
        top: 0;
        height: 100%;
        border-radius: 10px;
        transition: width 1s linear, background-color 1s ease;
    }

    footer { visibility: hidden; }
    header { visibility: hidden; }
    </style>
""", unsafe_allow_html=True)

# --- 2. CLOUD DATABASE INTERFACE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

@st.fragment(run_every=1)
def render_dashboard():
    try:
        # --- 3. DATA ACQUISITION PAYLOAD EXTRACTION ---
        recent_resp = supabase.table("sensor_data").select("*").order("created_at", desc=True).limit(288).execute()
        days7_resp  = supabase.table("sensor_data").select("*").order("created_at", desc=True).limit(2016).execute()
        min_record_resp = supabase.table("sensor_data").select("*").order("temperature", desc=False).limit(1).execute()
        max_record_resp = supabase.table("sensor_data").select("*").order("temperature", desc=True).limit(1).execute()

        if recent_resp.data and days7_resp.data:
            df24 = pd.DataFrame(recent_resp.data)
            df7d = pd.DataFrame(days7_resp.data)
            df24["local_time"] = pd.to_datetime(df24["created_at"]).dt.tz_convert('US/Eastern')
            df7d["local_time"] = pd.to_datetime(df7d["created_at"]).dt.tz_convert('US/Eastern')
            df24 = df24.sort_values(by="local_time")

            latest_record   = df24.iloc[-1]
            current_temp    = float(latest_record["temperature"])
            current_humidity = float(latest_record["humidity"])

            # --- TIMER WICK INTERVAL MATH ---
            last_reading_time = latest_record["local_time"]
            now_time = datetime.datetime.now(datetime.timezone.utc).astimezone(
                datetime.timezone(datetime.timedelta(hours=-4), 'EDT')
            )
            seconds_elapsed = (now_time - last_reading_time).total_seconds()
            seconds_left    = max(0.0, min(300.0, 300.0 - (seconds_elapsed % 300.0)))
            pct_left        = seconds_left / 300.0

            # Dynamic color interpolation: Pure Blue (100%) -> Pure Red (0%)
            wick_r = int(255 * (1.0 - pct_left))
            wick_b = int(255 * pct_left)
            wick_color = f"rgb({wick_r}, 0, {wick_b})"
            wick_pct_str = f"{pct_left * 100:.2f}%"

            timestamp_str = last_reading_time.strftime("%A, %B %d, %Y, %I:%M %p") \
                .replace("AM", "a.m.").replace("PM", "p.m.")

            # Real-time Trajectory Delta Arrows
            arrow = "→"
            if len(df24) >= 3:
                prev_avg = (float(df24.iloc[-2]["temperature"]) + float(df24.iloc[-3]["temperature"])) / 2.0
                if current_temp > prev_avg + 0.1:   arrow = "↑"
                elif current_temp < prev_avg - 0.1: arrow = "↓"

            # Core Title Thermal Color Mappings (50°F to 80°F constraints)
            pct = (max(50.0, min(80.0, current_temp)) - 50.0) / (80.0 - 50.0)
            solid_color = f"rgb({int(255 * pct)}, 0, {int(255 * (1 - pct))})"

            # --- CARD 1: LIVE ENVIRONMENT DISPLAY ---
            st.markdown(f"""
                <div class="custom-card-wrapper">
                    <div class="hero-temp-frame">
                        <div class="temp-value-display" style="color: {solid_color};">
                            {current_temp}°F<span style="font-size: 0.45em; color: #1e293b; margin-left: 8px; vertical-align: middle;">{arrow}</span>
                        </div>
                        <div style="font-size:1.3rem; font-weight:700; color:#1e293b; margin-top:4px;">Humidity {current_humidity}%</div>
                        
                        <div class="wick-outer-container">
                            <div class="wick-track">
                                <div class="wick-fill" style="width: {wick_pct_str}; background-color: {wick_color};"></div>
                            </div>
                        </div>
                        
                        <div style="text-align:center; font-size:0.95rem; color:#64748b; font-weight:400;">{timestamp_str}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # --- CARD 2: PAST 24 HOURS ENGINE ---
            st.markdown('<div class="custom-card-wrapper">', unsafe_allow_html=True)
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
            st.markdown('</div>', unsafe_allow_html=True)

            # --- CARD 3: PAST 7 DAYS CHRONO WINDOWS ---
            st.markdown('<div class="custom-card-wrapper">', unsafe_allow_html=True)
            st.markdown('<div class="card-headline-text">Past 7 Days</div>', unsafe_allow_html=True)

            # Establish absolute chronological array mapping windows
            today_et = now_time.date()
            ordered_dates = [today_et - datetime.timedelta(days=d) for d in range(6, -1, -1)]
            day_labels = ["Today" if d == today_et else d.strftime("%a") for d in ordered_dates]

            df7d["date_et"] = df7d["local_time"].dt.date
            agg_7d = df7d.groupby("date_et")["temperature"].agg(["min", "max"]).reset_index()
            
            # Map elements into an explicit timeline framework to block auto-rotation orientation flips
            agg_7d['date_et'] = pd.Categorical(agg_7d['date_et'], categories=ordered_dates, ordered=True)
            agg_7d = agg_7d.dropna().sort_values('date_et')

            fig7d = go.Figure()

            # Iterate through bars explicitly to generate perfect individual vertical columns
            for idx, row in agg_7d.iterrows():
                lbl = "Today" if row["date_et"] == today_et else row["date_et"].strftime("%a")
                t_min, t_max = row["min"], row["max"]

                def get_bar_hue(val):
                    p = (max(50.0, min(90.0, val)) - 50.0) / (90.0 - 50.0)
                    return f"rgb({int(255*p)}, 0, {int(255*(1-p))})"

                fig7d.add_trace(go.Bar(
                    x=[lbl],
                    y=[t_max - t_min],
                    base=[t_min],
                    orientation='v', # STRICTLY lock into vertical layout mode
                    marker=dict(
                        color=[t_max],
                        colorscale=[[0, get_bar_hue(t_min)], [1, get_bar_hue(t_max)]],
                        line=dict(width=0)
                    ),
                    text=f"<b>{round(t_max)}°</b><br><br><br><b>{round(t_min)}°</b>",
                    textposition="inside",
                    insidetextanchor="middle",
                    textfont=dict(color="white", size=12),
                    width=0.45,
                    showlegend=False
                ))

            fig7d.update_layout(
                yaxis=dict(range=[44, 96], fixedrange=True, showgrid=False, zeroline=False, showticklabels=False),
                xaxis=dict(showgrid=False, type='category', categoryorder='array', categoryarray=day_labels, tickfont=dict(size=12, color='#1e293b', weight='bold')),
                margin=dict(l=10, r=10, t=15, b=10),
                height=230,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                barmode='stack'
            )
            st.plotly_chart(fig7d, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)

            # --- CARD 4: COMPACT RECORDS PANEL (SANS ALL-TIME TITLE) ---
            st.markdown('<div class="custom-card-wrapper">', unsafe_allow_html=True)
            all_min  = float(min_record_resp.data[0]["temperature"]) if min_record_resp.data else current_temp
            all_max  = float(max_record_resp.data[0]["temperature"]) if max_record_resp.data else current_temp
            min_date = pd.to_datetime(min_record_resp.data[0]["created_at"]).tz_convert('US/Eastern').strftime("%b %d, %Y")
            max_date = pd.to_datetime(max_record_resp.data[0]["created_at"]).tz_convert('US/Eastern').strftime("%b %d, %Y")

            st.markdown(f"""
                <div style="display:flex; justify-content:space-around; text-align:center; padding:5px 0; font-family:sans-serif;">
                    <div style="flex:1;">
                        <div style="font-size:0.85rem; color:#64748b; font-weight:700; letter-spacing:0.03em;">RECORD MINIMUM</div>
                        <div style="font-size:1.6rem; font-weight:800; color:#0000ff; margin-top:3px;">{all_min}°F</div>
                        <div style="font-size:0.85rem; color:#64748b; margin-top:2px;">{min_date}</div>
                    </div>
                    <div style="border-left:1px solid #e2e8f0; height:55px; margin-top:5px;"></div>
                    <div style="flex:1;">
                        <div style="font-size:0.85rem; color:#64748b; font-weight:700; letter-spacing:0.03em;">RECORD MAXIMUM</div>
                        <div style="font-size:1.6rem; font-weight:800; color:#ff0000; margin-top:3px;">{all_max}°F</div>
                        <div style="font-size:0.85rem; color:#64748b; margin-top:2px;">{max_date}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Render pipeline trace error: {e}")

render_dashboard()
