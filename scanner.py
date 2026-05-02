import streamlit as st
from tradingview_screener import Query, Column
import pandas as pd

st.set_page_config(page_title="360일 신고가 스캐너", layout="wide")
st.title("📈 360일(1년) 신고가 & 지표 검색기")

# 사이드바 설정
st.sidebar.header("🔍 검색 설정")
market_choice = st.sidebar.selectbox("대상 시장", ["korea", "america"], index=0)
min_vol = st.sidebar.number_input("최소 거래량", value=100000)

def run_scanner():
    # 'high_52_week_high'는 1년(약 360일 내외) 동안의 최고가를 의미하는 표준 필드입니다.
    q = Query().set_markets(market_choice).select(
        'name', 'close', 'volume', 'change', 'SMA20', 'BB.upper', 'high_52_week_high'
    )
    
    # 조건 설정
    q = q.where(
        Column('volume') > min_vol,
        Column('close') > Column('SMA20'),
        Column('close') > Column('BB.upper'),
        # 현재가가 1년 최고가와 같거나 큰 경우 (신고가 경신)
        Column('close') >= Column('high_52_week_high')
    )
    
    _, df = q.get_scanner_data()
    return df

if st.button("종목 검색 시작"):
    with st.spinner("360일 신고가 종목 분석 중..."):
        try:
            df = run_scanner()
            
            if df is not None and not df.empty:
                st.success(f"신고가 경신 중인 {len(df)}개의 종목을 찾았습니다!")
                df.columns = ['티커', '현재가', '거래량', '변동률', '20일이평', 'BB상단', '1년최고가']
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("조건에 맞는 신고가 종목이 없습니다. 최소 거래량을 낮춰보세요.")
        except Exception as e:
            st.error(f"오류 발생: {e}")
            st.info("💡 만약 'Unknown field' 에러가 또 발생하면 필드명 호환성 문제입니다.")
