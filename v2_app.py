import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import plotly.graph_objects as go

# --- 1. SET PHONE VIEWPORT & AUTOMATIC REFRESH ---
st.set_page_config(page_title="Climate v2", layout="centered")
st.fragment(run_every=300)

# Inject advanced CSS for absolute mobile formatting, container cards, and structural layouts
st.markdown("""
    <style>
    /* Maximize container real estate for Pixel 9 Pro */
    .block-container { padding-top: 0.5rem; padding-bottom: 1rem; padding-left: 0.6rem; padding-right: 0.6rem; max-width: 460px !important; }
    div[data-testid="stVerticalBlock"] { gap: 0.6rem; }
    footer { visibility: hidden; }
    
    /* Clean, structured card styling */
    .dashboard-card {
        background-color: #ffffff;
        padding: 16px 14px;
        border-radius: 18px;
        box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.03);
        border: 1px solid #eef1f6;
        margin-bottom: 0.2rem;
    }
    .card-title {
        text-align: center;
        font-weight: 700;
        font-size: 1.15rem;
        margin-bottom: 12px;
        color: #1f2328;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. CONNECT TO DATABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

try:
    # --- 3. PULL SENSOR LOGS ---
    recent_resp = supabase.table("sensor_data").select("*").order("created_at", desc=True).limit(288).execute()
    days7_resp = supabase.table("sensor_data").select("*").order("created_at", desc=True).limit(2016).execute()
    min_record_resp = supabase.table("sensor_data").select("*").order("temperature", desc=False).limit(1).execute()
    max_record_resp = supabase.table("sensor_data").select("*").order("temperature", desc=True).limit(1).execute()

    if recent_resp.data and days7_resp.data:
        # Load datasets into dataframes
        df24 = pd.DataFrame(recent_resp.data)
        df7d = pd.DataFrame(days7_resp.data)
        
        # Adjust time zones natively
        df24["local_time"] = pd.to_datetime(df24["created_at"]).dt.tz_convert('US/Eastern')
        df7d["local_time"] = pd.to_datetime(df7d["created_at"]).dt.tz_convert('US/Eastern')
        
        # Sort current 24 hour view chronologically for smooth line rendering
        df24 = df24.sort_values(by="local_time")
        
        # Extract immediate sensor strings
        latest_record = df24.iloc[-1]
        current_temp = float(latest_record["temperature"])
        current_humidity = float(latest_record["humidity"])
        timestamp_str = latest_record["local_time"].strftime("%A, %B %d, %Y, %I:%M %p").replace("AM", "a.m.").replace("PM", "p.m.")

        # --- 4. TREND ARROW LOGIC ---
        arrow = "→"
        if len(df24) >= 3:
            prev_avg = (float(df24.iloc[-2]["temperature"]) + float(df24.iloc[-3]["temperature"])) / 2.0
            if current_temp > prev_avg + 0.1: arrow = "↑"
            elif current_temp < prev_avg - 0.1: arrow = "↓"

        # --- 5. TEMPERATURE SOLID COLOR CALCULATION (RGB 0,0,255 to 255,0,0) ---
        pct = (max(50.0, min(80.0, current_temp)) - 50.0) / (80.0 - 50.0)
        r = int(0 + (255 - 0) * pct)
        g = 0
        b = int(255 + (0 - 255) * pct)
        solid_temp_color = f"rgb({r}, {g}, {b})"

        # --- 6. RENDER TOP SECTION METRICS (Slightly smaller font to prevent cut-off) ---
        st.markdown(f"""
            <div class="dashboard-card" style="text-align: center; padding-top: 10px; padding-bottom: 14px;">
                <div style="font-size: 5.4rem; font-weight: 800; color: {solid_temp_color}; line-height: 1.05; display: inline-block; position: relative; letter-spacing: -2px;">
                    {current_temp}°F<span style="font-size: 2.2rem; font-weight: 500; color: #1f2328; margin-left: 6px; vertical-align: middle;">{arrow}</span>
                </div>
                <div style="font-size: 1.15rem; color: #1f2328; font-weight: 600; margin-top: 2px; margin-bottom: 2px;">Humidity {current_humidity}%</div>
                <div style="font-size: 1.0rem; color: #57606a; font-weight: 400;">{timestamp_str}</div>
            </div>
        """, unsafe_allow_html=True)

        # --- 7. CARD 2: PAST 24 HOURS WITH TRUE VERTICAL GRADIENT ---
        st.markdown('<div class="dashboard-card"><div class="card-title">Past 24 Hours</div>', unsafe_allow_html=True)
        
        fig24 = go.Figure()
        
        # The Line Trace
        fig24.add_trace(go.Scatter(
            x=df24["local_time"], y=df24["temperature"],
            mode='lines',
            line=dict(width=4, color='#2d3748', shape='spline'),
            name="Temperature"
        ))
        
        # Inject linear gradient directly via layout images mapping to an SVG gradient background
        fig24.update_layout(
            yaxis=dict(range=[50, 90], fixedrange=True, gridcolor='#edf2f7', tickfont=dict(size=11, color='#4a5568')),
            xaxis=dict(tickformat="%I%p", tickvals=[df24["local_time"].min(), df4_mid := df24["local_time"].median(), df24["local_time"].max()], gridcolor='#edf2f7', tickfont=dict(size=11, color='#4a5568')),
            margin=dict(l=22, r=10, t=10, b=15),
            height=180,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            # Create the dynamic bounding blue-to-red gradient background mask beneath the chart
            images=[dict(
                source="https://raw.githubusercontent.com/unrshd/assets/main/blue-red-gradient.png",
                xref="paper", yref="paper",
                x=0, y=0, sizex=1, sizey=1,
                sizing="stretch", layer="below", opacity=0.35
            )]
        )
        st.plotly_chart(fig24, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

        # --- 8. CARD 3: PAST 7 DAYS (Floating Windows) ---
        st.markdown('<div class="dashboard-card"><div class="card-title">Past 7 Days</div>', unsafe_allow_html=True)
        
        df7d["day_name"] = df7d["local_time"].dt.strftime("%a")
        agg_7d = df7d.groupby("day_name")["temperature"].agg(["min", "max"]).reset_index()
        day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        agg_7d['day_name'] = pd.Categorical(agg_7d['day_name'], categories=day_order, ordered=True)
        agg_7d = agg_7d.sort_values('day_name')

        fig7d = go.Figure()
        base_vals = agg_7d["min"].tolist()
        lengths = (agg_7d["max"] - agg_7d["min"]).tolist()

        for i, row in agg_7d.iterrows():
            def get_color_str(temp_val):
                t_pct = (max(50.0, min(80.0, temp_val)) - 50.0) / (80.0 - 50.0)
                t_r = int(0 + (255 - 0) * t_pct)
                t_b = int(255 + (0 - 255) * t_pct)
                return f"rgb({t_r}, 0, {t_b})"

            # Custom text formatting inside the narrow columns
            fig7d.add_trace(go.Bar(
                x=[row["day_name"]],
                y=[lengths[i]],
                base=[base_vals[i]],
                marker=dict(
                    color=[row["max"]],
                    colorscale=[[0.0, get_color_str(row["min"])], [1.0, get_color_str(row["max"])]],
                    line=dict(width=0)
                ),
                text=f"{round(row['max'])}°<br><br>{round(row['min'])}°",
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(size=12, color="white", weight="bold"),
                width=0.55
            ))

        fig7d.update_layout(
            yaxis=dict(range=[45, 95], fixedrange=True, showgrid=False, zeroline=False, showticklabels=False),
            xaxis=dict(showgrid=False, tickfont=dict(size=12, color='#1f2328', weight="bold")),
            margin=dict(l=5, r=5, t=15, b=10),
            height=200,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            barmode='stack'
        )
        st.plotly_chart(fig7d, use_container_width=True, config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

        # --- 9. CARD 4: ALL-TIME RECORDS SECTION ---
        all_min = float(min_record_resp.data[0]["temperature"]) if min_record_resp.data else current_temp
        all_max = float(max_record_resp.data[0]["temperature"]) if max_record_resp.data else current_temp
        min_date = pd.to_datetime(min_record_resp.data[0]["created_at"]).tz_convert('US/Eastern').strftime("%B %d, %Y") if min_record_resp.data else "June 15, 2026"
        max_date = pd.to_datetime(max_record_resp.data[0]["created_at"]).tz_convert('US/Eastern').strftime("%B %d, %Y") if max_record_resp.data else "June 15, 2026"

        st.markdown(f"""
            <div class="dashboard-card">
                <div class="card-title" style="margin-bottom: 8px;">All-Time Records</div>
                <table style="width: 100%; border-collapse: collapse; border: none;">
                    <tr style="border: none;">
                        <td style="width: 50%; vertical-align: top; border: none; text-align: center;">
                            <div style="font-weight: 500; font-size: 0.9rem; color: #57606a; text-transform: uppercase;">Minimum</div>
                            <div style="font-size: 1.4rem; font-weight: 700; color: #0000ff; margin-top: 1px;">{all_min}°F</div>
                            <div style="font-size: 0.85rem; color: #6a737d;">{min_date}</div>
                        </td>
                        <td style="width: 50%; vertical-align: top; border: none; text-align: center; border-left: 1px solid #eef1f6;">
                            <div style="font-weight: 500; font-size: 0.9rem; color: #57606a; text-transform: uppercase;">Maximum</div>
                            <div style="font-size: 1.4rem; font-weight: 700; color: #ff0000; margin-top: 1px;">{all_max}°F</div>
                            <div style="font-size: 0.85rem; color: #6a737d;">{max_date}</div>
                        </td>
                    </tr>
                </table>
            </div>
        """, unsafe_allow_html=True)

    else:
        st.info("Awaiting sensor data logs to populate dashboard canvas layer blocks.")

except Exception as e:
    st.error(f"Render pipeline variance encountered: {e}")
