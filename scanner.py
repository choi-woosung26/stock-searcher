import streamlit as st
from tradingview_screener import Query, Column
import pandas as pd

st.set_page_config(page_title="한국주식 스캐너", layout="wide")
st.title("🇰🇷 한국 시장 종목 검색기 (최종 링크 수정)")

# 사이드바
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
            # [방법 변경] 일반 주소가 아닌 트레이딩뷰의 차트 위젯 주소를 사용합니다.
            # 이 주소는 중간에 ?가 들어가서 브라우저가 숫자를 주소로 오해하지 못하게 합니다.
            def make_safe_link(ticker):
                return f"https://tradingview.com:{ticker}"

            df['차트보기'] = df['name'].apply(make_safe_link)
            df = df.rename(columns={'description': '종목명', 'close': '현재가', 'volume': '거래량', 'change': '등락률'})
            
            # 이번에는 st.dataframe 대신 링크가 가장 잘 작동하는 마크다운 테이블을 사용합니다.
            st.write("### 검색 결과")
            st.info("💡 종목별 '차트보기' 링크를 클릭하세요.")
            
            # 마크다운 방식으로 링크를 띄워 브라우저가 새 주소임을 인식하게 함
            for i, row in df.iterrows():
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                with col1:
                    st.markdown(f"**[{row['종목명']}]({row['차트보기']})**")
                with col2:
                    st.text(f"{row['현재가']:,}원")
                with col3:
                    st.text(f"{row['등락률']:+.2f}%")
                with col4:
                    st.link_button("차트열기", row['차트보기'])
            
        else:
            st.warning("조건에 맞는 종목이 없습니다.")
    except Exception as e:
        st.error(f"오류: {e}")
