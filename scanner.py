import streamlit as st
from tradingview_screener import Query, Column
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="국내주식 조건 검색기", page_icon="🇰🇷", layout="wide")
st.title("🇰🇷 한국 시장 전용 종목 검색기")
st.markdown("이동평균선(20일), 볼린저밴드 상단 돌파, 대량 거래 종목을 실시간으로 검색합니다.")

# 2. 사이드바 검색 조건 (한국 시장 고정)
st.sidebar.header("🔍 검색 필터")
min_vol = st.sidebar.number_input("최소 거래량 (주)", value=100000, step=10000)
min_price = st.sidebar.number_input("최소 주가 (원)", value=1000, step=500)

def run_scanner():
    # 'korea' 시장으로 고정하고 에러 없는 필드들만 선택
    # 한국 서버에서 'high_52_week' 관련 에러가 잦아 이를 제외하고 안정성을 높였습니다.
    q = Query().set_markets('korea').select(
        'name', 'close', 'volume', 'change', 'SMA20', 'BB.upper'
    )
    
    # 조건 설정
    q = q.where(
        Column('volume') > min_vol,
        Column('close') >= min_price,
        Column('close') > Column('SMA20'),      # 20일 이평선 위
        Column('close') > Column('BB.upper'),   # 볼린저밴드 상단 돌파
        Column('change') > 0                    # 당일 양봉 종목
    )
    
    # 데이터 가져오기
    _, df = q.get_scanner_data()
    return df

# 3. 실행 버튼
if st.button("🚀 한국 종목 검색 시작"):
    with st.spinner("한국 거래소(KRX) 데이터를 분석 중입니다..."):
        try:
            df = run_scanner()
            
            if df is not None and not df.empty:
                st.success(f"조건에 맞는 한국 종목 {len(df)}개를 찾았습니다!")
                
                # 표 제목 한글화
                df.columns = ['종목명', '현재가', '거래량', '등락률', '20일이평', 'BB상단']
                
                # 데이터 포맷 변경 (천단위 콤마 등)
                st.dataframe(df.style.format({
                    '현재가': '{:,.0f}',
                    '거래량': '{:,.0f}',
                    '등락률': '{:+.2f}%',
                    '20일이평': '{:,.0f}',
                    'BB상단': '{:,.0f}'
                }), use_container_width=True)
                
            else:
                st.warning("조건에 맞는 종목이 없습니다. 최소 거래량이나 주가 조건을 낮춰보세요.")
                
        except Exception as e:
            st.error(f"⚠️ 데이터 연동 오류: {e}")
            st.info("트레이딩뷰 서버 응답에 문제가 있을 수 있습니다. 잠시 후 다시 시도해 주세요.")

st.divider()
st.caption("제공되는 데이터는 트레이딩뷰 공개 데이터를 기반으로 하며 투자 권유가 아닙니다.")
