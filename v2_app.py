import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
from supabase import create_client
import plotly.graph_objects as go
import datetime

# --- 1. SET VIEWPORT PROFILE ---
st.set_page_config(page_title="Office Climate Tracker", layout="centered")

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

@st.fragment(run_every=5)
def render_dashboard():
    try:
        # --- 3. FETCH SENSOR ARRAYS ---
        recent_resp     = supabase.table("sensor_data").select("*").order("created_at", desc=True).limit(288).execute()
        days7_resp      = supabase.table("sensor_data").select("*").order("created_at", desc=True).limit(2016).execute()
        min_record_resp = supabase.table("sensor_data").select("*").order("temperature", desc=False).limit(1).execute()
        max_record_resp = supabase.table("sensor_data").select("*").order("temperature", desc=True).limit(1).execute()

        if recent_resp.data and days7_resp.data:
            df24 = pd.DataFrame(recent_resp.data)
            df7d = pd.DataFrame(days7_resp.data)
            df24["local_time"] = pd.to_datetime(df24["created_at"]).dt.tz_convert('US/Eastern')
            df7d["local_time"] = pd.to_datetime(df7d["created_at"]).dt.tz_convert('US/Eastern')
            df24 = df24.sort_values(by="local_time")

            latest_record    = df24.iloc[-1]
            current_temp     = float(latest_record["temperature"])
            current_humidity = float(latest_record["humidity"])

            # --- TIME CALCULATIONS ---
            last_reading_time = latest_record["local_time"]
            now_time = datetime.datetime.now(datetime.timezone.utc).astimezone(
                datetime.timezone(datetime.timedelta(hours=-4), 'EDT')
            )
            seconds_elapsed = (now_time - last_reading_time).total_seconds()
            seconds_left    = max(0.0, min(300.0, 300.0 - (seconds_elapsed % 300.0)))
            pct_left        = seconds_left / 300.0

            # Formatted strings
            # m-dd-yy: no leading zero on month, two-digit year
            _m  = last_reading_time.strftime("%-m")   # Linux; no leading zero
            _dy = last_reading_time.strftime("%d")
            _yy = last_reading_time.strftime("%y")
            _t  = last_reading_time.strftime("%I:%M:%S %p").lstrip("0") \
                      .replace("AM", "a.m.").replace("PM", "p.m.")
            timestamp_str = f"{_m}-{_dy}-{_yy} {_t}"
            elapsed_total  = int(seconds_elapsed)
            elapsed_h      = elapsed_total // 3600
            elapsed_m      = (elapsed_total % 3600) // 60
            elapsed_s      = elapsed_total % 60
            elapsed_str    = f"{elapsed_h:02d}:{elapsed_m:02d}:{elapsed_s:02d}"

            # Trajectory arrow
            arrow = "→"
            if len(df24) >= 3:
                prev_avg = (float(df24.iloc[-2]["temperature"]) + float(df24.iloc[-3]["temperature"])) / 2.0
                if current_temp > prev_avg + 0.1:   arrow = "↑"
                elif current_temp < prev_avg - 0.1: arrow = "↓"

            # Hero temperature hue: 65°F→blue, 76°F→red
            pct = (max(65.0, min(76.0, current_temp)) - 65.0) / (76.0 - 65.0)
            solid_color = f"rgb({int(255 * pct)}, 0, {int(255 * (1 - pct))})"

            # ================================================================
            # CARD 1: HERO
            # ================================================================
            with st.container(border=True):
                # Temperature + humidity
                st.markdown(f"""
                    <div class="hero-temp-frame">
                        <div class="temp-value-display" style="color:{solid_color};">
                            {current_temp}°F<span style="font-size:0.45em; color:#1e293b;
                            margin-left:8px; vertical-align:middle;">{arrow}</span>
                        </div>
                        <div style="font-size:1.3rem; font-weight:700; color:#1e293b;
                            margin-top:4px;">Humidity {current_humidity}%</div>
                    </div>
                """, unsafe_allow_html=True)

                # --- WICK (COMMENTED OUT — re-enable by removing the block comment markers) ---
                # components.html(f"""
                #     <div style="width:100%; padding:10px 0 4px 0; box-sizing:border-box;">
                #         <div style="width:80%; margin:0 auto; border-radius:10px; height:6px;
                #              overflow:hidden; position:relative;
                #              background:linear-gradient(to right, #0000ff, #ff0000);">
                #             <div id="wick" style="position:absolute; left:0; top:0; width:0;
                #                  height:100%; background:#f1f5f9;"></div>
                #         </div>
                #     </div>
                #     <script>
                #     (function() {{
                #         const wick = document.getElementById('wick');
                #         const secondsLeft = {seconds_left:.2f};
                #         const pctLeft = {pct_left:.6f};
                #         const startMaskPct = (1 - pctLeft) * 100;
                #         wick.style.width = startMaskPct + '%';
                #         requestAnimationFrame(function() {{
                #             requestAnimationFrame(function() {{
                #                 wick.style.transition = 'width ' + secondsLeft + 's linear';
                #                 wick.style.width = '100%';
                #             }});
                #         }});
                #     }})();
                #     </script>
                # """, height=26, scrolling=False)

                # --- THREE-CELL INFO ROW with live clock via JS ---
                # Last Log Entry (static from Python), Current Time (JS setInterval),
                # Time Elapsed (JS setInterval from seconds_elapsed at render time).
                # All three cells use the same column structure for alignment.
                components.html(f"""
                    <style>
                        .info-row {{
                            display: flex;
                            justify-content: space-between;
                            align-items: flex-start;
                            padding: 10px 4px 6px 4px;
                            font-family: sans-serif;
                            gap: 8px;
                        }}
                        .info-cell {{
                            flex: 1;
                            display: flex;
                            flex-direction: column;
                        }}
                        .info-cell.center {{ align-items: center; text-align: center; }}
                        .info-cell.right  {{ align-items: flex-end;  text-align: right; }}
                        .info-label {{
                            font-size: 0.72rem;
                            font-weight: 700;
                            color: #64748b;
                            text-transform: uppercase;
                            letter-spacing: 0.04em;
                            margin-bottom: 3px;
                        }}
                        .info-value {{
                            font-size: 0.92rem;
                            font-weight: 600;
                            color: #1e293b;
                        }}
                    </style>
                    <div class="info-row">
                        <div class="info-cell">
                            <div class="info-label">Last Log Entry</div>
                            <div class="info-value">{timestamp_str}</div>
                        </div>
                        <div class="info-cell center">
                            <div class="info-label">Current Time</div>
                            <div class="info-value" id="clock">--:--:--</div>
                        </div>
                        <div class="info-cell right">
                            <div class="info-label">Time Elapsed</div>
                            <div class="info-value" id="elapsed">--:--:--</div>
                        </div>
                    </div>
                    <script>
                    (function() {{
                        // Elapsed starts from seconds_elapsed at render time and counts up
                        let elapsedSec = Math.round({seconds_elapsed:.1f});

                        function pad(n) {{ return String(n).padStart(2, '0'); }}

                        function formatElapsed(s) {{
                            const h = Math.floor(s / 3600);
                            const m = Math.floor((s % 3600) / 60);
                            const sec = s % 60;
                            return h + ':' + pad(m) + ':' + pad(sec);
                        }}

                        function formatTime(d) {{
                            let h = d.getHours();
                            const min = d.getMinutes();
                            const sec = d.getSeconds();
                            const ampm = h >= 12 ? 'p.m.' : 'a.m.';
                            h = h % 12 || 12;
                            return h + ':' + pad(min) + ':' + pad(sec) + ' ' + ampm;
                        }}

                        function tick() {{
                            document.getElementById('clock').textContent = formatTime(new Date());
                            document.getElementById('elapsed').textContent = formatElapsed(elapsedSec);
                            elapsedSec++;
                        }}

                        tick();
                        setInterval(tick, 1000);
                    }})();
                    </script>
                """, height=70, scrolling=False)

            # ================================================================
            # CARD 2: PAST 24 HOURS
            # ================================================================
            with st.container(border=True):
                st.markdown('<div class="card-headline-text">Past 24 Hours</div>', unsafe_allow_html=True)

                # Day/night palette from uploaded image (left=day, right=night):
                # #a8ccd7 light blue (midday), #7fa8b8, #6b8f9e, #4d6b7a, #2d4a57 (midnight)
                # The x-axis runs from oldest→newest (could start at any hour).
                # We overlay a horizontal gradient band below the plot area using a shape
                # spanning the full x-domain at y just below the plot, keyed to time-of-day.
                # Implemented as an SVG-based Plotly shape with a custom colorscale image.

                fig24 = go.Figure()

                # --- Day/night band ---
                # Strategy: add a thin filled scatter at y=60 (bottom of visible range)
                # using a time-mapped color. Better: use layout images or shapes with
                # a horizontal gradient per segment.
                # Most reliable in Plotly: add a series of thin rect shapes across the
                # x-axis at fixed y (below chart data, above x-labels) colored by hour.
                # We'll place them at y=60→61.5 (just above yaxis min).

                # Build time segments: one rect per 30-min block across the 24h window
                x_start = df24["local_time"].min()
                x_end   = df24["local_time"].max()

                # Generate 30-min slots
                slot_start = x_start
                day_night_shapes = []

                def hour_to_daynight_color(hour_frac):
                    # hour_frac: 0–24 float. Noon=brightest, midnight=darkest.
                    # Map to a 0–1 "night index": 0=noon (lightest), 1=midnight (darkest)
                    # Distance from noon, normalized to 0–1
                    dist_from_noon = abs(hour_frac - 12.0)
                    if dist_from_noon > 12:
                        dist_from_noon = 24 - dist_from_noon
                    night_t = dist_from_noon / 12.0  # 0 at noon, 1 at midnight

                    # Palette stops (5 colors, evenly spaced 0→1):
                    # 0.00 → #a8ccd7  (noon, lightest)
                    # 0.25 → #7fa8b8
                    # 0.50 → #6b8f9e
                    # 0.75 → #4d6b7a
                    # 1.00 → #2d4a57  (midnight, darkest)
                    palette = [
                        (0xA8, 0xCC, 0xD7),
                        (0x7F, 0xA8, 0xB8),
                        (0x6B, 0x8F, 0x9E),
                        (0x4D, 0x6B, 0x7A),
                        (0x2D, 0x4A, 0x57),
                    ]
                    idx_f  = night_t * (len(palette) - 1)
                    idx_lo = int(idx_f)
                    idx_hi = min(idx_lo + 1, len(palette) - 1)
                    frac   = idx_f - idx_lo
                    r = int(palette[idx_lo][0] + frac * (palette[idx_hi][0] - palette[idx_lo][0]))
                    g = int(palette[idx_lo][1] + frac * (palette[idx_hi][1] - palette[idx_lo][1]))
                    b = int(palette[idx_lo][2] + frac * (palette[idx_hi][2] - palette[idx_lo][2]))
                    return f"rgb({r},{g},{b})"

                BAND_Y0 = -0.055   # paper coords: just below plot bottom edge
                BAND_Y1 = -0.01    # paper coords: at plot bottom edge
                slot_minutes = 30
                current_slot = x_start.replace(minute=(x_start.minute // slot_minutes) * slot_minutes,
                                               second=0, microsecond=0)

                while current_slot < x_end:
                    next_slot  = current_slot + datetime.timedelta(minutes=slot_minutes)
                    hour_frac  = current_slot.hour + current_slot.minute / 60.0
                    color      = hour_to_daynight_color(hour_frac)
                    day_night_shapes.append(dict(
                        type="rect",
                        xref="x", yref="paper",
                        x0=current_slot, x1=min(next_slot, x_end),
                        y0=BAND_Y0, y1=BAND_Y1,
                        fillcolor=color,
                        line=dict(width=0),
                        layer="above"
                    ))
                    current_slot = next_slot

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
                    shapes=day_night_shapes,
                    yaxis=dict(range=[60, 90], fixedrange=True, gridcolor='#f1f5f9',
                               zeroline=False, tickfont=dict(color='#64748b', size=11)),
                    xaxis=dict(tickformat="%I%p", gridcolor='#f1f5f9', showgrid=True,
                               tickfont=dict(color='#64748b', size=11), nticks=6),
                    margin=dict(l=20, r=10, t=5, b=32),
                    height=240,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False
                )
                st.plotly_chart(fig24, use_container_width=True, config={'displayModeBar': False})

            # ================================================================
            # CARD 3: PAST 7 DAYS
            # ================================================================
            with st.container(border=True):
                st.markdown('<div class="card-headline-text">Past 7 Days</div>', unsafe_allow_html=True)

                RANGE_MIN, RANGE_MAX = 60.0, 90.0
                SLICES = 60

                def temp_to_color(t):
                    p = (max(RANGE_MIN, min(RANGE_MAX, float(t))) - RANGE_MIN) / (RANGE_MAX - RANGE_MIN)
                    return f"rgb({int(255*p)},0,{int(255*(1.0-p))})"

                today_et      = now_time.date()
                ordered_dates = [today_et - datetime.timedelta(days=d) for d in range(6, -1, -1)]

                # Two-line tick labels: "Sat\n6/21"  (day name + m/d date)
                day_labels = []
                for d in ordered_dates:
                    name = "Today" if d == today_et else d.strftime("%a")
                    date_str = f"{d.month}/{d.day}"
                    day_labels.append(f"{name}<br>{date_str}")

                df7d["date_et"] = df7d["local_time"].dt.date
                agg_map = df7d.groupby("date_et")["temperature"].agg(["min", "max"]).to_dict("index")

                fig7d   = go.Figure()
                shapes  = []
                annotations = []

                for slot, cal_date in enumerate(ordered_dates):
                    if cal_date not in agg_map:
                        continue
                    t_min = float(agg_map[cal_date]["min"])
                    t_max = float(agg_map[cal_date]["max"])

                    x0 = slot - 0.28
                    x1 = slot + 0.28

                    for s in range(SLICES):
                        frac_lo = s / SLICES
                        frac_hi = (s + 1) / SLICES
                        y0 = t_min + frac_lo * (t_max - t_min)
                        y1 = t_min + frac_hi * (t_max - t_min)
                        shapes.append(dict(
                            type="rect",
                            xref="x", yref="y",
                            x0=x0, x1=x1, y0=y0, y1=y1,
                            fillcolor=temp_to_color((y0 + y1) / 2.0),
                            line=dict(width=0),
                            layer="below"
                        ))

                    # Max label above bar
                    annotations.append(dict(
                        x=slot, y=t_max,
                        xref="x", yref="y",
                        text=f"<b>{round(t_max)}°</b>",
                        showarrow=False,
                        yanchor="bottom",
                        font=dict(color="#1e293b", size=15),
                    ))
                    # Min label below bar
                    annotations.append(dict(
                        x=slot, y=t_min,
                        xref="x", yref="y",
                        text=f"<b>{round(t_min)}°</b>",
                        showarrow=False,
                        yanchor="top",
                        font=dict(color="#1e293b", size=15),
                    ))

                fig7d.update_layout(
                    shapes=shapes,
                    annotations=annotations,
                    # Padded range: 6° below RANGE_MIN for min labels, 6° above RANGE_MAX for max labels
                    yaxis=dict(range=[54, 96], fixedrange=True,
                               showgrid=False, zeroline=False, showticklabels=False),
                    xaxis=dict(
                        tickmode="array",
                        tickvals=list(range(7)),
                        ticktext=day_labels,
                        showgrid=False,
                        zeroline=False,
                        tickfont=dict(size=14, color='#1e293b'),
                        range=[-0.5, 6.5]
                    ),
                    margin=dict(l=10, r=10, t=25, b=10),
                    height=260,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False
                )
                st.plotly_chart(fig7d, use_container_width=True, config={'displayModeBar': False})

            # ================================================================
            # CARD 4: RECORDS
            # ================================================================
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
