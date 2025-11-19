import streamlit as st
import yfinance as yf
import pandas as pd
from groq import Groq
import math

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Value Investor Pro AI", layout="wide", page_icon="📈")

# --- CSS FOR STYLING ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 10px;
    }
    .score-high { color: #00C805; font-weight: bold; }
    .score-med { color: #FFA500; font-weight: bold; }
    .score-low { color: #FF0000; font-weight: bold; }
    .big-score { font-size: 48px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR SETUP ---
with st.sidebar:
    st.title("⚙️ Settings")
    groq_api_key = st.text_input("Enter Groq API Key", type="password", help="Get one for free at console.groq.com")
    st.markdown("---")
    ticker_input = st.text_input("Enter US Stock Ticker", value="NVDA").upper()
    analyze_btn = st.button("Analyze Stock", type="primary")
    st.info("Methodology: Qualitative Analysis (0-20) x Valuation Multiplier (1-5) = Final Score (0-100).")

# --- FUNCTIONS ---

def get_stock_data(ticker):
    """Fetches financial data using yfinance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get history for PE calculation
        hist = stock.history(period="5y")
        
        current_price = info.get('currentPrice', 0)
        eps_fwd = info.get('forwardEps', 1)
        if eps_fwd is None: eps_fwd = 1 # Avoid div by zero
        
        fwd_pe = current_price / eps_fwd if eps_fwd > 0 else 0
        
        # Calculate generic historical PE range (Approximation using Close / Trailing EPS estimate)
        # Note: Accurate historical PE requires expensive data, we will approximate using price action
        # relative to earnings growth for the demo.
        
        return {
            "price": current_price,
            "fwd_pe": fwd_pe,
            "eps_fwd": eps_fwd,
            "name": info.get('longName', ticker),
            "industry": info.get('industry', 'Unknown'),
            "summary": info.get('longBusinessSummary', '')
        }
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

def analyze_qualitative(client, ticker, summary, topic):
    """Uses AI to rate specific qualitative aspects 0-4"""
    prompt = f"""
    You are a strict Value Investor. Analyze {ticker}.
    Context: {summary}
    
    Topic: {topic}
    
    Task:
    1. Give a score from 0 to 4 integers only (0=Terrible, 4=Excellent/Monopoly).
    2. Provide a 2-sentence explanation focusing on competitive advantage (Moat).
    
    Format: SCORE|EXPLANATION
    Example: 4|Nvidia has a near-monopoly in AI chips with CUDA lock-in.
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama3-70b-8192", # High quality, fast, free on Groq
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"0|Error analyzing: {e}"

# --- MAIN APP LOGIC ---

if analyze_btn and groq_api_key:
    client = Groq(api_key=groq_api_key)
    
    with st.spinner(f'Fetching data for {ticker_input}...'):
        data = get_stock_data(ticker_input)
    
    if data:
        st.header(f"{data['name']} ({ticker_input})")
        
        col1, col2 = st.columns([3, 2])
        
        # --- LEFT COLUMN: QUALITATIVE ANALYSIS ---
        with col1:
            st.subheader("1. Qualitative Analysis (Business Moat)")
            st.caption("Based on Warren Buffett / Fisher principles (0-4 points each)")
            
            topics = [
                "Selling Unique Products/Services (Is it hard to replicate?)",
                "Long-term Revenue Growth (Is it >20% CAGR?)",
                "Competitive Advantage (Market Leader?)",
                "High Gross Margins & Profitability",
                "Management & Capital Allocation"
            ]
            
            total_qual_score = 0
            
            for i, topic in enumerate(topics):
                with st.spinner(f"Analyzing {topic}..."):
                    response = analyze_qualitative(client, ticker_input, data['summary'], topic)
                    
                try:
                    score_str, explanation = response.split('|', 1)
                    score = int(float(score_str.strip()))
                except:
                    score = 0
                    explanation = "AI Parse Error."
                
                total_qual_score += score
                
                # UI for the item
                st.markdown(f"**{i+1}. {topic}**")
                st.progress(score / 4)
                st.markdown(f"**Score: {score}/4** - *{explanation.strip()}*")
                st.divider()

            st.markdown(f"### Qualitative Score: :blue[{total_qual_score} / 20]")

        # --- RIGHT COLUMN: QUANTITATIVE VALUATION ---
        with col2:
            st.subheader("2. Quantitative Valuation")
            st.caption("Setting the Multiplier based on Price/Earnings")
            
            with st.container(border=True):
                st.metric("Current Price", f"${data['price']:.2f}")
                st.metric("Forward PE Ratio", f"{data['fwd_pe']:.2f}")
                st.metric("Est. Future EPS", f"{data['eps_fwd']:.2f}")
                
                # --- Valuation Logic (Simplified Fireman Logic) ---
                # Rule: 
                # PE < 20 -> x5 (Cheap)
                # PE 20-35 -> x4 (Fair)
                # PE 35-50 -> x3 (Expensive)
                # PE 50-75 -> x2 (Very Expensive)
                # PE > 75 -> x1 (Bubble)
                
                pe = data['fwd_pe']
                if pe < 20: multiplier = 5
                elif pe < 35: multiplier = 4
                elif pe < 50: multiplier = 3
                elif pe < 75: multiplier = 2
                else: multiplier = 1
                
                st.markdown("#### Valuation Multiplier")
                
                # Visual representation of multiplier
                colors = ["red", "orange", "gold", "lightgreen", "green"]
                st.markdown(f"### :green[x{multiplier}]")
                
                st.info(f"Based on a Forward PE of {pe:.1f}, the valuation multiplier is set to x{multiplier}.")

        # --- BOTTOM SECTION: FINAL RESULT ---
        st.markdown("---")
        st.subheader("Evaluation Result")
        
        final_score = total_qual_score * multiplier
        
        res_col1, res_col2, res_col3 = st.columns(3)
        
        with res_col1:
             st.markdown("### Qualitative")
             st.markdown(f"# {total_qual_score}")
        
        with res_col2:
             st.markdown("### Multiplier")
             st.markdown(f"# x{multiplier}")
             
        with res_col3:
             color = "green" if final_score >= 75 else "orange" if final_score >= 45 else "red"
             verdict = "STRONG BUY" if final_score >= 75 else "HOLD" if final_score >= 45 else "AVOID"
             
             st.markdown("### Final Score")
             st.markdown(f"<span style='color:{color}; font-size: 60px; font-weight:bold'>{final_score}</span>", unsafe_allow_html=True)
             st.markdown(f"**Verdict: {verdict}**")
             
        # Disclaimer
        st.warning("Disclaimer: This is an AI-generated analysis for educational purposes. Not financial advice.")

elif analyze_btn and not groq_api_key:
    st.error("Please enter a Groq API Key in the sidebar.")
