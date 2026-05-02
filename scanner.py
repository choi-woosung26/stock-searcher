import streamlit as st
from tradingview_screener import Query, Column
import pandas as pd

st.set_page_config(page_title="한국주식 스캐너", layout="wide")
st.title("🇰🇷 한국 시장 종목 검색기 (HTML 링크 버전)")

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
            # [최종 해결책] 텍스트 기반의 HTML 링크를 생성합니다.
            # 이 방식은 Streamlit의 LinkColumn 버그를 완전히 무시합니다.
            def make_html_link(ticker):
                url = f"https://tradingview.com{ticker}/"
                return f'<a href="{url}" target="_blank">차트열기 ↗</a>'

            df['차트보기'] = df['name'].apply(make_html_link)
            df = df.rename(columns={'description': '종목명', 'close': '현재가', 'volume': '거래량', 'change': '등락률'})
            
            # 보기 좋게 컬럼 순서 조정
            display_df = df[['종목명', '현재가', '거래량', '등락률', '차트보기']]

            # 일반 표(st.write) 대신 HTML을 지원하는 형태로 출력
            st.write("💡 **차트열기** 파란색 글자를 클릭하세요. (안 되면 마우스 우클릭 -> 새 탭에서 열기)")
            st.write(display_df.to_html(escape=False, index=False), unsafe_allow_html=True)
            
        else:
            st.warning("조건에 맞는 종목이 없습니다.")
    except Exception as e:
        st.error(f"오류: {e}")
