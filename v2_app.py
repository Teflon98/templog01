import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import plotly.graph_objects as go
import datetime

# --- 1. SET VIEWPORT PROFILE ---
st.set_page_config(page_title="Office Climate Tracker", layout="centered")

# Global Layout Sanitation Engine
st.markdown("""
    <style>
    .block-container {
        max-width: 1000px !important;
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
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
        margin-bottom: 12px;
        letter-spacing: 0.05em;
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
        # --- 3. FETCH SENSOR ARRAYS ---
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

            # --- TIMER WICK MATH ---
            last_reading_time = latest_record["local_time"]
            now_time = datetime.datetime.now(datetime.timezone.utc).astimezone(
                datetime.timezone(datetime.timedelta(hours=-4), 'EDT')
            )
            seconds_elapsed = (now_time - last_reading_time).total_seconds()
            seconds_left    = max(0.0, min(300.0, 300.0 - (seconds_elapsed % 300.0)))
            pct_left        = seconds_left / 300.0

            # Blue (full) → Red (empty), receding left
            wick_r = int(255 * (1.0 - pct_left))
            wick_b = int(255 * pct_left)
            wick_color = f"rgb({wick_r}, 0, {wick_b})"

            timestamp_str = last_reading_time.strftime("%A, %B %d, %Y, %I:%M %p") \
                .replace("AM", "a.m.").replace("PM", "p.m.")

            # Trajectory arrow
            arrow = "→"
            if len(df24) >= 3:
                prev_avg = (float(df24.iloc[-2]["temperature"]) + float(df24.iloc[-3]["temperature"])) / 2.0
                if current_temp > prev_avg + 0.1:   arrow = "↑"
                elif current_temp < prev_avg - 0.1: arrow = "↓"

            # Hero temperature hue (50–80°F → blue→red)
            pct = (max(50.0, min(80.0, current_temp)) - 50.0) / (80.0 - 50.0)
            solid_color = f"rgb({int(255 * pct)}, 0, {int(255 * (1 - pct))})"

            # --- CARD 1: HERO ---
            with st.container(border=True):
                st.markdown(f"""
                    <div class="hero-temp-frame">
                        <div class="temp-value-display" style="color: {solid_color};">
                            {current_temp}°F<span style="font-size: 0.45em; color: #1e293b;
                            margin-left: 8px; vertical-align: middle;">{arrow}</span>
                        </div>
                        <div style="font-size:1.3rem; font-weight:700; color:#1e293b;
                            margin-top:4px;">Humidity {current_humidity}%</div>

                        <!-- Countdown wick -->
                        <div style="width:80%; margin:14px auto 6px auto;
                             background-color:#f1f5f9; border-radius:10px;
                             height:6px; overflow:hidden;">
                            <div style="width:{pct_left*100:.2f}%; height:100%;
                                 border-radius:10px;
                                 background: linear-gradient(to left, rgb({wick_r},0,{wick_b}), #0000ff);
                                 float:right;">
                            </div>
                        </div>

                        <div style="font-size:0.95rem; color:#64748b;
                            font-weight:400; margin-top:6px;">{timestamp_str}</div>
                    </div>
                """, unsafe_allow_html=True)

            # --- CARD 2: PAST 24 HOURS ---
            with st.container(border=True):
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
                    yaxis=dict(range=[50, 90], fixedrange=True, gridcolor='#f1f5f9',
                               zeroline=False, tickfont=dict(color='#64748b', size=11)),
                    xaxis=dict(tickformat="%I%p", gridcolor='#f1f5f9', showgrid=True,
                               tickfont=dict(color='#64748b', size=11), nticks=6),
                    margin=dict(l=20, r=10, t=5, b=10),
                    height=220,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False
                )
                st.plotly_chart(fig24, use_container_width=True, config={'displayModeBar': False})

            # --- CARD 3: PAST 7 DAYS ---
            with st.container(border=True):
                st.markdown('<div class="card-headline-text">Past 7 Days</div>', unsafe_allow_html=True)

                df7d["day_name"] = df7d["local_time"].dt.strftime("%a")
                agg_7d = df7d.groupby("day_name")["temperature"].agg(["min", "max"]).reset_index()
                day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                agg_7d['day_name'] = pd.Categorical(agg_7d['day_name'], categories=day_order, ordered=True)
                agg_7d = agg_7d.sort_values('day_name')

                RANGE_MIN, RANGE_MAX = 50.0, 90.0

                def temp_to_color(t):
                    """Map temperature → absolute blue-to-red within 50–90°F."""
                    p = (max(RANGE_MIN, min(RANGE_MAX, float(t))) - RANGE_MIN) / (RANGE_MAX - RANGE_MIN)
                    r = int(255 * p)
                    b = int(255 * (1.0 - p))
                    return f"rgb({r},0,{b})"

                # Build vertical gradient bars using SVG shapes via Plotly layout shapes.
                # Each bar = stack of thin horizontal slices, each colored by absolute temp.
                SLICES = 60  # resolution of gradient per bar
                fig7d = go.Figure()

                # Invisible scatter just to set axes and force sizing
                fig7d.add_trace(go.Scatter(x=day_order, y=[None]*7, mode='markers',
                                           marker=dict(opacity=0)))

                shapes = []
                annotations = []

                for i, row in agg_7d.iterrows():
                    day   = row["day_name"]
                    t_min = float(row["min"])
                    t_max = float(row["max"])
                    x_idx = day_order.index(day)

                    # Bar occupies ±0.22 category units on either side of center
                    x0 = x_idx - 0.22
                    x1 = x_idx + 0.22

                    # Slice from t_min to t_max
                    step = (t_max - t_min) / SLICES if t_max != t_min else 1.0
                    for s in range(SLICES):
                        frac_lo = s / SLICES
                        frac_hi = (s + 1) / SLICES
                        y0 = t_min + frac_lo  * (t_max - t_min)
                        y1 = t_min + frac_hi  * (t_max - t_min)
                        mid_t = (y0 + y1) / 2.0
                        color = temp_to_color(mid_t)
                        shapes.append(dict(
                            type="rect",
                            xref="x", yref="y",
                            x0=x0, x1=x1,
                            y0=y0, y1=y1,
                            fillcolor=color,
                            line=dict(width=0),
                            layer="below"
                        ))

                    # Labels: max on top, min on bottom (white text)
                    annotations.append(dict(
                        x=x_idx, y=t_max,
                        text=f"<b>{round(t_max)}°</b>",
                        showarrow=False,
                        yanchor="bottom",
                        font=dict(color="white", size=11),
                        bgcolor="rgba(0,0,0,0)"
                    ))
                    annotations.append(dict(
                        x=x_idx, y=t_min,
                        text=f"<b>{round(t_min)}°</b>",
                        showarrow=False,
                        yanchor="top",
                        font=dict(color="white", size=11),
                        bgcolor="rgba(0,0,0,0)"
                    ))

                fig7d.update_layout(
                    shapes=shapes,
                    annotations=annotations,
                    yaxis=dict(range=[RANGE_MIN, RANGE_MAX], fixedrange=True,
                               showgrid=False, zeroline=False, showticklabels=False),
                    xaxis=dict(
                        tickmode="array",
                        tickvals=list(range(len(day_order))),
                        ticktext=day_order,
                        showgrid=False,
                        tickfont=dict(size=13, color='#1e293b', weight='bold'),
                        range=[-0.5, len(day_order) - 0.5]
                    ),
                    margin=dict(l=10, r=10, t=15, b=10),
                    height=220,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False
                )
                st.plotly_chart(fig7d, use_container_width=True, config={'displayModeBar': False})

            # --- CARD 4: RECORDS ---
            with st.container(border=True):
                all_min  = float(min_record_resp.data[0]["temperature"]) if min_record_resp.data else current_temp
                all_max  = float(max_record_resp.data[0]["temperature"]) if max_record_resp.data else current_temp
                min_date = pd.to_datetime(min_record_resp.data[0]["created_at"]).tz_convert('US/Eastern').strftime("%b %d, %Y")
                max_date = pd.to_datetime(max_record_resp.data[0]["created_at"]).tz_convert('US/Eastern').strftime("%b %d, %Y")

                st.markdown(f"""
                    <div style="display:flex; justify-content:space-around; text-align:center;
                         padding:5px 0; font-family:sans-serif;">
                        <div style="flex:1;">
                            <div style="font-size:0.85rem; color:#64748b; font-weight:700;
                                letter-spacing:0.03em;">RECORD MINIMUM</div>
                            <div style="font-size:1.6rem; font-weight:800; color:#0000ff;
                                margin-top:3px;">{all_min}°F</div>
                            <div style="font-size:0.85rem; color:#64748b; margin-top:2px;">{min_date}</div>
                        </div>
                        <div style="border-left:1px solid #e2e8f0; height:55px; margin-top:5px;"></div>
                        <div style="flex:1;">
                            <div style="font-size:0.85rem; color:#64748b; font-weight:700;
                                letter-spacing:0.03em;">RECORD MAXIMUM</div>
                            <div style="font-size:1.6rem; font-weight:800; color:#ff0000;
                                margin-top:3px;">{all_max}°F</div>
                            <div style="font-size:0.85rem; color:#64748b; margin-top:2px;">{max_date}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Render error: {e}")

render_dashboard()
