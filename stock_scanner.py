import streamlit as st
from tradingview_screener import Query, Column

st.set_page_config(page_title="한국주식 스캐너", layout="wide")
st.title("🇰🇷 한국 시장 종목 검색기 (버전 5.2 - 캐시 강제 삭제)")

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
            st.success(f"{len(df)}개의 종목을 찾았습니다.")
            
            for i, row in df.iterrows():
                # [필살기] 주소 뒤에 의미 없는 숫자를 붙여 브라우저가 매번 새 주소로 인식하게 함
                # 주소 형식을 차트 전용 파라미터 방식으로 변경
                safe_url = f"https://tradingview.com:{row['name']}&refresh=true"
                
                cols = st.columns(4)
                with cols[0]:
                    st.markdown(f"**{row['description']}**")
                with cols[1]:
                    st.text(f"{row['close']:,}원")
                with cols[2]:
                    st.text(f"{row['change']:+.2f}%")
                with cols[3]:
                    # 링크 버튼을 통해 새 창 열기 유도
                    st.link_button("차트 열기 ↗", safe_url)
                st.divider()
        else:
            st.warning("조건에 맞는 종목이 없습니다.")
    except Exception as e:
        st.error(f"오류: {e}")
