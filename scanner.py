import streamlit as st
from tradingview_screener import Query, Column
import pandas as pd

st.set_page_config(page_title="주식 스캐너", layout="wide")
st.title("📈 내 전용 종목 검색기")

# 사이드바 설정
st.sidebar.header("🔍 검색 설정")
market_choice = st.sidebar.selectbox("대상 시장", ["korea", "america"], index=0)
min_vol = st.sidebar.number_input("최소 거래량", value=100000)

def run_scanner():
    # 최신 라이브러리 문법으로 수정
    q = Query().set_markets(market_choice).select('name', 'close', 'volume', 'change', 'SMA20', 'BB.upper', 'high_52week')
    
    # 조건 설정
    q = q.where(
        Column('volume') > min_vol,
        Column('close') > Column('SMA20'),
        Column('close') > Column('BB.upper')
    )
    
    # 데이터 가져오기
    # 최신 버전은 (count, data) 형태의 튜플을 반환하므로 데이터만 추출
    _, df = q.get_scanner_data()
    return df

if st.button("종목 검색 시작"):
    with st.spinner("데이터 분석 중..."):
        try:
            df = run_scanner()
            
            if df is not None and not df.empty:
                st.success(f"{len(df)}개의 종목을 찾았습니다!")
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("조건에 맞는 종목이 없습니다.")
        except Exception as e:
            st.error(f"오류 발생: {e}")
            st.info("최신 라이브러리 문법으로 코드를 수정했습니다. 다시 시도해 보세요.")
