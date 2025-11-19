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
    """Fetches financial data and history from Yahoo Finance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if not info: return None
        
        # Get Price
        price = info.get('currentPrice', 0)
        
        # Fetch 6mo history (We need this for the charts)
        hist = stock.history(period="6mo")
        
        if price == 0 and not hist.empty:
            price = hist['Close'].iloc[-1]

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
            "summary": info.get('longBusinessSummary', ''),
            "history": hist['Close'] # Passing the price history series
        }
    except: return None

def analyze_qualitative(ticker, summary, topic):
    """
    Primary: Llama-3.3-70b (Best Reasoning/Cost Balance)
    Backup:  Llama-3.1-8b (Cheapest: $0.05/1M tokens)
    """
    PRIMARY_MODEL = "llama-3.3-70b-versatile" 
    BACKUP_MODEL  = "llama-3.1-8b-instant"    

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

# 1. DESKTOP SIDEBAR
with st.sidebar:
    st.header("Analysis Tool")
    with st.form(key='desktop_form'):
        st.write("Select Market")
        d_market = st.selectbox("Market", ["US", "Canada (TSX)", "HK (HKEX)"], label_visibility="collapsed")
        st.write("Enter Stock Ticker")
        d_ticker = st.text_input("Ticker", value="NVDA", label_visibility="collapsed").upper()
        d_submit = st.form_submit_button("Analyze Stock", type="primary") 
    
    st.markdown("---")
    st.caption("Primary: Llama 3.3 70B\nBackup: Llama 3.1 8B")

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
        total_qual = 0.0 
        backup_used = False
        
        progress = st.progress(0)
        for i, t in enumerate(topics):
            progress.progress((i)/5)
            res, is_backup = analyze_qualitative(data['name'], data['summary'], t)
            if is_backup: backup_used = True
            
            try: 
                s, r = res.split('|', 1)
                s = float(s.strip()) 
            except: s, r = 0.0, "Error parsing AI"
            
            total_qual += s
            qual_results.append((t, s, r))
        progress.empty()

        # --- VALUATION LOGIC ---
        pe = data['pe']
        if pe <= 0: mult, color_code = 1.0, "#8B0000"
        elif pe <= 20: mult, color_code = 5.0, "#00C805"
        elif pe >= 75: mult, color_code = 1.0, "#8B0000" 
        else:
            pct = (pe - 20) / 55
            mult = 5.0 - (pct * 4.0)
            if mult >= 4.0: color_code = "#00C805"
            elif mult >= 3.0: color_code = "#90EE90"
            elif mult >= 2.0: color_code = "#FFA500"
            else: color_code = "#FF4500"

        mult = round(mult, 2) 
        final_score = round(total_qual * mult, 1) 
        
        if backup_used:
            st.toast("High traffic: Used Backup Model", icon="⚠️")

        # --- VIEW A: DESKTOP (6 Month Chart) ---
        if st.session_state.layout_mode == 'desktop':
            
            col1, col2 = st.columns([1.5, 1])
            
            with col1:
                st.subheader("1. Qualitative Analysis")
                for item in qual_results:
                    st.markdown(f"**{item[0]}**")
                    st.progress(min(item[1]/4.0, 1.0)) 
                    st.caption(f"**{item[1]}/4** — {item[2]}")
                    st.divider()
                st.info(f"Total Qualitative Score: {total_qual:.1f} / 20")

            with col2:
                st.subheader("2. Valuation")
                with st.container(border=True):
                    st.metric(f"Price ({data['currency']})", f"{data['price']:.2f}")
                    st.metric("Forward PE", f"{pe:.2f}")
                    
                    # --- 6 MONTH CHART FOR DESKTOP ---
                    st.caption("6-Month Price History")
                    st.line_chart(data['history'], height=200)
                    
                    st.markdown("#### Valuation Multiplier")
                    st.markdown(f"<div class='multiplier-box' style='color:{color_code}; border:2px solid {color_code}'>x{mult}</div>", unsafe_allow_html=True)
                    
                    if mult >= 4.5: st.caption("✅ Deep Value")
                    elif mult <= 1.5: st.caption("⚠️ Expensive")
                    else: st.caption(f"⚖️ Fair Value Adjustment")
            
            st.divider()
            verdict_color = "#00C805" if final_score >= 75 else "#FFA500" if final_score >= 45 else "#FF0000"
            st.markdown(f"""
            <div class="final-score-box" style="border-color: {verdict_color};">
                <h2 style="color:#333; margin:0;">FINAL SCORE</h2>
                <h1 style="color: {verdict_color}; font-size: 80px; margin:0;">{final_score}</h1>
            </div>
            """, unsafe_allow_html=True)

        # --- VIEW B: MOBILE (1 Month Chart) ---
        else:
            
            tab1, tab2, tab3 = st.tabs(["🏢 Business", "💰 Value", "🏁 Verdict"])
            
            with tab1:
                st.info(f"Quality Score: **{total_qual:.1f}/20**")
                for item in qual_results:
                    with st.chat_message("assistant", avatar="🤖"):
                        st.write(f"**{item[0]}**")
                        st.write(f"⭐ {item[1]}")
                        st.caption(item[2])

            with tab2:
                c1, c2 = st.columns(2)
                c1.metric("Price", f"{data['price']:.0f}")
                c2.metric("PE", f"{pe:.1f}")
                
                # --- 1 MONTH CHART FOR MOBILE ---
                # Slice the last 22 days (approx 1 trading month)
                st.caption("1-Month Price Trend")
                if not data['history'].empty:
                    st.line_chart(data['history'].tail(22), height=150)
                
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
