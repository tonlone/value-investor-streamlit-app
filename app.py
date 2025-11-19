import streamlit as st
import yfinance as yf
import pandas as pd
from groq import Groq
import time

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
    .multiplier-box {
        font-size: 40px;
        font-weight: bold;
        text-align: center;
        padding: 10px;
        border-radius: 10px;
        background-color: #f9f9f9;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- API KEY SETUP ---
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except (FileNotFoundError, KeyError):
    GROQ_API_KEY = st.sidebar.text_input("Enter Groq API Key", type="password")
    if not GROQ_API_KEY:
        st.warning("⚠️ Please enter a Groq API Key in the sidebar or set it in .streamlit/secrets.toml")
        st.stop()

# Initialize Groq Client
client = Groq(api_key=GROQ_API_KEY)

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

        # 2. Get EPS (Forward or Trailing)
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
    """
    Tries High Quality model first. 
    If Rate Limit (429) is hit, switches to Backup model.
    """
    
    # --- MODEL CONFIGURATION ---
    PRIMARY_MODEL = "llama-3.3-70b-versatile"  # Best Quality (100k Limit)
    BACKUP_MODEL  = "llama-3.1-8b-instant"     # High Speed (500k Limit) - Recommended Backup
    # You can change BACKUP_MODEL to "groq/compound" if you prefer, 
    # but 8b-instant is usually more reliable for this specific task.

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
        # 1. Try Primary Model
        completion = call_ai(PRIMARY_MODEL)
        return completion.choices[0].message.content, False # False = No fallback used
        
    except Exception as e:
        error_msg = str(e)
        # 2. Check for Rate Limit (429)
        if "429" in error_msg or "rate_limit" in error_msg:
            try:
                # 3. Try Backup Model
                completion = call_ai(BACKUP_MODEL)
                return completion.choices[0].message.content, True # True = Fallback used
            except Exception as e2:
                return f"0|Error (Backup Failed): {e2}", True
        else:
            # Genuine other error
            return f"0|Error: {error_msg}", False

# --- SIDEBAR ---
with st.sidebar:
    st.title("⚙️ Analysis Tool")
    
    with st.form(key='search_form'):
        # 1. Market Selection
        market_choice = st.selectbox(
            "Select Market", 
            ["US (NYSE/NASDAQ)", "Canada (TSX)", "Hong Kong (HKEX)"]
        )
        
        # 2. Ticker Input
        raw_ticker = st.text_input("Enter Stock Ticker", value="NVDA", max_chars=8).upper().strip()
        
        analyze_btn = st.form_submit_button("Analyze Stock", type="primary")
    
    st.markdown("---")
    st.info("**Methodology:**\n\nQualitative Score (0-20) \n\n× \n\nValuation Multiplier (1-5) \n\n= **Final Score (0-100)**")

# --- MAIN APP LOGIC ---

if analyze_btn:
    
    # --- TICKER FORMATTING LOGIC ---
    final_ticker = raw_ticker
    
    if market_choice == "Canada (TSX)":
        if ".TO" not in raw_ticker and ".V" not in raw_ticker:
            final_ticker = f"{raw_ticker}.TO"
            
    elif market_choice == "Hong Kong (HKEX)":
        clean_nums = ''.join(filter(str.isdigit, raw_ticker)) 
        if clean_nums:
            final_ticker = f"{clean_nums.zfill(4)}.HK"
        else:
            final_ticker = f"{raw_ticker}.HK"

    with st.spinner(f'🔍 Fetching data for {final_ticker}...'):
        data = get_stock_data(final_ticker)
    
    if data and data['price'] > 0:
        st.header(f"{data['name']} ({final_ticker})")
        st.caption(f"Industry: {data['industry']} | Currency: {data['currency']}")
        
        col1, col2 = st.columns([3, 2])
        
        # --- LEFT COLUMN: QUALITATIVE ANALYSIS ---
        with col1:
            st.subheader("1. Qualitative Analysis")
            
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
                    st.write(f"Analyzing: **{topic}**...")
                    
                    # Call AI with Fallback Logic
                    response, backup_triggered = analyze_qualitative(data['name'], data['summary'], topic)
                    
                    if backup_triggered:
                        used_backup = True
                    
                    try:
                        score_str, explanation = response.split('|', 1)
                        score = int(float(score_str.strip()))
                    except:
                        score = 0
                        explanation = "Could not parse AI response."
                    
                    total_qual_score += score
                    
                    st.markdown(f"**Score: {score}/4** — {explanation.strip()}")
            
            progress_bar.empty()
            st.divider()
            
            # Show indicator if backup model was used
            if used_backup:
                st.warning("⚠️ Daily Rate Limit reached on Primary Model. Switched to Backup Model (Llama-3.1-8b).")
                
            st.markdown(f"### Qualitative Score: :blue[{total_qual_score} / 20]")

        # --- RIGHT COLUMN: QUANTITATIVE VALUATION ---
        with col2:
            st.subheader("2. Quantitative Valuation")
            
            with st.container(border=True):
                st.metric(f"Price ({data['currency']})", f"{data['price']:.2f}")
                st.metric("Forward PE Ratio", f"{data['fwd_pe']:.2f}")
                
                pe = data['fwd_pe']
                
                # Multiplier Logic
                if pe <= 0: multiplier = 1 
                elif pe < 20: multiplier = 5
                elif pe < 35: multiplier = 4
                elif pe < 50: multiplier = 3
                elif pe < 75: multiplier = 2
                else: multiplier = 1
                
                st.divider()
                st.markdown("#### Valuation Multiplier")
                
                html_colors = {
                    5: "#00C805", 4: "#90EE90", 3: "#FFA500", 2: "#FF4500", 1: "#8B0000"
                }
                color_hex = html_colors.get(multiplier, "#333333")
                
                st.markdown(
                    f"""
                    <div class="multiplier-box" style="color: {color_hex}; border: 2px solid {color_hex};">
                        x{multiplier}
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

                if multiplier == 5:
                    st.caption("✅ Undervalued (PE < 20)")
                elif multiplier == 1:
                    st.caption("⚠️ Very Expensive (PE > 75)")
                else:
                    st.caption(f"⚖️ Fair/Premium Valuation (PE ~{int(pe)})")

        # --- FINAL RESULT ---
        st.markdown("---")
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
        <div style="text-align: center; padding: 20px; border: 4px solid {final_color}; border-radius: 15px; background-color: #ffffff;">
            <h2 style="color: #333333; margin:0;">FINAL EVALUATION</h2>
            <h1 style="color: {final_color}; font-size: 80px; margin: 0;">{final_score}</h1>
            <h3 style="color: #333333; margin:0;">{verdict}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.warning("Disclaimer: AI generated analysis. Not financial advice.")
        
    elif analyze_btn:
        st.error(f"Ticker '{final_ticker}' not found. Please check spelling or market selection.")
