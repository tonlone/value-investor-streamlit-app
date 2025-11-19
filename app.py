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
    /* This ensures the button looks like the original "Red" button */
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
    # --- MODEL SELECTION BASED ON YOUR REQUEST ---
    PRIMARY_MODEL = "llama-3.3-70b-versatile" 
    BACKUP_MODEL  = "llama-3.1-8b-instant"    

    prompt = f"Analyze {ticker} regarding '{topic}'. Context: {summary}. Give a score (0-4) and 1 sentence reason. Format: SCORE|REASON"
    
    try:
        # Try Primary
        resp = client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[{"role": "user", "content": prompt}], temperature=0.1, max_tokens=100
        )
        return resp.choices[0].message.content, False
    except:
        try: 
            # Try Backup (Cheapest)
            resp = client.chat.completions.create(
                model=BACKUP_MODEL, 
                messages=[{"role": "user", "content": prompt}], temperature=0.1, max_tokens=100
            )
            return resp.choices[0].message.content, True
        except: return "0|Error", True

# --- HYBRID INPUT LOGIC ---

# Session State to track which view to show
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
        
        # type="primary" makes it RED
        d_submit = st.form_submit_button("Analyze Stock", type="primary") 
    
    st.markdown("---")
    st.caption("Primary Model: Llama 3.3 70B\nBackup Model: Llama 3.1 8B")

# 2. MOBILE EXPANDER (Hidden on desktop usually, first thing on mobile)
with st.expander("📱 Tap here for Mobile Search", expanded=False):
    with st.form(key='mobile_form'):
        m_col1, m_col2 = st.columns([1, 1])
        with m_col1:
            m_market = st.selectbox("Market", ["US", "Canada (TSX)", "HK (HKEX)"], key='m_m')
        with m_col2:
            m_ticker = st.text_input("Ticker", value="NVDA", key='m_t').upper()
        # Also RED button
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
        # Heading
        st.header(f"{data['name']} ({final_t})")
        st.caption(f"Industry: {data['industry']} | Currency: {data['currency']}")

        # Run Analysis (Shared for both layouts)
        topics = ["Unique Product/Moat", "Revenue Growth", "Competitive Advantage", "Profit Stability", "Management"]
        qual_results = []
        total_qual = 0
        backup_used = False
        
        progress = st.progress(0)
        for i, t in enumerate(topics):
            progress.progress((i)/5)
            # AI Call
            res, is_backup = analyze_qualitative(data['name'], data['summary'], t)
            if is_backup: backup_used = True
            
            try: 
                s, r = res.split('|', 1)
                s = int(float(s))
            except: s, r = 0, "Error parsing AI"
            total_qual += s
            qual_results.append((t, s, r))
        progress.empty()

        # Valuation Math
        pe = data['pe']
        if pe <= 0: mult, color_code = 1, "#8B0000"
        elif pe < 20: mult, color_code = 5, "#00C805"
        elif pe < 35: mult, color_code = 4, "#90EE90"
        elif pe < 50: mult, color_code = 3, "#FFA500"
        elif pe < 75: mult, color_code = 2, "#FF4500"
        else: mult, color_code = 1, "#8B0000"

        final_score = total_qual * mult
        
        if backup_used:
            st.toast("High traffic: Used Backup Model (Llama-3.1-8B)", icon="⚠️")

        # --- VIEW A: DESKTOP (COLUMNS + CARDS) ---
        if st.session_state.layout_mode == 'desktop':
            
            col1, col2 = st.columns([1.5, 1])
            
            with col1:
                st.subheader("1. Qualitative Analysis")
                for item in qual_results:
                    # Original clean look
                    st.markdown(f"**{item[0]}**")
                    st.progress(item[1]/4)
                    st.caption(f"**{item[1]}/4** — {item[2]}")
                    st.divider()
                st.info(f"Total Qualitative Score: {total_qual} / 20")

            with col2:
                st.subheader("2. Valuation")
                with st.container(border=True):
                    st.metric(f"Price ({data['currency']})", f"{data['price']:.2f}")
                    st.metric("Forward PE", f"{pe:.2f}")
                    st.markdown("#### Valuation Multiplier")
                    st.markdown(f"<div class='multiplier-box' style='color:{color_code}; border:2px solid {color_code}'>x{mult}</div>", unsafe_allow_html=True)
                    if mult == 5: st.caption("✅ Undervalued")
                    elif mult == 1: st.caption("⚠️ Expensive")
            
            # Desktop Final Verdict
            st.divider()
            verdict_color = "#00C805" if final_score >= 75 else "#FFA500" if final_score >= 45 else "#FF0000"
            st.markdown(f"""
            <div class="final-score-box" style="border-color: {verdict_color};">
                <h2 style="color:#333; margin:0;">FINAL SCORE</h2>
                <h1 style="color: {verdict_color}; font-size: 80px; margin:0;">{final_score}</h1>
            </div>
            """, unsafe_allow_html=True)

        # --- VIEW B: MOBILE (TABS) ---
        else:
            
            tab1, tab2, tab3 = st.tabs(["🏢 Business", "💰 Value", "🏁 Verdict"])
            
            with tab1:
                st.info(f"Quality Score: **{total_qual}/20**")
                for item in qual_results:
                    with st.chat_message("assistant", avatar="🤖"):
                        st.write(f"**{item[0]}**")
                        st.write(f"⭐ {item[1]}/4")
                        st.caption(item[2])

            with tab2:
                c1, c2 = st.columns(2)
                c1.metric("Price", f"{data['price']:.0f}")
                c2.metric("PE", f"{pe:.1f}")
                st.markdown(f"<div class='multiplier-box' style='color:{color_code}; border:2px solid {color_code}'>x{mult}</div>", unsafe_allow_html=True)

            with tab3:
                verdict_color = "#00C805" if final_score >= 75 else "#FFA500" if final_score >= 45 else "#FF0000"
                verdict_txt = "BUY" if final_score >= 75 else "HOLD" if final_score >= 45 else "SELL"
                st.markdown(f"""
                <div class="final-score-box" style="border-color: {verdict_color};">
                    <h1 style="color: {verdict_color}; font-size: 60px; margin:0;">{final_score}</h1>
                    <h3 style="color:#333; margin:0;">{verdict_txt}</h3>
                </div>
                """, unsafe_allow_html=True)

    else:
        st.error(f"Ticker '{final_t}' not found.")
