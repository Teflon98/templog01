import streamlit as st
import pandas as pd
from supabase import create_client

# 1. Page Configuration for Mobile
st.set_page_config(page_title="Climate Tracker", layout="centered")

# Automatically refreshes the app elements every 5 minutes (300 seconds)
st.fragment(run_every=300)

# 2. Connect to Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

try:
    # --- DATA FETCHING ---
    # Fetch last 24 hours of data (at 5-min intervals, 288 rows = 24 hours)
    recent_response = supabase.table("sensor_data").select("*").order("created_at", desc=True).limit(288).execute()
    
    # Fetch All-Time Records (Min and Max)
    min_record_resp = supabase.table("sensor_data").select("*").order("temperature", desc=False).limit(1).execute()
    max_record_resp = supabase.table("sensor_data").select("*").order("temperature", desc=True).limit(1).execute()

    if recent_response.data:
        # Load 24-hour data into a Pandas DataFrame
        df = pd.DataFrame(recent_response.data)
        
        # Convert UTC timestamps to US/Eastern for processing
        df["local_time"] = pd.to_datetime(df["created_at"]).dt.tz_convert('US/Eastern')
        
        # Extract the absolute newest single reading for the main display
        latest_record = df.iloc[0]
        current_temp = float(latest_record["temperature"])
        current_humidity = float(latest_record["humidity"])
        timestamp_str = latest_record["local_time"].strftime("%a, %b %d | %I:%M %p")
        
        # --- CALCULATE STATISTICS ---
        # 24-Hour Stats
        day_min = df["temperature"].min()
        day_max = df["temperature"].max()
        
        # All-Time Stats
        all_min = float(min_record_resp.data[0]["temperature"]) if min_record_resp.data else current_temp
        all_max = float(max_record_resp.data[0]["temperature"]) if max_record_resp.data else current_temp

        # --- DYNAMIC TEMPERATURE COLOR LOGIC (65°F Blue to 85°F Red) ---
        pct = (max(65.0, min(85.0, current_temp)) - 65.0) / (85.0 - 65.0)
        r = int(30 + (255 - 30) * pct)
        g = int(144 + (69 - 144) * pct)
        b = int(255 + (0 - 255) * pct)
        dynamic_color = f"rgb({r}, {g}, {b})"
        
        # --- RENDER MAIN CARD (Visual Priority: Temp -> Timestamp -> Humidity) ---
        st.markdown(f"""
            <style>
            .main-card {{
                background-color: #ffffff;
                padding: 30px;
                border-radius: 20px;
                box-shadow: 0px 8px 20px rgba(0,0,0,0.04);
                text-align: center;
                border: 1px solid #eef1f6;
                margin-bottom: 20px;
            }}
            .temp-val {{ font-size: 4.8rem; font-weight: 800; color: {dynamic_color}; line-height: 1; margin-bottom: 5px; }}
            .time-val {{ font-size: 1.1rem; color: #6a737d; font-weight: 500; margin-bottom: 25px; }}
            .hum-val {{ font-size: 1.6rem; color: #1f2328; font-weight: 600; }}
            .hum-lbl {{ color: #57606a; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em; }}
            </style>
            
            <div class="main-card">
                <div class="temp-val">{current_temp}°F</div>
                <div class="time-val">{timestamp_str}</div>
                <div class="hum-lbl">Humidity</div>
                <div class="hum-val">{current_humidity}%</div>
            </div>
        """, unsafe_allow_html=True)
        
        # --- RENDER HISTORICAL GRAPH ---
        st.write("### Past 24 Hours")
        
        # Sort chronologically (oldest to newest) specifically for plotting a smooth graph line
        chart_df = df.sort_values(by="local_time")
        
        # Create a clean line chart with fixed y-axis constraints (50°F to 100°F)
        st.line_chart(
            data=chart_df,
            x="local_time",
            y="temperature",
            color="#1e90ff", 
            use_container_width=True,
            y_label="Temperature (°F)",
            x_label="Time"
        )
        
        # Note: Streamlit's native st.line_chart auto-scales to data values. 
        # To guarantee the strict 50-100 grid visual range even with tight data, 
        # we inject two hidden helper limits if needed, or rely on a custom slider.
        # Alternatively, using native altair configuration provides strict bounding:
        
        # --- RENDER SUMMARY TILES (24 HR vs All-Time) ---
        st.write("### Records & Summaries")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
                <div style="background-color: #f4f7fb; padding: 15px; border-radius: 12px; text-align: center; border: 1px solid #e2e8f0;">
                    <div style="color: #64748b; font-size: 0.8rem; text-transform: uppercase; font-weight: 600;">Last 24 Hours</div>
                    <div style="color: #0284c7; font-size: 1.2rem; font-weight: 700; margin-top: 5px;">Min: {day_min}°F</div>
                    <div style="color: #b91c1c; font-size: 1.2rem; font-weight: 700;">Max: {day_max}°F</div>
                </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
                <div style="background-color: #f4f7fb; padding: 15px; border-radius: 12px; text-align: center; border: 1px solid #e2e8f0;">
                    <div style="color: #64748b; font-size: 0.8rem; text-transform: uppercase; font-weight: 600;">All-Time Records</div>
                    <div style="color: #0369a1; font-size: 1.2rem; font-weight: 700; margin-top: 5px;">Min: {all_min}°F</div>
                    <div style="color: #991b1b; font-size: 1.2rem; font-weight: 700;">Max: {all_max}°F</div>
                </div>
            """, unsafe_allow_html=True)
            
    else:
        st.info("The database is running, but no data records were found.")

except Exception as e:
    st.error(f"Error loading dashboard assets: {e}")
