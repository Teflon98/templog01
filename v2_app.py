import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import plotly.graph_objects as go

# --- 1. SET PHONE VIEWPORT & AUTOMATIC REFRESH ---
st.set_page_config(page_title="Climate v2", layout="centered")
st.fragment(run_every=300)

# Inject CSS to remove standard padding and maximize screen real estate for Pixel 9 Pro
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; padding-left: 0.5rem; padding-right: 0.5rem; max-width: 450px !important; }
    div[data-testid="stVerticalBlock"] { gap: 0.8rem; }
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. CONNECT TO DATABASE ---
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

try:
    # --- 3. PULL SENSOR LOGS ---
    # Fetch 24 Hours of historical data (288 rows)
    recent_resp = supabase.table("sensor_data").select("*").order("created_at", desc=True).limit(288).execute()
    
    # Fetch 7 Days of historical records for high/low aggregation
    days7_resp = supabase.table("sensor_data").select("*").order("created_at", desc=True).limit(2016).execute()
    
    # Fetch All-Time Records
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

        # --- 4. TREND ARROW LOGIC (Averaging current vs last 2 readings) ---
        arrow = "→"
        if len(df24) >= 3:
            prev_avg = (float(df24.iloc[-2]["temperature"]) + float(df24.iloc[-3]["temperature"])) / 2.0
            if current_temp > prev_avg + 0.1: arrow = "↑"
            elif current_temp < prev_avg - 0.1: arrow = "↓"

        # --- 5. TEMPERATURE SOLID COLOR CALCULATION (RGB 0,0,255 to 255,0,0) ---
        # Scale range: 50°F to 80°F+
        pct = (max(50.0, min(80.0, current_temp)) - 50.0) / (80.0 - 50.0)
        r = int(0 + (255 - 0) * pct)
        g = 0
        b = int(255 + (0 - 255) * pct)
        solid_temp_color = f"rgb({r}, {g}, {b})"

        # --- 6. RENDER TOP SECTION METRICS ---
        st.markdown(f"""
            <div style="text-align: center; font-family: -apple-system, BlinkMacSystemFont, sans-serif;">
                <div style="font-size: 6.8rem; font-weight: 800; color: {solid_temp_color}; line-height: 1; display: inline-block; position: relative; letter-spacing: -2px;">
                    {current_temp}°F<span style="font-size: 2.5rem; font-weight: 400; color: #1f2328; margin-left: 5px; vertical-align: middle;">{arrow}</span>
                </div>
                <div style="font-size: 1.2rem; color: #1f2328; font-weight: 500; margin-top: 2px; margin-bottom: 4px;">Humidity {current_humidity}%</div>
                <div style="font-size: 1.1rem; color: #1f2328; font-weight: 400;">{timestamp_str}</div>
            </div>
        """, unsafe_allow_html=True)

        # --- 7. GRAPH 1: PAST 24 HOURS (Smooth Curve with Gradient Fill) ---
        st.markdown("<div style='text-align: center; font-weight: 600; font-size: 1.3rem; margin-top: 15px; margin-bottom: -5px; color: #000000;'>Past 24 hours</div>", unsafe_allow_html=True)
        
        fig24 = go.Figure()
        
        # Render custom gradient fill under the curve using Plotly's explicit SVG path generator
        fig24.add_trace(go.Scatter(
            x=df24["local_time"], y=df24["temperature"],
            mode='lines',
            line=dict(width=4, color='rgba(0,0,255,0.7)', shape='spline'), # Spline handles smooth curve layout
            fill='tozeroy',
            fillcolor='rgba(128,0,128,0.15)' # Midpoint blending translucency
        ))
        
        fig24.update_layout(
            yaxis=dict(range=[50, 90], fixedrange=True, gridcolor='#eef1f6', tickfont=dict(size=12, color='#000')),
            xaxis=dict(tickformat="%I%p", tickvals=[df24["local_time"].min(), df24["local_time"].median(), df24["local_time"].max()], gridcolor='#eef1f6', tickfont=dict(size=12, color='#000')),
            margin=dict(l=25, r=10, t=10, b=20),
            height=200,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False
        )
        st.plotly_chart(fig24, use_container_width=True, config={'displayModeBar': False})

        # --- 8. GRAPH 2: PAST 7 DAYS (Floating Range Columns over Spatial Gradient) ---
        st.markdown("<div style='text-align: center; font-weight: 600; font-size: 1.3rem; margin-top: 10px; margin-bottom: 5px; color: #000000;'>Past 7 Days</div>", unsafe_allow_html=True)
        
        # Aggregate data by day of the week
        df7d["day_name"] = df7d["local_time"].dt.strftime("%a")
        agg_7d = df7d.groupby("day_name")["temperature"].agg(["min", "max"]).reset_index()
        
        # Ensure chronological ordering sequence mapping
        day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        agg_7d['day_name'] = pd.Categorical(agg_7d['day_name'], categories=day_order, ordered=True)
        agg_7d = agg_7d.sort_values('day_name')

        fig7d = go.Figure()

        # Calculate floating column arrays
        base_vals = agg_7d["min"].tolist()
        lengths = (agg_7d["max"] - agg_7d["min"]).tolist()

        # Build floating range column structures
        for i, row in agg_7d.iterrows():
            # Calculate the color bounds for the top and bottom of each independent column window
            def get_color_str(temp_val):
                t_pct = (max(50.0, min(80.0, temp_val)) - 50.0) / (80.0 - 50.0)
                t_r = int(0 + (255 - 0) * t_pct)
                t_b = int(255 + (0 - 255) * t_pct)
                return f"rgb({t_r}, 0, {t_b})"

            # Render each column using an individual marker dictionary to support independent gradient mapping
            fig7d.add_trace(go.Bar(
                x=[row["day_name"]],
                y=[lengths[i]],
                base=[base_vals[i]],
                marker=dict(
                    color=[row["max"]],
                    colorscale=[[0.0, get_color_str(row["min"])], [1.0, get_color_str(row["max"])]],
                    line=dict(width=0)
                ),
                text=f"Max: {round(row['max'])}°<br><br><br><br>Min: {round(row['min'])}°",
                textposition="inside",
                insidetextanchor="middle",
                textfont=dict(size=11, color="white"),
                width=0.6
            ))

        fig7d.update_layout(
            yaxis=dict(range=[40, 95], fixedrange=True, gridcolor='rgba(0,0,0,0)', showgrid=False, zeroline=False, showticklabels=False),
            xaxis=dict(gridcolor='rgba(0,0,0,0)', tickfont=dict(size=13, color='#000')),
            margin=dict(l=10, r=10, t=10, b=20),
            height=250,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            barmode='stack'
        )
        st.plotly_chart(fig7d, use_container_width=True, config={'displayModeBar': False})

        # --- 9. ALL-TIME RECORDS SECTION ---
        all_min = float(min_record_resp.data[0]["temperature"]) if min_record_resp.data else current_temp
        all_max = float(max_record_resp.data[0]["temperature"]) if max_record_resp.data else current_temp
        
        # Fallback date extraction if record holds structural timestamps
        min_date = pd.to_datetime(min_record_resp.data[0]["created_at"]).tz_convert('US/Eastern').strftime("%B %d, %Y") if min_record_resp.data else "June 15, 2026"
        max_date = pd.to_datetime(max_record_resp.data[0]["created_at"]).tz_convert('US/Eastern').strftime("%B %d, %Y") if max_record_resp.data else "June 15, 2026"

        st.markdown(f"""
            <div style="background-color: #f7f9fa; border-radius: 16px; padding: 15px; border: 1px solid #eef1f6; font-family: -apple-system, sans-serif; margin-top: 5px;">
                <table style="width: 100%; border-collapse: collapse; border: none;">
                    <tr style="border: none;">
                        <td style="width: 50%; vertical-align: top; border: none;">
                            <div style="font-weight: bold; font-size: 1.1rem; color: #000000;">Record Minimum</div>
                            <div style="font-size: 1.1rem; color: #1f2328; margin-top: 2px;">{all_min}°F on</div>
                            <div style="font-size: 1.0rem; color: #57606a;">{min_date}</div>
                        </td>
                        <td style="width: 50%; vertical-align: top; border: none; padding-left: 15px;">
                            <div style="font-weight: bold; font-size: 1.1rem; color: #000000;">Record Maximum</div>
                            <div style="font-size: 1.1rem; color: #1f2328; margin-top: 2px;">{all_max}°F on</div>
                            <div style="font-size: 1.0rem; color: #57606a;">{max_date}</div>
                        </td>
                    </tr>
                </table>
            </div>
        """, unsafe_allow_html=True)

    else:
        st.info("Awaiting sensor payload broadcasts to populate v2 canvas layers.")

except Exception as e:
    st.error(f"Render pipeline variance encountered: {e}")
