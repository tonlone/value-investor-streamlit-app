import streamlit as st
import yfinance as yf
import pandas as pd
from groq import Groq
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Value Investor Pro AI", layout="wide", page_icon="📈")

# --- CSS FOR STYLING (MOBILE OPTIMIZED) ---
st.markdown("""
<style>
    /* Make the final score box responsive */
    .final-score-box {
        text-align: center; 
        padding: 20px; 
        border-radius: 15px; 
        background-color: #ffffff;
        margin-top: 20px;
    }
    .multiplier-box {
        font-size: 30px; /* Slightly smaller for mobile */
        font-weight: bold;
        text-align: center;
        padding: 10px;
        border-radius: 10px;
        background-color: #f9f9f9;
        margin-top: 10px;
    }
    /* Adjust font sizes for mobile screens */
    @media only screen and (max-width: 600px) {
        h1 { font-size: 24px !important; }
        h2 { font-size: 20px !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR (SETTINGS ONLY) ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Key Input (Hidden in sidebar)
    try:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
        st.success("API Key loaded from Secrets")
    except (FileNotFoundError, KeyError):
        GROQ_API_KEY = st.text_input("Enter Groq API Key", type="password")
        if not GROQ_API_KEY:
            st.warning("Please enter API Key to proceed.")
    
    st.markdown("---")
    with st.expander("ℹ️ How it works"):
        st.info("**Methodology:**\n\nQualitative Score (0-20) \n\n× \n\nValuation Multiplier (1-5) \n\n= **Final Score (0-100)**")
        st.write("1. AI reads company summaries.")
        st.write("2. AI rates 5 criteria (0-4).")
        st.write("3. Algorithm calculates PE ratio position.")

# Initialize Groq Client
if GROQ_API_KEY:
    client = Groq(api_key=GROQ_API_KEY)
else:
    st.stop() # Stop app if no key

# --- FUNCTIONS ---

def get_stock_data(ticker):
    """Fetches financial data using yfinance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if not info:
            return None

        # 1. Get Price
        current_price = info.get('currentPrice', 0)
        if current_price == 0:
            hist = stock.history(period="1d")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]

        # 2. Get EPS
        eps_fwd = info.get('forwardEps', 0)
        if eps_fwd is None or eps_fwd == 0: 
            eps_fwd = info.get('trailingEps', 0) 
        
        # 3. Calculate PE
        fwd_pe = current_price / eps_fwd if eps_fwd and eps_fwd > 0 else 0
        
        return {
            "price": current_price,
            "currency": info.get('currency', 'USD'),
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
    """Tries High Quality model first, falls back to backup."""
    PRIMARY_MODEL = "llama-3.3-70b-versatile"
    BACKUP_MODEL  = "llama-3.1-8b-instant"

    prompt = f"""
    You are a strict Value Investor. Analyze {ticker}.
    Context: {summary}
    Topic: {topic}
    Task:
    1. Give a score from 0 to 4 integers only (0=Terrible, 4=Excellent).
    2. Provide a 1-sentence explanation.
    Format: SCORE|EXPLANATION
    """
    
    def call_ai(model_name):
        return client.chat.completions.create(
            model=model_name, 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=100
        )

    try:
        completion = call_ai(PRIMARY_MODEL)
        return completion.choices[0].message.content, False
    except Exception as e:
        if "429" in str(e) or "rate_limit" in str(e):
            try:
                completion = call_ai(BACKUP_MODEL)
                return completion.choices[0].message.content, True
            except Exception as e2:
                return f"0|Error (Backup Failed): {e2}", True
        else:
            return f"0|Error: {str(e)}", False

# --- MAIN PAGE LAYOUT ---

st.title("📈 Value Investor Pro")
st.write("AI-Powered Stock Analysis based on FIREman Methodology")

# --- INPUT FORM (MOVED TO MAIN PAGE) ---
# This ensures it is visible on mobile immediately
with st.container(border=True):
    with st.form(key='search_form'):
        c1, c2 = st.columns([1, 1])
        
        with c1:
            market_choice = st.selectbox(
                "Market", 
                ["US", "Canada (TSX)", "HK (HKEX)"]
            )
        with c2:
            raw_ticker = st.text_input("Ticker", value="NVDA").upper().strip()
        
        analyze_btn = st.form_submit_button("Analyze Stock", type="primary", use_container_width=True)

# --- ANALYSIS LOGIC ---

if analyze_btn:
    
    # Ticker Formatting
    final_ticker = raw_ticker
    if market_choice == "Canada (TSX)":
        if ".TO" not in raw_ticker and ".V" not in raw_ticker:
            final_ticker = f"{raw_ticker}.TO"
    elif market_choice == "HK (HKEX)":
        clean_nums = ''.join(filter(str.isdigit, raw_ticker)) 
        if clean_nums:
            final_ticker = f"{clean_nums.zfill(4)}.HK"
        else:
            final_ticker = f"{raw_ticker}.HK"

    with st.spinner(f'🔍 Analyzing {final_ticker}...'):
        data = get_stock_data(final_ticker)
    
    if data and data['price'] > 0:
        st.header(f"{data['name']}")
        st.caption(f"{final_ticker} | {data['industry']} | {data['currency']}")
        
        # Create tabs for better mobile organization
        tab1, tab2, tab3 = st.tabs(["1. Business (AI)", "2. Valuation", "3. Verdict"])
        
        # --- TAB 1: QUALITATIVE ---
        with tab1:
            topics = [
                "Unique Product/Service (Moat)",
                "Revenue Growth Potential",
                "Competitive Advantage",
                "Profit Stability",
                "Management & Allocation"
            ]
            
            total_qual_score = 0
            used_backup = False
            progress_bar = st.progress(0)
            
            for i, topic in enumerate(topics):
                progress_bar.progress((i) / len(topics))
                with st.chat_message("assistant", avatar="🤖"):
                    st.write(f"**{topic}**")
                    response, backup_triggered = analyze_qualitative(data['name'], data['summary'], topic)
                    if backup_triggered: used_backup = True
                    
                    try:
                        score_str, explanation = response.split('|', 1)
                        score = int(float(score_str.strip()))
                    except:
                        score = 0
                        explanation = "AI Error"
                    
                    total_qual_score += score
                    st.write(f"⭐ **{score}/4**")
                    st.caption(explanation.strip())
            
            progress_bar.empty()
            if used_backup:
                st.toast("Used backup AI model due to high traffic.", icon="⚠️")
                
            st.info(f"Qualitative Score: **{total_qual_score} / 20**")

        # --- TAB 2: QUANTITATIVE ---
        with tab2:
            c_a, c_b = st.columns(2)
            c_a.metric("Price", f"{data['price']:.2f}")
            c_b.metric("PE Ratio", f"{data['fwd_pe']:.2f}")
            
            pe = data['fwd_pe']
            if pe <= 0: multiplier = 1 
            elif pe < 20: multiplier = 5
            elif pe < 35: multiplier = 4
            elif pe < 50: multiplier = 3
            elif pe < 75: multiplier = 2
            else: multiplier = 1
            
            html_colors = {5: "#00C805", 4: "#90EE90", 3: "#FFA500", 2: "#FF4500", 1: "#8B0000"}
            color_hex = html_colors.get(multiplier, "#333333")
            
            st.markdown(f"""
                <div class="multiplier-box" style="color: {color_hex}; border: 2px solid {color_hex};">
                    x{multiplier} Multiplier
                </div>
            """, unsafe_allow_html=True)
            
            if multiplier == 5: st.caption("✅ Undervalued")
            elif multiplier == 1: st.caption("⚠️ Expensive")
            else: st.caption("⚖️ Fair Value")

        # --- TAB 3: VERDICT ---
        with tab3:
            final_score = total_qual_score * multiplier
            
            if final_score >= 75:
                verdict = "STRONG BUY 🚀"
                final_color = "#00C805"
            elif final_score >= 45:
                verdict = "HOLD / WATCH 👀"
                final_color = "#FFA500"
            else:
                verdict = "AVOID / SELL 🔻"
                final_color = "#FF0000"

            st.markdown(f"""
            <div class="final-score-box" style="border: 4px solid {final_color};">
                <h2 style="color: #333333; margin:0; font-size: 20px;">FINAL SCORE</h2>
                <h1 style="color: {final_color}; font-size: 60px; margin: 0;">{final_score}</h1>
                <h3 style="color: #333333; margin:0; font-size: 18px;">{verdict}</h3>
            </div>
            """, unsafe_allow_html=True)
            
            st.warning("Not financial advice.")

    elif analyze_btn:
        st.error(f"Ticker '{final_ticker}' not found.")
