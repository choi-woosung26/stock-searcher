import streamlit as st
from tradingview_screener import Query, col
import pandas as pd

st.set_page_config(page_title="주식 스캐너", page_icon="📈", layout="wide")

st.title("📈 한국 주식 종목 검색기")
st.markdown("이동평균선 돌파 · 신고가 근처 종목을 찾습니다.")

# ── 사이드바 설정 ──────────────────────────────────
st.sidebar.header("🔍 검색 설정")

# 이동평균선 직접 입력
ma_period = st.sidebar.number_input(
    "📊 이동평균선 (일)",
    min_value=1,
    max_value=500,
    value=20,
    step=1,
    help="종가가 이 이평선보다 높은 종목을 검색합니다. 예: 20 → 20일 이평선"
)
ma_col = f"SMA{ma_period}"

# 최소 거래량
min_vol = st.sidebar.number_input("📦 최소 거래량", value=100000, step=10000)

# 주가 범위
st.sidebar.markdown("💰 **주가 범위 (원)**")
min_price = st.sidebar.number_input("최소 금액", value=2000, step=500, min_value=0)
max_price = st.sidebar.number_input("최대 금액", value=30000, step=1000, min_value=0)

# ── 검색 함수 ──────────────────────────────────────
def run_scanner(ma_col, min_vol, min_price, max_price):
    count, data = (
        Query()
        .set_markets("korea")
        .select('name', 'description', 'close', 'volume', 'change', ma_col, 'price_52_week_high')
        .where(
            col('volume') > min_vol,
            col('close') > col(ma_col),
            col('close') >= min_price,
            col('close') <= max_price,
        )
        .limit(200)
        .get_scanner_data()
    )
    # 52주 신고가 5% 이내 → pandas 필터
    if data is not None and not data.empty and 'price_52_week_high' in data.columns:
        data = data[data['close'] >= data['price_52_week_high'] * 0.95]
    return data

# ── 차트 URL ───────────────────────────────────────
def get_chart_url(ticker):
    if ":" in str(ticker):
        symbol = ticker
    else:
        symbol = f"KRX:{ticker}"
    return f"https://www.tradingview.com/chart/?symbol={symbol}"

# ── 검색 실행 ──────────────────────────────────────
if st.button("🔍 종목 검색 시작", use_container_width=True):
    if min_price >= max_price:
        st.error("최소 금액이 최대 금액보다 작아야 합니다.")
    else:
        with st.spinner("분석 중... 잠시만 기다려주세요."):
            try:
                data = run_scanner(ma_col, min_vol, min_price, max_price)

                if data is not None and not data.empty:
                    st.success(f"✅ 조건에 맞는 종목 {len(data)}개를 찾았습니다!")

                    # 표시용 데이터프레임 구성
                    display_cols = [c for c in ['description', 'name', 'close', 'volume', 'change', ma_col, 'price_52_week_high'] if c in data.columns]
                    display = data[display_cols].copy()

                    rename_map = {
                        'description': '종목명',
                        'name': '종목코드',
                        'close': '현재가(원)',
                        'volume': '거래량',
                        'change': '등락률(%)',
                        ma_col: f'{ma_period}일 이평선',
                        'price_52_week_high': '52주 신고가',
                    }
                    display.rename(columns=rename_map, inplace=True)

                    fmt_cols = {}
                    for old, new in rename_map.items():
                        if old in ['close', ma_col, 'price_52_week_high']:
                            fmt_cols[new] = "{:,.0f}"
                        elif old == 'change':
                            fmt_cols[new] = "{:.2f}"
                        elif old == 'volume':
                            fmt_cols[new] = "{:,.0f}"

                    st.dataframe(
                        display.style.format(fmt_cols),
                        use_container_width=True,
                        hide_index=True
                    )

                    # 차트 바로가기 버튼
                    st.subheader("📊 차트 바로가기")
                    cols_ui = st.columns(5)
                    for i, (_, row) in enumerate(data.iterrows()):
                        ticker = row.get('ticker', row.get('name', ''))
                        # 한글명 있으면 버튼에 표시
                        label = row.get('description', ticker) or ticker
                        url = get_chart_url(ticker)
                        with cols_ui[i % 5]:
                            st.link_button(f"📈 {label}", url, use_container_width=True)

                else:
                    st.warning("⚠️ 조건에 맞는 종목이 현재 없습니다. 조건을 완화해 보세요.")

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

st.divider()
st.caption("본 프로그램은 트레이딩뷰의 공개 데이터를 활용하며 투자 권유를 목적으로 하지 않습니다.")
