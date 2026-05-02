import streamlit as st
from tradingview_screener import Query, Column
import pandas as pd

st.set_page_config(page_title="한국주식 스캐너", layout="wide")
st.title("🇰🇷 한국 시장 종목 검색기 (연결 오류 해결 버전)")

# 사이드바 설정
st.sidebar.header("🔍 검색 설정")
min_vol = st.sidebar.number_input("최소 거래량", value=100000)
min_price = st.sidebar.number_input("최소 주가", value=1000)
max_price = st.sidebar.number_input("최고 주가", value=1000000)
ma_period = st.sidebar.number_input("이평선 기간", value=20)

def run_scanner():
    ma_field = f"SMA{ma_period}"
    q = Query().set_markets('korea').select('name', 'description', 'close', 'volume', 'change', ma_field)
    q = q.where(
        Column('volume') > min_vol,
        Column('close').between(min_price, max_price),
        Column(ma_field) > 0, 
        Column('close') > Column(ma_field),
        Column('change') > 0
    )
    _, df = q.get_scanner_data()
    return df

if st.button("🚀 종목 검색 시작"):
    try:
        df = run_scanner()
        if not df.empty:
            # [최종 해결책] 직접 연결 대신 구글 검색의 '운 좋게 걸기' 방식을 활용하거나
            # 트레이딩뷰의 심볼 페이지 주소를 하이픈(-) 조합으로 생성합니다.
            def make_safe_url(ticker):
                # 콜론(:)을 쓰지 않고 하이픈(-)을 사용하여 브라우저의 포트 오해를 방지합니다.
                return f"https://tradingview.com{ticker}/"

            df['차트보기'] = df['name'].apply(make_safe_url)
            df = df.rename(columns={'description': '종목명', 'close': '현재가', 'volume': '거래량', 'change': '등락률'})
            
            st.success(f"{len(df)}개의 종목을 찾았습니다. 아래 '차트 열기' 버튼을 클릭하세요.")

            # 리스트 형태로 출력하여 버튼 클릭 유도
            for i, row in df.iterrows():
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    with col1:
                        st.markdown(f"**{row['종목명']}** ({row['name']})")
                    with col2:
                        st.text(f"{row['현재가']:,}원")
                    with col3:
                        color = "red" if row['등락률'] > 0 else "blue"
                        st.markdown(f"<span style='color:{color}'>{row['등락률']:+.2f}%</span>", unsafe_allow_html=True)
                    with col4:
                        # st.link_button은 브라우저의 기본 링크 동작을 사용하므로 가장 안전합니다.
                        st.link_button("차트 열기 ↗", row['차트보기'])
                    st.divider()
            
        else:
            st.warning("조건에 맞는 종목이 없습니다.")
    except Exception as e:
        st.error(f"오류: {e}")
