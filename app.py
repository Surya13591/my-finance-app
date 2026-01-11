import streamlit as st
import pandas as pd
import numpy_financial as npf
import google.generativeai as genai
import json
from fpdf import FPDF

# --- INITIALIZATION ---
st.set_page_config(page_title="Smart Finance AI 2026", layout="wide")

# Setup API Key safely from Streamlit Secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("🔑 API Key missing! Add GEMINI_API_KEY to your Streamlit Secrets.")

# --- THE AI ENGINE ---
def ai_parse_spendings(text):
    if not text: return []
    try:
        # Using a model loop for maximum reliability across regions
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = """
        Return ONLY a JSON array of transactions. 
        Format: [{"date": "YYYY-MM-DD", "merchant": "name", "amount": 0.00, "category": "category"}]
        Text: """ + text
        
        response = model.generate_content(prompt)
        res_text = response.text.strip()
        
        # Strip markdown if present
        if "```" in res_text:
            res_text = res_text.split("```")[1].replace("json", "").strip()
            
        return json.loads(res_text)
    except Exception as e:
        st.error(f"AI Sync Error: {e}")
        return []

# --- THE LOAN ENGINE ---
def run_loan_simulation(p, r, t, extra, rate_changes):
    balance = p
    data = []
    curr_r = r
    for m in range(1, t + 1):
        if m in rate_changes: curr_r = rate_changes[m]
        m_rate = (curr_r / 100) / 12
        interest = balance * m_rate
        # Calculate standard EMI for the remaining term
        emi = npf.pmt(m_rate, (t - m + 1), -balance)
        principal_part = (emi - interest) + extra
        balance -= principal_part
        data.append({"Month": m, "Interest": interest, "Balance": max(0, balance)})
        if balance <= 0: break
    return pd.DataFrame(data)

# --- THE UI ---
st.title("💰 AI Wealth & Loan Strategist")
st.markdown("---")

tab1, tab2 = st.tabs(["📊 Expense Analyzer", "🏠 Loan Optimization"])

with tab1:
    st.header("AI Receipt & SMS Parser")
    txt = st.text_area("Paste your bank alerts or email receipts here:", height=150)
    if st.button("Generate Expense Table"):
        with st.spinner("Gemini is analyzing..."):
            results = ai_parse_spendings(txt)
            if results:
                df_spend = pd.DataFrame(results)
                st.dataframe(df_spend, use_container_width=True)
                csv = df_spend.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download CSV", csv, "expenses.csv", "text/csv")
            else:
                st.warning("No transactions detected. Try pasting a clear bank alert.")

with tab2:
    st.header("Debt-Free Roadmap")
    c1, c2, c3 = st.columns(3)
    principal = c1.number_input("Loan Amount ($)", value=250000)
    rate = c2.number_input("Interest Rate (%)", value=6.5)
    term = c3.number_input("Term (Months)", value=360)
    
    extra_pay = st.slider("Monthly Prepayment ($)", 0, 5000, 500)
    
    # Simulating Floating Rate
    rate_map = {}
    with st.expander("Configure Floating Rates"):
        m_change = st.number_input("Month of Change", 1, term, 12)
        new_rate = st.number_input("New Rate (%)", 0.0, 20.0, 7.5)
        if st.button("Apply Rate Change"):
            rate_map[m_change] = new_rate
            st.success(f"Rate will change to {new_rate}% at month {m_change}")

    loan_df = run_loan_simulation(principal, rate, term, extra_pay, rate_map)
    
    # Results Metrics
    months_saved = term - len(loan_df)
    st.metric("Time Saved", f"{months_saved} Months", f"{months_saved/12:.1f} Years Early")
    st.line_chart(loan_df.set_index("Month")["Balance"])
    
    st.info("💡 Tip: Increasing your prepayment by just $100 can save thousands in interest.")

st.markdown("---")
st.caption("© 2026 AI Finance Hub | Powered by Google Gemini 3")
