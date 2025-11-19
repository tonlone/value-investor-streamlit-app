import streamlit as st
import yfinance as yf
from groq import Groq

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Value Investor Pro", layout="wide", page_icon="📈")

# --- CSS STYLING ---
st.markdown("""
<style>
    .multiplier-box {
        font-size: 30px;
        font-weight: bold;
        text-align: center;
        padding: 10px;
        border-radius: 10px;
        background-color: #f9f9f9;
        margin-top: 10px;
    }
    .final-score-box {
        text-align: center; 
        padding: 20px; 
        border-radius: 15px; 
        background-color: #ffffff; 
        margin-top: 20px;
        border: 4px solid #ccc; /* Default border */
    }
    /* Hide the mobile search expander on large screens if preferred, 
       but pure CSS detection is tricky in Streamlit. 
       We keep it visible but collapsed by default. */
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
    prompt = f"Analyze {ticker} regarding '{topic}'. Context: {summary}. Give a score (0-4) and 1 sentence reason. Format: SCORE|REASON"
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Primary
            messages=[{"role": "user", "content": prompt}], temperature=0.1, max_tokens=100
        )
        return resp.choices[0].message.content
    except:
        try: # Fallback
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant", 
                messages=[{"role": "user", "content": prompt}], temperature=0.1, max_tokens=100
            )
            return resp.choices[0].message.content
        except: return "0|Error"

# --- INPUT LOGIC (THE HYBRID MIRROR) ---

# Initialize Session State for Layout Mode
if 'layout_mode' not in st.session_state:
    st.session_state.layout_mode = 'desktop' # Default
if 'active_ticker' not in st.session_state:
    st.session_state.active_ticker = "NVDA"
if 'active_market' not in st.session_state:
    st.session_state.active_market = "US"

# 1. DESKTOP INPUT (Sidebar)
with st.sidebar:
    st.header("🖥️ Desktop Control")
    with st.form(key='desktop_form'):
        d_market = st.selectbox("Market", ["US", "Canada (TSX)", "HK (HKEX)"], key='d_m')
        d_ticker = st.text_input("Ticker", value="NVDA", key='d_t').upper()
        d_submit = st.form_submit_button("Analyze (Desktop Layout)")

# 2. MOBILE INPUT (Main Page Expander)
# This is what mobile users will see first
with st.expander("📱 Tap here for Mobile Search", expanded=False):
    with st.form(key='mobile_form'):
        m_col1, m_col2 = st.columns([1, 1])
        with m_col1:
            m_market = st.selectbox("Market", ["US", "Canada (TSX)", "HK (HKEX)"], key='m_m')
        with m_col2:
            m_ticker = st.text_input("Ticker", value="NVDA", key='m_t').upper()
        m_submit = st.form_submit_button("Analyze (Mobile Layout)", type="primary")

# --- LOGIC TO HANDLE INPUTS ---
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
    
    # Ticker Formatting
    raw_t = st.session_state.active_ticker
    mkt = st.session_state.active_market
    final_t = raw_t
    
    if mkt == "Canada (TSX)" and ".TO" not in raw_t: final_t += ".TO"
    elif mkt == "HK (HKEX)": 
        nums = ''.join(filter(str.isdigit, raw_t))
        if nums: final_t = f"{nums.zfill(4)}.HK"
        else: final_t += ".HK"

    with st.spinner(f"Analyzing {final_t} ({st.session_state.layout_mode} view)..."):
        data = get_stock_data(final_t)

    if data:
        st.header(f"{data['name']}")
        st.caption(f"{final_t} | {data['industry']} | {data['currency']}")

        # --- PREPARE DATA ---
        topics = ["Moat/Product", "Revenue Growth", "Competition", "Profitability", "Management"]
        qual_results = []
        total_qual = 0
        
        # We fetch AI results first so we can pass them to the layout
        progress = st.progress(0)
        for i, t in enumerate(topics):
            progress.progress((i)/5)
            res = analyze_qualitative(data['name'], data['summary'], t)
            try: 
                s, r = res.split('|', 1)
                s = int(float(s))
            except: s, r = 0, "Error"
            total_qual += s
            qual_results.append((t, s, r))
        progress.empty()

        # Calculate Valuation
        pe = data['pe']
        if pe <= 0: mult, color_code = 1, "#8B0000"
        elif pe < 20: mult, color_code = 5, "#00C805"
        elif pe < 35: mult, color_code = 4, "#90EE90"
        elif pe < 50: mult, color_code = 3, "#FFA500"
        elif pe < 75: mult, color_code = 2, "#FF4500"
        else: mult, color_code = 1, "#8B0000"

        final_score = total_qual * mult
        
        # --- LAYOUT RENDERING ---
        
        # LAYOUT A: DESKTOP (Your Original Design - Columns)
        if st.session_state.layout_mode == 'desktop':
            
            col1, col2 = st.columns([1.5, 1])
            
            with col1:
                st.subheader("1. Qualitative Analysis")
                for item in qual_results:
                    st.markdown(f"**{item[0]}**")
                    st.progress(item[1]/4)
                    st.caption(f"{item[1]}/4 - {item[2]}")
                    st.divider()
                st.info(f"Qualitative Score: {total_qual}/20")

            with col2:
                st.subheader("2. Valuation")
                with st.container(border=True):
                    st.metric("Price", f"{data['price']:.2f}")
                    st.metric("PE Ratio", f"{pe:.2f}")
                    st.markdown(f"<div class='multiplier-box' style='color:{color_code}; border:2px solid {color_code}'>x{mult}</div>", unsafe_allow_html=True)
            
            # Final Verdict Desktop
            st.divider()
            verdict_color = "#00C805" if final_score >= 75 else "#FFA500" if final_score >= 45 else "#FF0000"
            st.markdown(f"""
            <div class="final-score-box" style="border-color: {verdict_color};">
                <h1 style="color: {verdict_color}; font-size: 60px; margin:0;">{final_score}</h1>
                <h3 style="color: black; margin:0;">FINAL SCORE</h3>
            </div>
            """, unsafe_allow_html=True)

        # LAYOUT B: MOBILE (Suggested Design - Tabs)
        else:
            
            tab1, tab2, tab3 = st.tabs(["🏢 Business", "💰 Value", "🏁 Verdict"])
            
            with tab1:
                st.info(f"Total Quality: **{total_qual}/20**")
                for item in qual_results:
                    with st.chat_message("assistant", avatar="🤖"):
                        st.write(f"**{item[0]}**")
                        st.write(f"⭐ {item[1]}/4")
                        st.caption(item[2])

            with tab2:
                c1, c2 = st.columns(2)
                c1.metric("Price", f"{data['price']:.2f}")
                c2.metric("PE", f"{pe:.2f}")
                st.markdown(f"<div class='multiplier-box' style='color:{color_code}; border:2px solid {color_code}'>x{mult}</div>", unsafe_allow_html=True)
                if mult == 5: st.caption("✅ Undervalued")
                elif mult == 1: st.caption("⚠️ Expensive")

            with tab3:
                verdict_color = "#00C805" if final_score >= 75 else "#FFA500" if final_score >= 45 else "#FF0000"
                verdict_text = "STRONG BUY" if final_score >= 75 else "HOLD" if final_score >= 45 else "SELL"
                
                st.markdown(f"""
                <div class="final-score-box" style="border-color: {verdict_color};">
                    <h2 style="color:black; margin:0;">VERDICT</h2>
                    <h1 style="color: {verdict_color}; font-size: 70px; margin:0;">{final_score}</h1>
                    <h3 style="color:black; margin:0;">{verdict_text}</h3>
                </div>
                """, unsafe_allow_html=True)

    else:
        st.error("Ticker not found.")
