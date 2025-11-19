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
        d_market = st.selectb
