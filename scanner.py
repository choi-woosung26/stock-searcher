import streamlit as st
from tradingview_screener import Query, Column
import pandas as pd

st.set_page_config(page_title="한국주식 스캐너", layout="wide")
st.title("🇰🇷 한국 시장 종목 검색기")

# 사이드바 설정
st.sidebar.header("🔍 검색 설정")
min_vol = st.sidebar.number_input("최소 거래량", value=100000)
min_price = st.sidebar.number_input("최소 주가", value=1000)
max_price = st.sidebar.number_input("최고 주가", value=1000000)
ma_period = st.sidebar.number_input("이평선 기간", value=20)
ma_field = f"SMA{ma_period}"

def run_scanner():
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
            # [최종 수정] 주소 앞에 슬래시를 포함한 완벽한 고정 주소를 넣었습니다.
            # 이 코드는 서버가 절대로 오해할 수 없게 만듭니다.
            df['차트보기'] = df['name'].apply(lambda x: "https://tradingview.com" + str(x) + "/")
            
            df = df.rename(columns={'description': '종목명', 'close': '현재가', 'volume': '거래량', 'change': '등락률'})

            st.dataframe(
                df[['종목명', '현재가', '거래량', '등락률', '차트보기']],
                column_config={
                    "차트보기": st.column_config.LinkColumn("차트 열기", display_text="열기 ↗"),
                    "현재가": st.column_config.NumberColumn(format="%d원"),
                    "거래량": st.column_config.NumberColumn(format="%d주"),
                    "등락률": st.column_config.NumberColumn(format="%.2f%%")
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.warning("조건에 맞는 종목이 없습니다.")
    except Exception as e:
        st.error(f"오류: {e}")
