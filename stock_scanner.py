import streamlit as st
from tradingview_screener import Query, col
import pandas as pd
from pykrx import stock
from datetime import datetime

st.set_page_config(page_title="주식 스캐너", page_icon="📈", layout="wide")

st.title("📈 한국 주식 종목 검색기")
st.markdown("이동평균선 돌파 · 신고가 근처 종목을 찾습니다.")

# ── 한글 종목명 + ETF/스팩 제외 목록 로딩 ─────────────────
@st.cache_data(ttl=3600)  # 1시간 캐시 (매번 호출 방지)
def load_krx_info():
    today = datetime.today().strftime("%Y%m%d")
    try:
        # KOSPI + KOSDAQ 전체 종목
        kospi  = stock.get_market_ticker_list(today, market="KOSPI")
        kosdaq = stock.get_market_ticker_list(today, market="KOSDAQ")
        all_tickers = list(kospi) + list(kosdaq)

        # ETF 목록
        etf_tickers = set(stock.get_etf_ticker_list(today))

        # 종목코드 → 한글명 딕셔너리
        name_map = {}
        exclude_set = set()  # 제외할 종목코드

        for ticker in all_tickers:
            name = stock.get_market_ticker_name(ticker)
            name_map[ticker] = name

            # ETF 제외
            if ticker in etf_tickers:
                exclude_set.add(ticker)
                continue

            # 스팩(SPAC) 제외: 종목명에 '스팩' 포함
            if '스팩' in name:
                exclude_set.add(ticker)
                continue

            # 우선주 제외: 종목코드 끝자리가 5 (예: 005935 삼성전자우)
            if ticker.endswith('5') and len(ticker) == 6:
                exclude_set.add(ticker)
                continue

            # 기타 제외 키워드: 리츠, 인프라, 선박, 증권, 금융
            exclude_keywords = ['리츠', 'REIT', '인프라', '선박투자', '환기', '수익증권']
            if any(kw in name for kw in exclude_keywords):
                exclude_set.add(ticker)

        return name_map, exclude_set
    except Exception as e:
        st.warning(f"종목 정보 로딩 실패 (한글명 미표시): {e}")
        return {}, set()

# ── 사이드바 설정 ──────────────────────────────────
st.sidebar.header("🔍 검색 설정")

ma_period = st.sidebar.number_input(
    "📊 이동평균선 (일)",
    min_value=1, max_value=500, value=20, step=1,
    help="종가가 이 이평선보다 높은 종목을 검색합니다."
)
ma_col = f"SMA{ma_period}"

min_vol = st.sidebar.number_input("📦 최소 거래량", value=100000, step=10000)

st.sidebar.markdown("💰 **주가 범위 (원)**")
min_price = st.sidebar.number_input("최소 금액", value=2000, step=500, min_value=0)
max_price = st.sidebar.number_input("최대 금액", value=30000, step=1000, min_value=0)

# ── 검색 함수 ──────────────────────────────────────
def run_scanner(ma_col, min_vol, min_price, max_price):
    count, data = (
        Query()
        .set_markets("korea")
        .select('name', 'close', 'volume', 'change', ma_col, 'price_52_week_high')
        .where(
            col('volume') > min_vol,
            col('close') > col(ma_col),
            col('close') >= min_price,
            col('close') <= max_price,
        )
        .limit(300)
        .get_scanner_data()
    )
    # 52주 신고가 5% 이내 필터
    if data is not None and not data.empty and 'price_52_week_high' in data.columns:
        data = data[data['close'] >= data['price_52_week_high'] * 0.95]
    return data

def get_chart_url(ticker):
    symbol = ticker if ":" in str(ticker) else f"KRX:{ticker}"
    return f"https://www.tradingview.com/chart/?symbol={symbol}"

# ── 검색 실행 ──────────────────────────────────────
if st.button("🔍 종목 검색 시작", use_container_width=True):
    if min_price >= max_price:
        st.error("최소 금액이 최대 금액보다 작아야 합니다.")
    else:
        with st.spinner("종목 정보 및 데이터 로딩 중..."):
            name_map, exclude_set = load_krx_info()

        with st.spinner("조건에 맞는 종목 검색 중..."):
            try:
                data = run_scanner(ma_col, min_vol, min_price, max_price)

                if data is not None and not data.empty:

                    # 종목코드 추출 (name 컬럼: "KRX:005930" 형태)
                    def extract_code(name_val):
                        if ':' in str(name_val):
                            return str(name_val).split(':')[-1]
                        return str(name_val)

                    data['종목코드'] = data['name'].apply(extract_code)

                    # ETF·스팩·우선주 등 제외
                    before = len(data)
                    data = data[~data['종목코드'].isin(exclude_set)]
                    after = len(data)

                    # 한글 종목명 매핑
                    data['종목명'] = data['종목코드'].map(name_map).fillna(data['name'])

                    if data.empty:
                        st.warning("⚠️ 조건에 맞는 종목이 없습니다. 조건을 완화해 보세요.")
                    else:
                        st.success(f"✅ {after}개 종목 발견  (ETF·스팩·우선주 등 {before - after}개 제외)")

                        # 표시용 컬럼 정리
                        show_cols = ['종목명', '종목코드', 'close', 'volume', 'change', ma_col, 'price_52_week_high']
                        show_cols = [c for c in show_cols if c in data.columns]
                        display = data[show_cols].copy()
                        display.rename(columns={
                            'close': '현재가(원)',
                            'volume': '거래량',
                            'change': '등락률(%)',
                            ma_col: f'{ma_period}일 이평선',
                            'price_52_week_high': '52주 신고가',
                        }, inplace=True)

                        fmt = {
                            '현재가(원)': '{:,.0f}',
                            '거래량': '{:,.0f}',
                            '등락률(%)': '{:.2f}',
                            f'{ma_period}일 이평선': '{:,.0f}',
                            '52주 신고가': '{:,.0f}',
                        }
                        st.dataframe(
                            display.style.format(fmt),
                            use_container_width=True,
                            hide_index=True
                        )

                        # 차트 바로가기 버튼
                        st.subheader("📊 차트 바로가기")
                        cols_ui = st.columns(5)
                        for i, (_, row) in enumerate(data.iterrows()):
                            ticker = row['name']
                            label = row['종목명']
                            url = get_chart_url(ticker)
                            with cols_ui[i % 5]:
                                st.link_button(f"📈 {label}", url, use_container_width=True)

                else:
                    st.warning("⚠️ 조건에 맞는 종목이 현재 없습니다.")

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

st.divider()
st.caption("본 프로그램은 트레이딩뷰 및 KRX 공개 데이터를 활용하며 투자 권유를 목적으로 하지 않습니다.")
