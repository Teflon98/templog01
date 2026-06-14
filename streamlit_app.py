import streamlit as st
import pandas as pd
from supabase import create_client

# 1. Page Configuration for Mobile
st.set_page_config(page_title="Climate Tracker", layout="centered")
st.fragment(run_every=300) # Automatically reruns the script every 5 minutes (300 seconds)

# 2. Connect to Supabase using the secure secrets
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# 3. Pull Data from Database
try:
    # Fetch the single newest reading for the main display
    latest_response = supabase.table("sensor_data").select("*").order("created_at", desc=True).limit(1).execute()
    
    if latest_response.data:
        latest_record = latest_response.data[0]
        current_temp = float(latest_record["temperature"])
        current_humidity = float(latest_record["humidity"])
        
        # Convert the UTC timestamp to Eastern Time for display
        utc_time = pd.to_datetime(latest_record["created_at"])
        local_time = utc_time.tz_convert('US/Eastern')
        timestamp_str = local_time.strftime("%a, %b %d | %I:%M %p")
        
        # 4. Calculate Dynamic Color Gradient (65°F Blue to 85°F Red)
        pct = (max(65.0, min(85.0, current_temp)) - 65.0) / (85.0 - 65.0)
        r = int(30 + (255 - 30) * pct)
        g = int(144 + (69 - 144) * pct)
        b = int(255 + (0 - 255) * pct)
        dynamic_color = f"rgb({r}, {g}, {b})"
        
        # 5. Inject Clean Layout Matching Visual Priority
        # Priority: Temperature -> Time Stamp -> Humidity
        st.markdown(f"""
            <style>
            .main-card {{
                background-color: #ffffff;
                padding: 30px;
                border-radius: 20px;
                box-shadow: 0px 8px 20px rgba(0,0,0,0.05);
                text-align: center;
                border: 1px solid #eef1f6;
                margin-bottom: 25px;
            }}
            .temp-val {{
                font-size: 4.8rem;
                font-weight: 800;
                color: {dynamic_color};
                line-height: 1;
                margin-bottom: 5px;
            }}
            .time-val {{
                font-size: 1.1rem;
                color: #6a737d;
                font-weight: 500;
                margin-bottom: 25px;
            }}
            .hum-val {{
                font-size: 1.6rem;
                color: #1f2328;
                font-weight: 600;
            }}
            .hum-lbl {{
                color: #57606a;
                font-size: 0.9rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            </style>
            
            <div class="main-card">
                <div class="temp-val">{current_temp}°F</div>
                <div class="time-val">{timestamp_str}</div>
                <div class="hum-lbl">Humidity</div>
                <div class="hum-val">{current_humidity}%</div>
            </div>
        """, unsafe_allow_html=True)
        
    else:
        st.info("The database is connected, but no records were found yet.")

except Exception as e:
    st.error(f"Could not connect to database: {e}")
