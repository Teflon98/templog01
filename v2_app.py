import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client
import plotly.graph_objects as go

# --- 1. SET PHONE VIEWPORT & AUTOMATIC REFRESH ---
st.set_page_config(page_title="Climate v2", layout="centered")
st.fragment(run_every=300)

# CSS for true mobile optimization and card nesting fixes
st.markdown("""
    <style>
    /* Prevent horizontal scrolling and maximize app width for Pixel 9 Pro */
    .block-container { 
        padding-top: 0.5rem; 
        padding-bottom: 2rem; 
        padding-left: 0.5rem; 
        padding-right: 0.5rem; 
        max-width: 100% !important; 
    }
    
    /* Fix Streamlit's default container padding to make charts feel native to cards */
    [data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 0 !important;
    }
    
    /* Force specific font scaling for the large temp to prevent overflow */
    .temp-text {
        font-size: clamp(4rem, 18vw, 6.2rem);
        font-weight: 800;
        line-height: 0.9;
        white-space: nowrap;
        letter-spacing: -3px;
        margin-bottom: 10px;
    }
    
    /* Custom Card Headlines */
    .card-headline {
        font-size: 1.1rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #000000;
        text-align: center;
        margin-bottom: 10px;
        letter-spacing: 0.05em;
    }
    
    footer { visibility: hidden; }
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
        df24 = pd.DataFrame(recent_resp.data)
        df7d = pd.DataFrame(days7_resp.data)
        df24["local_time"] = pd.to_datetime(df24["created_at"]).dt.tz_convert('US/Eastern')
        df7d["local_time"] = pd.to_datetime(df7d["created_at"]).dt.tz_convert('US/Eastern')
        df24 = df24.sort_values(by="local_time")
        
        latest_record = df24.iloc[-1]
        current_temp = float(latest_record["temperature"])
        current_humidity = float(latest_record["humidity"])
        timestamp_str = latest_record["local_time"].strftime("%A, %B %d, %Y, %I:%M %p").replace("AM", "a.m.").replace("PM", "p.m.")

        # Trend Arrow Logic
        arrow = "→"
        if len(df24) >= 3:
            prev_avg = (float(df24.iloc[-2]["temperature"]) + float(df24.iloc[-3]["temperature"])) / 2.0
            if current_temp > prev_avg + 0.1: arrow = "↑"
            elif current_temp < prev_avg - 0.1: arrow = "↓"

        # Current Temp Color
        pct = (max(50.0, min(80.0, current_temp)) - 50.0) / (80.0 - 50.0)
        solid_color = f"rgb({int(255 * pct)}, 0, {int(255 * (1-pct))})"

        # --- TOP CARD: CURRENT TEMP ---
        with st.container(border=True):
            st.markdown(f"""
                <div style="text-align: center; padding: 10px 0;">
                    <div class="temp-text" style="color: {solid_color};">
                        {current_temp}°F<span style="font-size: 0.4em; color: #333; margin-left: 5px;">{arrow}</span>
                    </div>
                    <div style="font-size: 1.2rem; font-weight: 600;">Humidity {current_humidity}%</div>
                    <div style="font-size: 1rem; color: #666; margin-top: 4px;">{timestamp_str}</div>
                </div>
            """, unsafe_allow_html=True)

        # --- SECOND CARD: PAST 24 HOURS (WITH GRADIENT) ---
        with st.container(border=True):
            st.markdown('<div class="card-headline">Past 24 Hours</div>', unsafe_allow_html=True)
            fig24 = go.Figure()
            
            # Using the new fillgradient property (Plotly 5.20+)
            fig24.add_trace(go.Scatter(
                x=df24["local_time"], y=df24["temperature"],
                mode='lines',
                line=dict(width=4, color='#333', shape='spline'),
                fill='tozeroy',
                fillgradient=dict(
                    type="vertical",
                    colorscale=[(0.0, "blue"), (0.5, "purple"), (1.0, "red")]
                )
            ))
            fig24.update_layout(
                yaxis=dict(range=[50, 90], fixedrange=True, gridcolor='#eee'),
                xaxis=dict(tickformat="%I%p", gridcolor='#eee', nticks=5),
                margin=dict(l=25, r=10, t=5, b=20),
                height=220,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False
            )
            st.plotly_chart(fig24, use_container_width=True, config={'displayModeBar': False})

        # --- THIRD CARD: PAST 7 DAYS ---
        with st.container(border=True):
            st.markdown('<div class="card-headline">Past 7 Days</div>', unsafe_allow_html=True)
            df7d["day_name"] = df7d["local_time"].dt.strftime("%a")
            agg_7d = df7d.groupby("day_name")["temperature"].agg(["min", "max"]).reset_index()
            day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            agg_7d['day_name'] = pd.Categorical(agg_7d['day_name'], categories=day_order, ordered=True)
            agg_7d = agg_7d.sort_values('day_name')

            fig7d = go.Figure()
            for i, row in agg_7d.iterrows():
                # Map colors based on global 50-80 scale
                def get_rgb(val):
                    p = (max(50.0, min(80.0, val)) - 50.0) / (80.0 - 50.0)
                    return f"rgb({int(255*p)}, 0, {int(255*(1-p))})"
                
                fig7d.add_trace(go.Bar(
                    x=[row["day_name"]], y=[row["max"] - row["min"]], base=[row["min"]],
                    marker=dict(
                        color=[row["max"]],
                        colorscale=[[0, get_rgb(row["min"])], [1, get_rgb(row["max"])]],
                        line=dict(width=0)
                    ),
                    text=f"{round(row['max'])}°<br><br>{round(row['min'])}°",
                    textposition="inside", insidetextanchor="middle",
                    textfont=dict(color="white", size=12, weight="bold"),
                    width=0.6
                ))
            fig7d.update_layout(
                yaxis=dict(range=[45, 95], showgrid=False, showticklabels=False),
                xaxis=dict(showgrid=False),
                margin=dict(l=5, r=5, t=10, b=10),
                height=220,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False, barmode='stack'
            )
            st.plotly_chart(fig7d, use_container_width=True, config={'displayModeBar': False})

        # --- FOURTH CARD: RECORDS ---
        with st.container(border=True):
            st.markdown('<div class="card-headline">All-Time Records</div>', unsafe_allow_html=True)
            all_min = float(min_record_resp.data[0]["temperature"]) if min_record_resp.data else current_temp
            all_max = float(max_record_resp.data[0]["temperature"]) if max_record_resp.data else current_temp
            min_date = pd.to_datetime(min_record_resp.data[0]["created_at"]).tz_convert('US/Eastern').strftime("%b %d, %Y")
            max_date = pd.to_datetime(max_record_resp.data[0]["created_at"]).tz_convert('US/Eastern').strftime("%b %d, %Y")
            
            st.markdown(f"""
                <div style="display: flex; justify-content: space-around; text-align: center; padding-bottom: 10px;">
                    <div>
                        <div style="font-size: 0.8rem; color: #666; font-weight: 600;">MIN RECORD</div>
                        <div style="font-size: 1.4rem; font-weight: 800; color: blue;">{all_min}°F</div>
                        <div style="font-size: 0.8rem;">{min_date}</div>
                    </div>
                    <div style="border-left: 1px solid #eee;"></div>
                    <div>
                        <div style="font-size: 0.8rem; color: #666; font-weight: 600;">MAX RECORD</div>
                        <div style="font-size: 1.4rem; font-weight: 800; color: red;">{all_max}°F</div>
                        <div style="font-size: 0.8rem;">{max_date}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Render Error: {e}")

Feel free to refresh your testing URL and let me know if those cards and gradients are now behaving perfectly on your phone!
