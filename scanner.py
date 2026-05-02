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
    # 필드명을 가장 안전한 기본형으로 변경 (high_52week -> high_52_week)
    q = Query().set_markets(market_choice).select(
        'name', 'close', 'volume', 'change', 'SMA20', 'BB.upper', 'high_52_week'
    )
    
    # 조건 설정
    q = q.where(
        Column('volume') > min_vol,
        Column('close') > Column('SMA20'),
        Column('close') > Column('BB.upper')
    )
    
    # 데이터 가져오기
    _, df = q.get_scanner_data()
    return df

if st.button("종목 검색 시작"):
    with st.spinner("데이터 분석 중..."):
        try:
            df = run_scanner()
            
            if df is not None and not df.empty:
                st.success(f"{len(df)}개의 종목을 찾았습니다!")
                # 컬럼명 한글로 보기 좋게 변경
                df.columns = ['티커', '현재가', '거래량', '변동률', '20일이평', 'BB상단', '52주신고가']
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("조건에 맞는 종목이 없습니다. (필터를 조정해보세요)")
        except Exception as e:
            # 만약 또 필드명 에러가 나면 high_52_week를 제외하고 시도하도록 안내
            st.error(f"오류 발생: {e}")
            st.info("💡 '52주 신고가' 필드명이 시장마다 다를 수 있습니다. 오류가 반복되면 해당 필드를 제거해 드릴게요.")
