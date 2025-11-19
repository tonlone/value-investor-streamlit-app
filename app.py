import streamlit as st
import yfinance as yf
import pandas as pd
import re
from datetime import datetime
from groq import Groq

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Value Investor Pro", layout="wide", page_icon="📈")

# --- SESSION STATE & TRANSLATION SETUP ---
if 'language' not in st.session_state:
    st.session_state.language = 'EN'

def toggle_language():
    st.session_state.language = 'CN' if st.session_state.language == 'EN' else 'EN'

# --- TRANSLATION DICTIONARY (Static to save tokens) ---
T = {
    "EN": {
        "sidebar_title": "Analysis Tool",
        "market_label": "Select Market",
        "ticker_label": "Enter Stock Ticker",
        "analyze_btn": "Analyze Stock",
        "analyze_mobile_btn": "Analyze (Mobile)",
        "methodology": "Methodology:",
        "qual_score": "Qualitative Score (0-20)",
        "qual_detail": "(5 topics x 4 pts)",
        "val_mult": "Valuation Multiplier (1-5)",
        "val_detail": "(Based on Hist. PE Range)",
        "final_score": "= Final Score (0-100)",
        "tab_value": "💎 Value Analysis",
        "tab_tech": "📈 Technical Analysis",
        "tab_fin": "📊 Financials",
        "topics": ["Unique Product/Moat", "Revenue Growth", "Competitive Advantage", "Profit Stability", "Management"],
        "loading_data": "Fetching data for",
        "loading_ai": "AI Analyzing:",
        "currency": "Currency",
        "industry": "Industry",
        "val_analysis_header": "1. Qualitative Analysis (AI)",
        "quant_val_header": "2. Quantitative Valuation",
        "price": "Price",
        "pe_ttm": "Trailing PE (TTM)",
        "pe_ratio": "Forward PE (Used for Calc)",
        "multiplier_label": "Valuation Multiplier",
        "calc_qual": "Qualitative Score",
        "calc_mult": "Multiplier",
        "calc_result": "Final Score",
        "score_calc_title": "VALUE SCORE CALCULATION",
        "hist_low_pe": "Hist. Low PE (5Y)",
        "hist_high_pe": "Hist. High PE (5Y)",
        "pe_pos": "PE Position (5Y)",
        "pe_pos_low": "Low (Cheap)",
        "pe_pos_high": "High (Expensive)",
        "grade_strong_buy": "Strong Buy",
        "grade_buy": "Buy",
        "grade_hold": "Hold",
        "grade_sell": "Sell",
        "grade_avoid": "Avoid",
        "grading_scale": "Grading Scale:",
        "tech_verdict": "Technical Verdict", "reason": "Reason",
        "support": "Support", "resistance": "Resistance", "trend": "Trend", "squeeze": "Squeeze",
        "lbl_rsi": "RSI (14)", "lbl_vol": "Vol Ratio",
        "status_high": "High", "status_low": "Low", "status_ok": "OK",
        "recent_div": "💰 Recent Dividend History",
        "no_div": "No recent dividend history available.",
        "fiscal_year": "Fiscal Year End",
        "fin_mkt_cap": "Market Cap", "fin_ent_val": "Enterprise Val",
        "fin_trail_pe": "Trailing P/E", "fin_fwd_pe": "Forward P/E",
        "fin_peg": "PEG Ratio", "fin_ps": "Price/Sales",
        "fin_pb": "Price/Book", "fin_beta": "Beta",
        "fin_prof_marg": "Profit Margin", "fin_gross_marg": "Gross Margin",
        "fin_roa": "ROA", "fin_roe": "ROE",
        "fin_eps": "EPS (ttm)", "fin_rev": "Revenue (ttm)",
        "fin_div_yield": "Dividend Yield", "fin_target": "Target Price",
        "act_buy_sup": "BUY (Support Bounce) 🟢", "act_buy_break": "STRONG BUY (Breakout) 🚀",
        "act_prep": "PREPARE TO BUY (VCP) 🔵", "act_profit": "HOLD / TAKE PROFIT 🟠",
        "act_buy_hold": "BUY / HOLD 🟢", "act_sell_sup": "SELL / AVOID 🔴",
        "act_watch_oversold": "WATCH (Oversold) 🟡", "act_avoid": "AVOID / SELL 🔴",
        "reas_sup": "Uptrend + Near Support.", "reas_vol": "Uptrend + High Volume.",
        "reas_vcp": "Volatility Squeeze detected.", "reas_over": "Uptrend but Overbought.",
        "reas_health": "Healthy Uptrend.", "reas_break_sup": "Breaking below Support.",
        "reas_oversold": "Potential oversold bounce.", "reas_down": "Stock is in a Downtrend."
    },
    "CN": {
        "sidebar_title": "股票分析工具",
        "market_label": "選擇市場",
        "ticker_label": "輸入股票代號",
        "analyze_btn": "開始分析",
        "analyze_mobile_btn": "開始分析 (手機版)",
        "methodology": "分析方法:",
        "qual_score": "定性評分 (0-20)",
        "qual_detail": "(5個主題 x 4分)",
        "val_mult": "估值倍數 (1-5)",
        "val_detail": "(基於歷史 PE 區間)",
        "final_score": "= 最終評分 (0-100)",
        "tab_value": "💎 價值分析",
        "tab_tech": "📈 技術分析",
        "tab_fin": "📊 財務數據",
        "topics": ["獨特產品/護城河", "營收增長潛力", "競爭優勢", "獲利穩定性", "管理層質素"],
        "loading_data": "正在獲取數據：",
        "loading_ai": "AI 正在分析：",
        "currency": "貨幣",
        "industry": "行業",
        "val_analysis_header": "1. 定性分析 (AI)",
        "quant_val_header": "2. 量化估值",
        "price": "當前股價",
        "pe_ttm": "歷史市盈率 (Trailing)",
        "pe_ratio": "預測市盈率 (Forward)",
        "multiplier_label": "本益比乘數 (Multiplier)",
        "calc_qual": "投資評估分數",
        "calc_mult": "本益比乘數",
        "calc_result": "最終評分",
        "score_calc_title": "價值評分計算",
        "hist_low_pe": "歷史最低 PE (5年)",
        "hist_high_pe": "歷史最高 PE (5年)",
        "pe_pos": "目前 PE 位置區間",
        "pe_pos_low": "低位 (便宜)",
        "pe_pos_high": "高位 (昂貴)",
        "grade_strong_buy": "非常優秀 (Strong Buy)",
        "grade_buy": "優秀 (Buy)",
        "grade_hold": "良好 (Hold)",
        "grade_sell": "普通 (Sell)",
        "grade_avoid": "差 (Avoid)",
        "grading_scale": "評級標準:",
        "tech_verdict": "技術面結論", "reason": "理由",
        "support": "支持位", "resistance": "阻力位", "trend": "趨勢", "squeeze": "擠壓 (VCP)",
        "lbl_rsi": "RSI (14)", "lbl_vol": "成交量比",
        "status_high": "偏高", "status_low": "偏低", "status_ok": "適中",
        "recent_div": "💰 近期派息記錄",
        "no_div": "沒有近期派息記錄。",
        "fiscal_year": "財政年度結算日",
        "fin_mkt_cap": "市值", "fin_ent_val": "企業價值",
        "fin_trail_pe": "歷史市盈率", "fin_fwd_pe": "預測市盈率",
        "fin_peg": "PEG 比率", "fin_ps": "市銷率 (P/S)",
        "fin_pb": "市賬率 (P/B)", "fin_beta": "Beta 系數",
        "fin_prof_marg": "淨利潤率", "fin_gross_marg": "毛利率",
        "fin_roa": "ROA", "fin_roe": "ROE",
        "fin_eps": "每股盈利", "fin_rev": "總營收",
        "fin_div_yield": "股息率", "fin_target": "目標價",
        "act_buy_sup": "買入 (支持位反彈) 🟢", "act_buy_break": "強力買入 (突破) 🚀",
        "act_prep": "準備買入 (VCP擠壓) 🔵", "act_profit": "持有 / 獲利止盈 🟠",
        "act_buy_hold": "買入 / 持有 🟢", "act_sell_sup": "賣出 / 觀望 🔴",
        "act_watch_oversold": "關注 (超賣反彈) 🟡", "act_avoid": "觀望 / 賣出 🔴",
        "reas_sup": "上升趨勢 + 接近支持位。", "reas_vol": "上升趨勢 + 成交量激增。",
        "reas_vcp": "檢測到波動率擠壓 (VCP)。", "reas_over": "上升趨勢但超買。",
        "reas_health": "健康的上升趨勢。", "reas_break_sup": "跌破支持位。",
        "reas_oversold": "下跌趨勢但可能超賣反彈。", "reas_down": "股價處於下降趨勢。"
    }
}

def txt(key):
    return T[st.session_state.language][key]

# --- CSS STYLING ---
st.markdown("""
<style>
    .multiplier-box {
        font-size: 35px; font-weight: bold; text-align: center; padding: 15px; 
        border-radius: 10px; background-color: #ffffff; margin-top: 10px;
        margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .methodology-box {
        background-color: #262730; padding: 15px; border-radius: 10px;
        border: 1px solid #444; font-size: 14px; margin-top: 20px;
    }
    .final-score-box {
        text-align: center; padding: 20px; border-radius: 15px; 
        background-color: #ffffff; margin-top: 20px; border: 4px solid #ccc;
    }
    .grade-table { width: 100%; border-collapse: collapse; font-size: 14px; margin-top: 10px; }
    .grade-table td { padding: 5px; border: 1px solid #eee; text-align: center; }
    .grade-green { background-color: #e6ffe6; color: #006600; font-weight: bold; }
    .grade-lightgreen { background-color: #f0fff0; color: #009900; }
    .grade-yellow { background-color: #fffff0; color: #b3b300; }
    .grade-orange { background-color: #fff5e6; color: #cc6600; }
    .grade-red { background-color: #ffe6e6; color: #cc0000; }
    
    div[data-testid="stForm"] button[kind="primary"] {
        background-color: #FF4B4B; color: white; border: none;
        font-weight: bold; font-size: 16px; padding: 0.5rem 1rem; width: 100%;
    }
    div[data-testid="stForm"] button[kind="primary"]:hover {
        background-color: #FF0000; border-color: #FF0000;
    }
</style>
""", unsafe_allow_html=True)

# --- API KEY SETUP ---
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except (FileNotFoundError, KeyError):
    GROQ_API_KEY = st.sidebar.text_input("Enter Groq API Key", type="password")
    if not GROQ_API_KEY:
        st.warning("⚠️ Please enter a Groq API Key in the sidebar or set it in st.secrets.")
        st.stop()

client = Groq(api_key=GROQ_API_KEY)

# --- DATA HELPERS ---

def fmt_num(val, is_pct=False, is_currency=False):
    if val is None or val == "N/A": return "-"
    if is_pct: return f"{val * 100:.2f}%"
    if is_currency:
        if val > 1e12: return f"{val/1e12:.2f}T"
        if val > 1e9: return f"{val/1e9:.2f}B"
        if val > 1e6: return f"{val/1e6:.2f}M"
    return f"{val:.2f}"

def fmt_dividend(val):
    if val is None: return "-"
    return f"{val:.2f}%"

def fmt_date(ts):
    if ts is None: return "-"
    try: return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
    except: return str(ts)

def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        if not info: return None
        
        price = info.get('currentPrice', 0)
        
        # 5 Year History for Min/Max PE
        hist = stock.history(period="5y")
        if price == 0 and not hist.empty: price = hist['Close'].iloc[-1]
        
        # EPS & PE
        eps = info.get('forwardEps')
        if eps is None: eps = info.get('trailingEps')
        
        pe = info.get('forwardPE')
        if pe is None: pe = price / eps if (eps and eps > 0) else 0

        # Hist PE Calc
        min_pe, max_pe = 0, 0
        if eps and eps > 0 and not hist.empty:
            pe_series = hist['Close'] / eps
            # Filter outliers (PE > 200 or < 0)
            pe_series = pe_series[(pe_series > 0) & (pe_series < 200)]
            if not pe_series.empty:
                min_pe = pe_series.min()
                max_pe = pe_series.max()
        
        return {
            "price": price, "currency": info.get('currency', 'USD'), "pe": pe,
            "eps": eps, "min_pe": min_pe, "max_pe": max_pe,
            "name": info.get('longName', ticker), "industry": info.get('industry', 'Unknown'),
            "summary": info.get('longBusinessSummary', 'No summary available.'), 
            "history": hist, "dividends": stock.dividends, "raw_info": info 
        }
    except: return None

def calculate_technicals(df):
    if df.empty or len(df) < 200: return None
    
    # Use last 1 year (approx 252 trading days) for SMA 200
    df_recent = df.tail(300).copy()
    
    df_recent['SMA_50'] = df_recent['Close'].rolling(window=50).mean()
    df_recent['SMA_200'] = df_recent['Close'].rolling(window=200).mean()
    
    delta = df_recent['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df_recent['RSI'] = 100 - (100 / (1 + rs))
    
    avg_vol = df_recent['Volume'].rolling(window=20).mean().iloc[-1]
    curr_vol = df_recent['Volume'].iloc[-1]
    vol_ratio = curr_vol / avg_vol if avg_vol > 0 else 1.0
    
    recent_60 = df_recent.tail(60)
    support = recent_60['Low'].min()
    resistance = recent_60['High'].max()
    
    vol_short = df_recent['Close'].rolling(window=10).std().iloc[-1]
    vol_long = df_recent['Close'].rolling(window=60).std().iloc[-1]
    is_squeezing = vol_short < (vol_long * 0.5)
    
    curr_price = df_recent['Close'].iloc[-1]
    sma_50 = df_recent['SMA_50'].iloc[-1]
    sma_200 = df_recent['SMA_200'].iloc[-1]
    
    trend = "neutral"
    if curr_price > sma_200:
        trend = "uptrend" if curr_price > sma_50 else "weak_uptrend"
    else:
        trend = "downtrend"
        
    return {
        "trend": trend, "rsi": df_recent['RSI'].iloc[-1], 
        "support": support, "resistance": resistance,
        "vol_ratio": vol_ratio, "is_squeezing": is_squeezing,
        "last_price": curr_price
    }

def analyze_qualitative(ticker, summary, topic):
    """
    Primary: Llama-3.3-70b-versatile
    Backup: Llama-3.1-8b-instant
    Token Saving: Hardcoded instructions for language.
    """
    PRIMARY_MODEL = "llama-3.3-70b-versatile" 
    BACKUP_MODEL  = "llama-3.1-8b-instant"    
    
    lang_instruction = "Answer in English."
    if st.session_state.language == 'CN':
        lang_instruction = "You MUST Output the reason in Traditional Chinese (繁體中文)."

    prompt = (
        f"Analyze {ticker} regarding '{topic}'. "
        f"Context: {summary}. "
        f"Give a specific score from 0.0 to 4.0 (use 1 decimal place). "
        f"Provide a 1 sentence reason. {lang_instruction} "
        f"Strict Format: SCORE|REASON"
    )
    
    def call_groq(model_id):
        return client.chat.completions.create(
            model=model_id, 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=150 
        )

    try:
        resp = call_groq(PRIMARY_MODEL)
        return resp.choices[0].message.content, False
    except:
        try:
            resp = call_groq(BACKUP_MODEL)
            return resp.choices[0].message.content, True
        except Exception as e:
            return f"0.0|Error: {str(e)}", True

# --- TOP BAR ---
col_title, col_lang = st.columns([8, 1])
with col_title: st.title("📈 Value Investor Pro")
with col_lang: 
    if st.button("🌐 Eng/中"):
        toggle_language()
        st.rerun()

# --- INPUTS ---
if 'layout_mode' not in st.session_state: st.session_state.layout_mode = 'desktop' 
if 'active_ticker' not in st.session_state: st.session_state.active_ticker = "NVDA"
if 'active_market' not in st.session_state: st.session_state.active_market = "US"

with st.sidebar:
    st.header(txt('sidebar_title'))
    with st.form(key='desktop_form'):
        st.caption(txt('market_label'))
        d_market = st.selectbox("M", ["US", "Canada (TSX)", "HK (HKEX)"], label_visibility="collapsed")
        st.caption(txt('ticker_label'))
        d_ticker = st.text_input("T", value="NVDA", label_visibility="collapsed").upper()
        d_submit = st.form_submit_button(txt('analyze_btn'), type="primary") 
    
    st.markdown(f"""
    <div class="methodology-box">
    <strong style="color:#4da6ff;">{txt('methodology')}</strong><br><br>
    {txt('qual_score')} <span style="color:#aaa">{txt('qual_detail')}</span><br>
    ✖ {txt('val_mult')} <span style="color:#aaa">{txt('val_detail')}</span><br>
    = {txt('final_score')}
    </div>
    """, unsafe_allow_html=True)

with st.expander(f"📱 {txt('analyze_mobile_btn')}", expanded=False):
    with st.form(key='mobile_form'):
        m_c1, m_c2 = st.columns(2)
        with m_c1: m_market = st.selectbox(txt('market_label'), ["US", "Canada (TSX)", "HK (HKEX)"], key='m_m')
        with m_c2: m_ticker = st.text_input(txt('ticker_label'), value="NVDA", key='m_t').upper()
        m_submit = st.form_submit_button(txt('analyze_mobile_btn'), type="primary")

run_analysis = False
if d_submit:
    st.session_state.layout_mode, st.session_state.active_ticker, st.session_state.active_market = 'desktop', d_ticker, d_market
    run_analysis = True
elif m_submit:
    st.session_state.layout_mode, st.session_state.active_ticker, st.session_state.active_market = 'mobile', m_ticker, m_market
    run_analysis = True

# --- MAIN EXECUTION ---
if run_analysis:
    raw_t = st.session_state.active_ticker
    mkt = st.session_state.active_market
    final_t = raw_t
    if mkt == "Canada (TSX)" and ".TO" not in raw_t: final_t += ".TO"
    elif mkt == "HK (HKEX)": 
        nums = ''.join(filter(str.isdigit, raw_t))
        final_t = f"{nums.zfill(4)}.HK" if nums else f"{raw_t}.HK"

    with st.spinner(f"{txt('loading_data')} {final_t}..."):
        data = get_stock_data(final_t)

    if data:
        st.header(f"{data['name']} ({final_t})")
        st.caption(f"{txt('industry')}: {data['industry']} | {txt('currency')}: {data['currency']}")
        
        tab_fund, tab_tech, tab_fin = st.tabs([txt('tab_value'), txt('tab_tech'), txt('tab_fin')])

        # --- TAB 1: FUNDAMENTAL ---
        with tab_fund:
            eng_topics = ["Unique Product/Moat", "Revenue Growth", "Competitive Advantage", "Profit Stability", "Management"]
            display_topics = txt('topics')
            qual_results = []
            total_qual = 0.0 
            backup_used = False
            
            prog_bar = st.progress(0)
            
            col_q, col_v = st.columns([1.6, 1])
            
            with col_q:
                st.subheader(txt('val_analysis_header'))
                for i, t_eng in enumerate(eng_topics):
                    prog_bar.progress((i)/5)
                    res, is_backup = analyze_qualitative(data['name'], data['summary'], t_eng)
                    if is_backup: backup_used = True
                    
                    match = re.search(r'\b([0-3](?:\.\d)?|4(?:\.0)?)\b', res)
                    if match:
                        s_str = match.group(1); s = float(s_str)
                        r = res.replace(s_str, "").replace("|", "").replace("SCORE", "").replace("REASON", "").strip().strip(' :-=\n')
                    else: s, r = 0.0, res 
                    total_qual += s
                    
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        with c1: st.markdown(f"**{display_topics[i]}**")
                        with c2: st.markdown(f"<h4 style='margin:0; text-align:right; color:#4da6ff;'>{s} <span style='font-size:14px; color:#888;'>/ 4</span></h4>", unsafe_allow_html=True)
                        st.progress(min(s/4.0, 1.0))
                        st.caption(r)
                prog_bar.empty()
                if backup_used: st.toast("Backup Model used.", icon="⚠️")

            # Valuation Logic
            pe = data['pe']
            min_pe, max_pe = data['min_pe'], data['max_pe']
            
            mult = 1.0
            pos_pct = 1.0
            color_code = "#FF4500"

            if pe and pe > 0 and max_pe > min_pe:
                pos_pct = (pe - min_pe) / (max_pe - min_pe)
                if pos_pct < 0.25: mult = 5.0
                elif pos_pct < 0.50: mult = 4.0
                elif pos_pct < 0.75: mult = 3.0
                elif pos_pct < 1.00: mult = 2.0
                else: mult = 1.0
            
            if mult >= 4: color_code = "#00C805"
            elif mult >= 3: color_code = "#90EE90"
            elif mult >= 2: color_code = "#FFA500"

            final_score = round(total_qual * mult, 1)
            
            verdict_text, v_color, v_border = txt('grade_avoid'), "#ffcccc", "#cc0000"
            if final_score >= 75: verdict_text, v_color, v_border = txt('grade_strong_buy'), "#e6ffe6", "#006600"
            elif final_score >= 60: verdict_text, v_color, v_border = txt('grade_buy'), "#f0fff0", "#009900"
            elif final_score >= 45: verdict_text, v_color, v_border = txt('grade_hold'), "#fffff0", "#b3b300"
            elif final_score >= 30: verdict_text, v_color, v_border = txt('grade_sell'), "#fff5e6", "#cc6600"

            with col_v:
                st.subheader(txt('quant_val_header'))
                with st.container(border=True):
                    st.metric(txt('price'), f"{data['price']:.2f}")
                    st.metric(txt('pe_ratio'), f"{pe:.2f}" if pe and pe > 0 else "N/A")
                    
                    st.caption(f"PE Range (5Y): {min_pe:.1f} - {max_pe:.1f}")
                    st.progress(max(0.0, min(1.0, pos_pct)) if pe > 0 else 1.0)
                    
                    st.subheader(txt('multiplier_label'))
                    st.markdown(f"""<div class="multiplier-box" style="border: 2px solid {color_code}; color: {color_code};">x{mult:.0f}</div>""", unsafe_allow_html=True)

            st.markdown(f"""
            <div class="final-score-box" style="border-color: {v_border}; padding: 20px;">
            <h3 style="color:#555; margin:0;">{txt('score_calc_title')}</h3>
            <div style="display:flex; justify-content:center; align-items:center; gap:10px; flex-wrap:wrap; margin-top:10px;">
                <div><div style="font-size:30px; font-weight:bold;">{total_qual:g}</div><div style="font-size:12px;">{txt('calc_qual')}</div></div>
                <div style="font-size:20px;">✖</div>
                <div><div style="font-size:30px; font-weight:bold;">{mult:g}</div><div style="font-size:12px;">{txt('calc_mult')}</div></div>
                <div style="font-size:20px;">=</div>
                <div style="background:{v_color}; padding:10px 20px; border-radius:10px; border:2px solid {v_border};">
                    <div style="font-size:40px; font-weight:900; color:{v_border}; line-height:1;">{final_score}</div>
                    <div style="font-size:14px; font-weight:bold; color:#333;">{verdict_text}</div>
                </div>
            </div></div>
            """, unsafe_allow_html=True)

        # --- TAB 2: TECHNICAL ---
        with tab_tech:
            tech = calculate_technicals(data['history'])
            if tech:
                action_key, reason_key = "act_avoid", "reas_down"
                
                if "uptrend" in tech['trend']:
                    if tech['last_price'] < tech['support'] * 1.05: action_key, reason_key = "act_buy_sup", "reas_sup"
                    elif tech['vol_ratio'] > 1.5: action_key, reason_key = "act_buy_break", "reas_vol"
                    elif tech['is_squeezing']: action_key, reason_key = "act_prep", "reas_vcp"
                    elif tech['rsi'] > 70: action_key, reason_key = "act_profit", "reas_over"
                    else: action_key, reason_key = "act_buy_hold", "reas_health"
                else:
                    if tech['last_price'] < tech['support']: action_key, reason_key = "act_sell_sup", "reas_break_sup"
                    elif tech['rsi'] < 30: action_key, reason_key = "act_watch_oversold", "reas_oversold"
                
                st.subheader(f"{txt('tech_verdict')}: {txt(action_key)}")
                st.info(f"📝 {txt('reason')}: {txt(reason_key)}")
                
                tc1, tc2, tc3, tc4 = st.columns(4)
                tc1.metric(txt('trend'), txt(tech['trend']))
                tc2.metric(txt('lbl_rsi'), f"{tech['rsi']:.1f}", delta=txt('status_high') if tech['rsi']>70 else txt('status_low') if tech['rsi']<30 else txt('status_ok'), delta_color="inverse")
                tc3.metric(txt('lbl_vol'), f"{tech['vol_ratio']:.2f}x")
                tc4.metric(txt('squeeze'), "YES" if tech['is_squeezing'] else "No")
                
                st.line_chart(data['history'].tail(252)['Close'])
            else: st.warning("Not enough historical data.")

        # --- TAB 3: FINANCIALS ---
        with tab_fin:
            i = data['raw_info']
            def row(cols):
                c = st.columns(len(cols))
                for idx, (k, v) in enumerate(cols): c[idx].metric(txt(k), v)

            row([("fin_mkt_cap", fmt_num(i.get('marketCap'), is_currency=True)), ("fin_ent_val", fmt_num(i.get('enterpriseValue'), is_currency=True)), ("fin_trail_pe", fmt_num(i.get('trailingPE'))), ("fin_fwd_pe", fmt_num(i.get('forwardPE')))])
            st.divider()
            row([("fin_prof_marg", fmt_num(i.get('profitMargins'), is_pct=True)), ("fin_gross_marg", fmt_num(i.get('grossMargins'), is_pct=True)), ("fin_roa", fmt_num(i.get('returnOnAssets'), is_pct=True)), ("fin_roe", fmt_num(i.get('returnOnEquity'), is_pct=True))])
            st.divider()
            st.subheader(txt('recent_div'))
            divs = data.get('dividends')
            if divs is not None and not divs.empty:
                df_divs = divs.sort_index(ascending=False).head(10).reset_index()
                df_divs.columns = ["Date", "Amount"]
                df_divs['Date'] = df_divs['Date'].dt.strftime('%Y-%m-%d')
                st.table(df_divs)
            else: st.info(txt('no_div'))

    else: st.error(f"Ticker '{final_t}' not found.")
