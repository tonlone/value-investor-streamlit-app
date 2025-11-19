import streamlit as st
import yfinance as yf
import pandas as pd
from groq import Groq

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
    .stProgress > div > div > div > div {
        background-image: linear-gradient(to right, #ff4b4b, #ffa500, #21c354);
    }
</style>
""", unsafe_allow_html=True)

# --- API KEY SETUP (FROM SECRETS) ---
try:
    # This pulls the key securely from your Streamlit Cloud settings
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except FileNotFoundError:
    st.error("⚠️ Secret 'GROQ_API_KEY' not found. Please add it to your Streamlit Secrets.")
    st.stop()
except KeyError:
    st.error("⚠️ Secret 'GROQ_API_KEY' not found. Please add it to your Streamlit Secrets.")
    st.stop()

# Initialize Groq Client
client = Groq(api_key=GROQ_API_KEY)

# --- FUNCTIONS ---

def get_stock_data(ticker):
    """Fetches financial data using yfinance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # If stock info is empty, ticker might be wrong
        if not info:
            return None

        current_price = info.get('currentPrice', 0)
        if current_price == 0:
            # Try to get price from history if currentPrice is missing
            hist = stock.history(period="1d")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]

        eps_fwd = info.get('forwardEps', 1)
        if eps_fwd is None: eps_fwd = 1 
        
        # Calculate Forward PE
        fwd_pe = current_price / eps_fwd if eps_fwd > 0 else 0
        
        return {
            "price": current_price,
            "fwd_pe": fwd_pe,
            "eps_fwd": eps_fwd,
            "name": info.get('longName', ticker),
            "industry": info.get('industry', 'Unknown'),
            "summary": info.get('longBusinessSummary', 'No summary available.')
        }
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

def analyze_qualitative(ticker, summary, topic):
    """Uses Groq Llama 3.3 to rate specific qualitative aspects 0-4"""
    prompt = f"""
    You are a strict Value Investor (Warren Buffett style). Analyze {ticker}.
    Context: {summary}
    
    Topic: {topic}
    
    Task:
    1. Give a score from 0 to 4 integers only (0=Terrible/No Moat, 4=Excellent/Monopoly).
    2. Provide a 1-sentence explanation focusing on competitive advantage (Moat).
    
    Format: SCORE|EXPLANATION
    Example: 4|Nvidia has a near-monopoly in AI chips with CUDA lock-in.
    """
    
    try:
        completion = client.chat.completions.create(
            # UPDATED MODEL: The old one was decommissioned. 
            # Using Llama 3.3 70B which is currently the best/fastest on Groq.
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=100
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"0|Error analyzing: {e}"

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Analysis Tool")
    ticker_input = st.text_input("Enter US Stock Ticker", value="NVDA", max_chars=5).upper()
    analyze_btn = st.button("Analyze Stock", type="primary")
    
    st.markdown("---")
    st.caption("✅ API Key loaded from Secrets")
    st.info("**Methodology:**\n\nQualitative Score (0-20) \n\n× \n\nValuation Multiplier (1-5) \n\n= **Final Score (0-100)**")

# --- MAIN APP LOGIC ---

if analyze_btn:
    with st.spinner(f'🔍 Fetching financial data for {ticker_input}...'):
        data = get_stock_data(ticker_input)
    
    if data and data['price'] > 0:
        st.header(f"{data['name']} ({ticker_input})")
        st.caption(f"Industry: {data['industry']}")
        
        col1, col2 = st.columns([3, 2])
        
        # --- LEFT COLUMN: QUALITATIVE ANALYSIS ---
        with col1:
            st.subheader("1. Qualitative Analysis (The Business)")
            
            topics = [
                "Selling Unique Products/Services (Hard to replicate?)",
                "Long-term Revenue Growth Potential",
                "Competitive Advantage (Moat & Market Leader?)",
                "Profitability & Margins",
                "Management Quality & Allocation"
            ]
            
            total_qual_score = 0
            progress_bar = st.progress(0)
            
            for i, topic in enumerate(topics):
                # Update progress bar
                progress_bar.progress((i) / len(topics))
                
                with st.chat_message("assistant", avatar="🤖"):
                    st.write(f"Analyzing: **{topic}**...")
                    response = analyze_qualitative(ticker_input, data['summary'], topic)
                    
                    try:
                        score_str, explanation = response.split('|', 1)
                        score = int(float(score_str.strip()))
                    except:
                        score = 0
                        explanation = "Could not parse AI response."
                    
                    total_qual_score += score
                    
                    # Display Result
                    st.markdown(f"**Score: {score}/4** — {explanation.strip()}")
            
            progress_bar.empty()
            st.divider()
            st.markdown(f"### Qualitative Score: :blue[{total_qual_score} / 20]")

        # --- RIGHT COLUMN: QUANTITATIVE VALUATION ---
        with col2:
            st.subheader("2. Quantitative Valuation")
            
            with st.container(border=True):
                st.metric("Current Price", f"${data['price']:.2f}")
                st.metric("Forward PE Ratio", f"{data['fwd_pe']:.2f}")
                
                # --- Valuation Logic ---
                pe = data['fwd_pe']
                
                # Dynamic Logic: 
                # < 20 PE = x5
                # 20-35 PE = x4
                # 35-50 PE = x3
                # 50-75 PE = x2
                # > 75 PE = x1
                
                if pe <= 0: multiplier = 1 # Negative earnings
                elif pe < 20: multiplier = 5
                elif pe < 35: multiplier = 4
                elif pe < 50: multiplier = 3
                elif pe < 75: multiplier = 2
                else: multiplier = 1
                
                st.divider()
                st.markdown("#### Valuation Multiplier")
                
                color_map = {5: "green", 4: "lightgreen", 3: "orange", 2: "red", 1: "darkred"}
                
                st.markdown(f"### :{color_map[multiplier]}[x{multiplier}]")
                
                if multiplier == 5:
                    st.caption("Stock is Cheap (PE < 20)")
                elif multiplier == 1:
                    st.caption("Stock is Very Expensive (PE > 75)")
                else:
                    st.caption(f"Fair/Premium Valuation (PE ~{int(pe)})")

        # --- FINAL RESULT ---
        st.markdown("---")
        final_score = total_qual_score * multiplier
        
        # Determine Color and Verdict
        if final_score >= 75:
            verdict = "STRONG BUY 🚀"
            final_color = "#00C805" # Green
        elif final_score >= 45:
            verdict = "HOLD / WATCH 👀"
            final_color = "#FFA500" # Orange
        else:
            verdict = "AVOID / SELL 🔻"
            final_color = "#FF0000" # Red

        st.markdown(f"""
        <div style="text-align: center; padding: 20px; border: 2px solid {final_color}; border-radius: 15px;">
            <h2>FINAL SCORE</h2>
            <h1 style="color: {final_color}; font-size: 80px; margin: 0;">{final_score}</h1>
            <h3>{verdict}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.warning("Disclaimer: AI generated analysis. Not financial advice.")
        
    elif analyze_btn:
        st.error("Ticker not found or data unavailable. Please check the spelling (e.g., AAPL, TSLA).")
