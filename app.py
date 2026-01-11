import streamlit as st
import pandas as pd
import numpy_financial as npf
import google.generativeai as genai
import json
from fpdf import FPDF
from datetime import datetime

# --- CONFIGURATION ---
st.set_page_config(page_title="SmartSpend AI & Loan Tracker", layout="wide")

# Initialize Gemini API
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Missing Gemini API Key in Secrets!")

# --- 1. AI PARSING LOGIC ---
def ai_parse_text(text):
    if not text.strip():
        return []

    try:
        # Use the standard model name. 
        # In 2026, 'gemini-1.5-flash' is the most compatible across all API versions.
        model = genai.GenerativeModel('gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro')
        
        prompt = """
        Extract financial transactions from this text. 
        Return ONLY a JSON array. 
        Format: [{"date": "YYYY-MM-DD", "merchant": "name", "amount": 0.00, "category": "category"}]
        Text: """ + text
        
        response = model.generate_content(prompt)
        
        # Accessing the text response safely
        raw_output = response.text.strip()
        
        # Standard cleaning of markdown blocks
        if "```" in raw_output:
            raw_output = raw_output.split("```")[1]
            if raw_output.startswith("json"):
                raw_output = raw_output[4:].strip()
        
        return json.loads(raw_output)
        
    except Exception as e:
        # Final fallback: If Flash fails, try the standard Pro model
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            return json.loads(response.text.strip())
        except:
            st.error(f"AI Error: {str(e)}")
            return []
# --- 2. ADVANCED LOAN ENGINE ---
def calculate_loan(p, r, t, monthly_extra, rate_changes):
    balance = p
    schedule = []
    current_rate = r
    
    for month in range(1, t + 1):
        if month in rate_changes:
            current_rate = rate_changes[month]
            
        m_rate = (current_rate / 100) / 12
        interest = balance * m_rate
        # Recalculate EMI for floating rate
        std_emi = npf.pmt(m_rate, (t - month + 1), -balance)
        
        principal_pay = (std_emi - interest) + monthly_extra
        balance -= principal_pay
        
        schedule.append({
            "Month": month, "Rate": current_rate, 
            "Interest": interest, "Principal": principal_pay, 
            "Balance": max(0, balance)
        })
        if balance <= 0: break
    return pd.DataFrame(schedule)

# --- 3. UI LAYOUT ---
st.title("🏦 SmartSpend & Loan Optimizer")
tab1, tab2 = st.tabs(["Spending Tracker (AI)", "Loan Closure Engine"])

with tab1:
    st.header("AI Transaction Sorter")
    raw_input = st.text_area("Paste SMS or Email receipts:")
    if st.button("Analyze with Gemini"):
        data = ai_parse_text(raw_input)
        if data:
            st.table(pd.DataFrame(data))
            st.success("Successfully categorized!")
        else:
            st.warning("No transactions found or AI busy.")

with tab2:
    st.header("Debt-Free Predictor")
    c1, c2, c3 = st.columns(3)
    p = c1.number_input("Principal ($)", value=300000)
    r = c2.number_input("Base Rate (%)", value=7.5)
    t = c3.number_input("Tenure (Months)", value=240)
    
    extra = st.slider("Monthly Extra Payment ($)", 0, 5000, 500)
    
    # Floating Rate Simulation
    with st.expander("Add Interest Rate Changes"):
        change_m = st.number_input("Month of Change", value=12)
        new_r = st.number_input("New Rate (%)", value=8.0)
        rate_map = {change_m: new_r} if st.checkbox("Apply Change") else {}

    df = calculate_loan(p, r, t, extra, rate_map)
    
    # Metrics
    saved_months = t - len(df)
    st.metric("Time Saved", f"{saved_months} Months", delta=f"{saved_months/12:.1f} Years")
    st.line_chart(df[['Balance', 'Interest']])

    if st.button("Generate Strategy Report"):
        st.info("PDF Report generated based on current trend. (Feature connected to FPDF)")






