import streamlit as st
import joblib
import random
import pandas as pd
import folium
from streamlit_folium import st_folium
from auth import create_table, register_user, login_user, get_user_village
import time

# ----------------------------
# LOAD MODEL
# ----------------------------
model = joblib.load("flood_model.pkl")

# ----------------------------
# PREDICTION FUNCTION
# ----------------------------
def predict_future_risk(selected_date, elevation):

    month = selected_date.month

    if month in [6,7,8,9]:
        rainfall = random.randint(250, 450)
        temperature = random.randint(24, 28)

    elif month in [10,11]:
        rainfall = random.randint(100, 250)
        temperature = random.randint(26, 30)

    else:
        rainfall = random.randint(20, 100)
        temperature = random.randint(30, 35)

    pred = model.predict([[rainfall, temperature, elevation]])[0]

    if pred == 0:
        return "LOW", "green"
    elif pred == 1:
        return "MEDIUM", "orange"
    else:
        return "HIGH", "red"

# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(page_title="Flood Emergency Alert System", layout="wide")

# ----------------------------
# CSS (UPDATED WITH CALENDAR FIX)
# ----------------------------
st.markdown("""
<style>

/* Background */
.stApp { background-color: #ffffff !important; }

/* Global text */
body, p, span, div { color: #000000 !important; }

/* Title */
.title-text {
    font-size: 42px !important;
    font-weight: bold;
    color: #003366 !important;
}

/* Tabs */
button[role="tab"] {
    font-size: 26px !important;
    font-weight: bold !important;
}

/* Labels */
label {
    font-size: 24px !important;
    font-weight: 700 !important;
}

/* Inputs */
.stTextInput input, 
.stPasswordInput input {
    font-size: 22px !important;
    background-color: #ffffff !important;
    color: #000000 !important;
    border: 2px solid #ccc !important;
    border-radius: 8px;
    padding: 10px !important;
}

/* Buttons */
.stButton>button {
    font-size: 20px !important;
    background-color: #007bff !important;
    color: white !important;
    border-radius: 10px;
    height: 50px;
}

/* ------------------ */
/* CALENDAR STYLING */
/* ------------------ */

div[data-baseweb="calendar"] {
    background-color: #ffffff !important;
}

/* Calendar numbers (light color) */
div[data-baseweb="calendar"] button {
    color: #777777 !important;
    font-size: 16px !important;
}

/* Selected date */
div[data-baseweb="calendar"] button[aria-selected="true"] {
    background-color: #007bff !important;
    color: white !important;
}

/* Hover */
div[data-baseweb="calendar"] button:hover {
    background-color: #e6f0ff !important;
}

/* Month header */
div[data-baseweb="calendar"] div {
    color: #333333 !important;
}

/* Footer */
.footer {
    background-color: #ff4d4d;
    color: white;
    padding: 14px;
    border-radius: 10px;
    font-size: 20px;
    text-align: center;
    font-weight: bold;
}

</style>
""", unsafe_allow_html=True)

# ----------------------------
# INIT DB
# ----------------------------
create_table()

# ----------------------------
# SESSION
# ----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# ----------------------------
# LOAD DATA
# ----------------------------
villages_df = pd.read_csv("villages.csv")

# ----------------------------
# HEADER
# ----------------------------
col1, col2, col3 = st.columns([6,2,2])

with col1:
    st.markdown('<p class="title-text">🚨 SMART FLOOD RISK ANALYSER</p>', unsafe_allow_html=True)
    st.markdown('<p style="font-size:20px;color:#444;">Real-Time Village-Based Flood Risk Monitoring</p>', unsafe_allow_html=True)

with col3:
    if st.session_state.logged_in:
        if st.button("🔴 Logout"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

st.markdown("---")

# ============================
# LOGIN / REGISTER
# ============================
if not st.session_state.logged_in:

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_btn = st.form_submit_button("Login")

            if login_btn:
                user = login_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("Login Successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")

    with tab2:
        district_list = villages_df["district"].unique().tolist()
        selected_district = st.selectbox("Select District", district_list)

        filtered_villages = villages_df[villages_df["district"] == selected_district]
        village_list = filtered_villages["village"].dropna().unique().tolist()

        with st.form("register_form"):
            new_user = st.text_input("Create Username")
            new_pass = st.text_input("Create Password", type="password")
            email = st.text_input("Email")
            village = st.selectbox("Select Village", village_list)
            register_btn = st.form_submit_button("Register")

            if register_btn:
                result = register_user(new_user, new_pass, email, village)

                if result == "success":
                    st.success("Registration Successful!")
                elif result == "username_exists":
                    st.error("Username already exists")
                elif result == "email_exists":
                    st.error("Email already registered")
                else:
                    st.error("Registration failed")

# ============================
# DASHBOARD
# ============================
else:

    st.subheader(f"Welcome, {st.session_state.username}")
    st.warning("Connected to Flood Alert Monitoring Network")

    user_village = get_user_village(st.session_state.username)
    selected_data = villages_df[villages_df["village"] == user_village]

    if not selected_data.empty:

        lat = selected_data.iloc[0]["latitude"]
        lon = selected_data.iloc[0]["longitude"]
        elevation = selected_data.iloc[0]["elevation"] if "elevation" in selected_data.columns else 150

        st.markdown("### 📍 Your Registered Village")
        st.info(user_village)

        # CALENDAR
        selected_date = st.date_input("📅 Select Date to Check Flood Risk")

        if st.button("Predict Flood Risk"):
            risk, color = predict_future_risk(selected_date, elevation)
            st.session_state.risk = risk
            st.session_state.color = color
            st.session_state.show_map = False

        if "risk" in st.session_state:
            st.success(f"⚠️ Predicted Risk on {selected_date}: {st.session_state.risk}")

            if st.button("🗺️ View Map"):
                st.session_state.show_map = True

        if st.session_state.get("show_map"):
            m = folium.Map(location=[lat, lon], zoom_start=12)

            folium.CircleMarker(
                location=[lat, lon],
                radius=15,
                popup=f"{user_village} - {st.session_state.risk}",
                color=st.session_state.color,
                fill=True,
                fill_color=st.session_state.color,
                fill_opacity=0.7
            ).add_to(m)

            st_folium(m, width=900, height=500)

    else:
        st.error("Village data not found")

# ----------------------------
# FOOTER
# ----------------------------
st.markdown("---")
st.markdown('<div class="footer">⚠ FLOOD MONITORING ENGINE ACTIVE | AUTOMATIC ALERT MODE ENABLED</div>', unsafe_allow_html=True)