import streamlit as st
import yfinance as yf
from groq import Groq

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Value Investor Pro", layout="wide", page_icon="📈")

# --- CSS STYLING ---
st.markdown("""
<style>
    /* 1. Multiplier Box Style */
    .multiplier-box {
        font-size: 30px;
        font-weight: bold;
        text-align: center;
        padding: 10px;
        border-radius: 10px;
        background-color: #f9f9f9;
        margin-top: 10px;
    }
    
    /* 2. Final Score Box Style */
    .final-score-box {
        text-align: center; 
        padding: 20px; 
        border-radius: 15px; 
        background-color: #ffffff; 
        margin-top: 20px;
        border: 4px solid #ccc;
    }

    /* 3. Custom RED Button Styling for Desktop Sidebar */
    div[data-testid="stForm"] button[kind="primary"] {
        background-color: #FF4B4B;
        color: white;
        border: none;
        font-weight: bold;
        font-size: 16px;
        padding: 0.5rem 1rem;
        width: 100%;
    }
    div[data-testid="stForm"] button[kind="primary"]:hover {
        background-color: #FF0000;
        border-color: #FF0000;
    }
</style>
""", unsafe_allow_html=True)

# --- API KEY SETUP ---
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except (FileNotFoundError, KeyError):
    GROQ_API_KEY = st.sidebar.text_input("Enter Groq API Key", type="password")
    if not GROQ_API_KEY:
        st.warning("⚠️ Please enter a Groq API Key in the sidebar.")
        st.stop()

client = Groq(api_key=GROQ_API_KEY)

# --- FUNCTIONS ---

def get_stock_data(ticker):
    """Fetches financial data from Yahoo Finance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if not info: return None
        
        # Get Price
        price = info.get('currentPrice', 0)
        if price == 0:
            hist = stock.history(period="1d")
            if not hist.empty: price = hist['Close'].iloc[-1]

        # Get EPS
        eps = info.get('forwardEps', info.get('trailingEps', 0))
        
        # Calc PE
        pe = price / eps if eps and eps > 0 else 0
        
        return {
            "price": price,
            "currency": info.get('currency', 'USD'),
            "pe": pe,
            "name": info.get('longName', ticker),
            "industry": info.get('industry', 'Unknown'),
            "summary": info.get('longBusinessSummary', '')
        }
    except: return None

def analyze_qualitative(ticker, summary, topic):
    """
    Primary: Llama-3.3-70b (Best Reasoning/Cost Balance)
    Backup:  Llama-3.1-8b (Cheapest: $0.05/1M tokens)
    """
    PRIMARY_MODEL = "llama-3.3-70b-versatile" 
    BACKUP_MODEL  = "llama-3.1-8b-instant"    

    # UPDATED PROMPT: Asks for decimals (e.g., 3.5)
    prompt = f"""
    Analyze {ticker} regarding '{topic}'. Context: {summary}. 
    Give a specific score from 0.0 to 4.0 (use 1 decimal place, e.g., 3.5 or 2.8).
    Provide a 1 sentence reason.
    Format: SCORE|REASON
    """
    
    try:
        resp = client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[{"role": "user", "content": prompt}], temperature=0.1, max_tokens=100
        )
        return resp.choices[0].message.content, False
    except:
        try: 
            resp = client.chat.completions.create(
                model=BACKUP_MODEL, 
                messages=[{"role": "user", "content": prompt}], temperature=0.1, max_tokens=100
            )
            return resp.choices[0].message.content, True
        except: return "0.0|Error", True

# --- HYBRID INPUT LOGIC ---

if 'layout_mode' not in st.session_state: st.session_state.layout_mode = 'desktop' 
if 'active_ticker' not in st.session_state: st.session_state.active_ticker = "NVDA"
if 'active_market' not in st.session_state: st.session_state.active_market = "US"

# 1. DESKTOP SIDEBAR (With RED Button)
with st.sidebar:
    st.header("Analysis Tool")
    with st.form(key='desktop_form'):
        st.write("Select Market")
        d_market = st.selectbox("Market", ["US", "Canada (TSX)", "HK (HKEX)"], label_visibility="collapsed")
        st.write("Enter Stock Ticker")
        d_ticker = st.text_input("Ticker", value="NVDA", label_visibility="collapsed").upper()
        d_submit = st.form_submit_button("Analyze Stock", type="primary") 
    
    st.markdown("---")
    st.caption("Precision Mode: Enabled (Decimals)")

# 2. MOBILE EXPANDER
with st.expander("📱 Tap here for Mobile Search", expanded=False):
    with st.form(key='mobile_form'):
        m_col1, m_col2 = st.columns([1, 1])
        with m_col1:
            m_market = st.selectbox("Market", ["US", "Canada (TSX)", "HK (HKEX)"], key='m_m')
        with m_col2:
            m_ticker = st.text_input("Ticker", value="NVDA", key='m_t').upper()
        m_submit = st.form_submit_button("Analyze (Mobile)", type="primary")

# --- PROCESSING LOGIC ---
run_analysis = False

if d_submit:
    st.session_state.layout_mode = 'desktop'
    st.session_state.active_ticker = d_ticker
    st.session_state.active_market = d_market
    run_analysis = True
elif m_submit:
    st.session_state.layout_mode = 'mobile'
    st.session_state.active_ticker = m_ticker
    st.session_state.active_market = m_market
    run_analysis = True

# --- MAIN EXECUTION ---

if run_analysis:
    
    # Ticker Clean Up
    raw_t = st.session_state.active_ticker
    mkt = st.session_state.active_market
    final_t = raw_t
    
    if mkt == "Canada (TSX)" and ".TO" not in raw_t: final_t += ".TO"
    elif mkt == "HK (HKEX)": 
        nums = ''.join(filter(str.isdigit, raw_t))
        if nums: final_t = f"{nums.zfill(4)}.HK"
        else: final_t += ".HK"

    with st.spinner(f"Analyzing {final_t}..."):
        data = get_stock_data(final_t)

    if data:
        st.header(f"{data['name']} ({final_t})")
        st.caption(f"Industry: {data['industry']} | Currency: {data['currency']}")

        # Run Analysis
        topics = ["Unique Product/Moat", "Revenue Growth", "Competitive Advantage", "Profit Stability", "Management"]
        qual_results = []
        total_qual = 0.0 # Float now
        backup_used = False
        
        progress = st.progress(0)
        for i, t in enumerate(topics):
            progress.progress((i)/5)
            res, is_backup = analyze_qualitative(data['name'], data['summary'], t)
            if is_backup: backup_used = True
            
            try: 
                s, r = res.split('|', 1)
                s = float(s.strip()) # Parse as decimal
            except: s, r = 0.0, "Error parsing AI"
            
            total_qual += s
            qual_results.append((t, s, r))
        progress.empty()

        # --- NEW DECIMAL VALUATION LOGIC (Linear Interpolation) ---
        pe = data['pe']
        
        if pe <= 0: 
            mult = 1.0
            color_code = "#8B0000"
        elif pe <= 20: 
            mult = 5.0
            color_code = "#00C805" # Green
        elif pe >= 75: 
            mult = 1.0
            color_code = "#8B0000" # Dark Red
        else:
            # Linear Interpolation between PE 20 and PE 75
            # Range = 55 points (75 - 20)
            # Slope: Multiplier drops from 5 to 1 (Difference of 4)
            pct = (pe - 20) / 55
            mult = 5.0 - (pct * 4.0)
            
            # Determine color based on the calculated multiplier
            if mult >= 4.0: color_code = "#00C805" # Green
            elif mult >= 3.0: color_code = "#90EE90" # Light Green
            elif mult >=
