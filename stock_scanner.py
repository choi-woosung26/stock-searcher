import streamlit as st
from tradingview_screener import Query, col
import pandas as pd

st.set_page_config(page_title="주식 스캐너", page_icon="📈", layout="wide")

st.title("📈 내 전용 종목 검색기")
st.markdown("트레이딩뷰 데이터를 활용해 **이평선 돌파, 볼린저밴드 상단 이탈, 신고가** 종목을 찾습니다.")

st.sidebar.header("🔍 검색 설정")
market = st.sidebar.selectbox("대상 시장", ["KOREA", "AMERICA"], index=0)
min_vol = st.sidebar.number_input("최소 거래량", value=100000, step=10000)

def run_scanner(market, min_vol):
    market_key = "korea" if market == "KOREA" else "america"
    count, data = (
        Query()
        .set_markets(market_key)
        .select('name', 'close', 'volume', 'change', 'SMA20', 'BB.upper', 'high_52week')
        .where(
            col('volume') > min_vol,
            col('close') > col('SMA20'),    # 20일 이평선 위
            col('close') > col('BB.upper'), # 볼린저밴드 상단 돌파
            # 신고가 근처는 검색 후 파이썬으로 필터링
        )
        .limit(200)
        .get_scanner_data()
    )
    # 52주 신고가 5% 이내 → 파이썬에서 직접 필터
    if data is not None and not data.empty and 'high_52week' in data.columns:
        data = data[data['close'] >= data['high_52week'] * 0.95]
    return count, data

def get_chart_url(ticker, market):
    if ":" in str(ticker):
        return f"https://www.tradingview.com/chart/?symbol={ticker}"
    elif market == "KOREA":
        return f"https://www.tradingview.com/chart/?symbol=KRX:{ticker}"
    else:
        return f"https://www.tradingview.com/chart/?symbol={ticker}"

if st.button("종목 검색 시작"):
    with st.spinner("분석 중... 잠시만 기다려주세요."):
        try:
            count, data = run_scanner(market, min_vol)

            if data is not None and not data.empty:
                st.success(f"조건에 맞는 종목 {len(data)}개를 찾았습니다!")

                display_cols = [c for c in ['name', 'close', 'volume', 'change', 'SMA20', 'BB.upper', 'high_52week'] if c in data.columns]
                fmt_cols = {c: "{:.2f}" for c in ['close', 'change', 'SMA20', 'BB.upper'] if c in data.columns}
                st.dataframe(
                    data[display_cols].style.format(fmt_cols),
                    use_container_width=True
                )

                st.subheader("📊 차트 바로가기")
                cols_ui = st.columns(4)
                for i, (_, row) in enumerate(data.iterrows()):
                    ticker = row.get('ticker', row.get('name', ''))
                    url = get_chart_url(ticker, market)
                    with cols_ui[i % 4]:
                        st.link_button(f"📈 {ticker}", url)
            else:
                st.warning("조건에 맞는 종목이 현재 없습니다.")

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

st.divider()
st.caption("본 프로그램은 트레이딩뷰의 공개 데이터를 활용하며 투자 권유를 목적으로 하지 않습니다.")
