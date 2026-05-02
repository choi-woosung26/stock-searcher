import streamlit as st
from tradingview_screener import Query, Column
import pandas as pd

# 앱 제목과 아이콘
st.set_page_config(page_title="주식 스캐너", page_icon="📈", layout="wide")

st.title("📈 내 전용 종목 검색기")
st.markdown("트레이딩뷰 데이터를 활용해 **이평선 돌파, 볼린저밴드 상단 이탈, 신고가** 종목을 찾습니다.")

# 사이드바 설정
st.sidebar.header("🔍 검색 설정")
market = st.sidebar.selectbox("대상 시장", ["KOREA", "AMERICA"], index=0)
min_vol = st.sidebar.number_input("최소 거래량", value=100000, step=10000)

# 검색 실행 함수
def run_scanner():
    q = Query().from_(market.lower()).select(
        'name', 'close', 'volume', 'change', 'SMA20', 'BB.upper', 'high_52week'
    )
    
    # 조건 설정
    q = q.where(
        Column('volume') > min_vol,
        Column('close') > Column('SMA20'),      # 20일 이평선 위
        Column('close') > Column('BB.upper'),   # 볼린저밴드 상단 돌파
        Column('close') >= Column('high_52week') * 0.95  # 52주 신고가 근처(5% 이내)
    )
    
    return q.get_scanner_data()

# 차트 URL 생성 함수
def get_chart_url(ticker, market):
    if market == "KOREA":
        return f"https://www.tradingview.com/chart/?symbol=KRX:{ticker}"
    else:
        return f"https://www.tradingview.com/chart/?symbol={ticker}"

# 버튼 클릭
if st.button("종목 검색 시작"):
    with st.spinner("분석 중... 잠시만 기다려주세요."):
        try:
            count, data = run_scanner()  # ← 튜플로 반환됩니다
            if data is not None and not data.empty:
                st.success(f"조건에 맞는 종목 {len(data)}개를 찾았습니다!")

                # 차트 링크 열 추가
                data['차트'] = data['name'].apply(
                    lambda ticker: f"[📊 차트 열기](https://www.tradingview.com/chart/?symbol={'KRX:' if market == 'KOREA' else ''}{ticker})"
                )

                # 표 출력
                st.dataframe(
                    data.style.format(
                        subset=['close', 'change', 'SMA20', 'BB.upper'],
                        formatter="{:.2f}"
                    ),
                    use_container_width=True
                )

                # 차트 바로가기 버튼 목록
                st.subheader("📊 차트 바로가기")
                cols = st.columns(4)  # 한 줄에 4개씩 배치
                for i, (_, row) in enumerate(data.iterrows()):
                    ticker = row['name']
                    url = get_chart_url(ticker, market)
                    with cols[i % 4]:
                        st.link_button(f"📈 {ticker}", url)

            else:
                st.warning("조건에 맞는 종목이 현재 없습니다.")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

st.divider()
st.caption("본 프로그램은 트레이딩뷰의 공개 데이터를 활용하며 투자 권유를 목적으로 하지 않습니다.")
