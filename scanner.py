import streamlit as st
from tradingview_screener import Query, Column
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="한국주식 이평선 스캐너", page_icon="📈", layout="wide")
st.title("🇰🇷 한국 시장 이동평균선 검색기")
st.write("💡 아래 표의 '차트보기' 링크를 클릭하면 트레이딩뷰 차트가 새 창에서 열립니다.")

# 2. 사이드바 검색 조건
st.sidebar.header("🔍 검색 및 지표 설정")
min_vol = st.sidebar.number_input("최소 거래량 (주)", value=100000, step=10000)
min_price = st.sidebar.number_input("최소 주가 (원)", value=1000, step=500)
ma_period = st.sidebar.number_input("이동평균선 기간 (예: 20, 60, 120)", value=20, min_value=1, max_value=300)
ma_field = f"SMA{ma_period}"

def run_scanner():
    q = Query().set_markets('korea').select('name', 'close', 'volume', 'change', ma_field)
    q = q.where(
        Column('volume') > min_vol,
        Column('close') >= min_price,
        Column(ma_field) > 0, 
        Column('close') > Column(ma_field),
        Column('change') > 0
    )
    _, df = q.get_scanner_data()
    return df

# 3. 실행 버튼
if st.button("🚀 조건 검색 시작"):
    with st.spinner("데이터 분석 중..."):
        try:
            df = run_scanner()
            if df is not None and not df.empty:
                st.success(f"조건에 맞는 종목 {len(df)}개를 찾았습니다!")

                # 티커(name) 정보를 이용해 직접 링크 주소 생성
                # KRX:티커 주소 형식을 정확히 맞춤
                def get_link(ticker, interval):
                    return f"https://tradingview.com:{ticker}&interval={interval}"

                df['차트보기'] = df['name'].apply(lambda x: get_link(x, 'D'))
                df['주봉'] = df['name'].apply(lambda x: get_link(x, 'W'))
                df['월봉'] = df['name'].apply(lambda x: get_link(x, 'M'))

                # 컬럼 이름 변경
                rename_map = {'name': '종목티커', 'close': '현재가', 'volume': '거래량', 'change': '등락률', ma_field: f'{ma_period}일이평'}
                df = df.rename(columns=rename_map)

                # 링크가 작동하도록 컬럼 설정 (st.dataframe 대신 st.column_config 사용)
                st.dataframe(
                    df,
                    column_config={
                        "차트보기": st.column_config.LinkColumn("일봉 차트", display_text="차트 열기"),
                        "주봉": st.column_config.LinkColumn("주봉", display_text="보기"),
                        "월봉": st.column_config.LinkColumn("월봉", display_text="보기"),
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
            st.error(f"오류 발생: {e}")

st.divider()
st.info("스마트폰에서는 '차트 열기' 글자를 정확히 터치해 주세요.")
