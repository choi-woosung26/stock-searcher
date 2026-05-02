import streamlit as st
from tradingview_screener import Query, Column
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="한국주식 이평선 스캐너", page_icon="📈", layout="wide")
st.title("🇰🇷 한국 시장 가격대별 종목 검색기")
st.write("💡 설정한 가격 범위 내에서 이동평균선을 돌파한 종목을 찾습니다.")

# 2. 사이드바 검색 조건
st.sidebar.header("🔍 검색 및 지표 설정")
min_vol = st.sidebar.number_input("최소 거래량 (주)", value=100000, step=10000)

# 가격 범위 설정 (최소 ~ 최고)
st.sidebar.subheader("💰 가격대 설정 (원)")
min_price = st.sidebar.number_input("최소 주가", value=1000, step=500)
max_price = st.sidebar.number_input("최고 주가", value=1000000, step=10000)

# 이동평균선 설정
ma_period = st.sidebar.number_input("이동평균선 기간 (예: 20, 60, 120)", value=20, min_value=1, max_value=300)
ma_field = f"SMA{ma_period}"

def run_scanner():
    q = Query().set_markets('korea').select('name', 'close', 'volume', 'change', ma_field)
    
    # 필터 조건: 거래량 + 가격범위(min~max) + 이평선 돌파
    q = q.where(
        Column('volume') > min_vol,
        Column('close') >= min_price,          # 최소 주가 이상
        Column('close') <= max_price,          # 최고 주가 이하
        Column(ma_field) > 0, 
        Column('close') > Column(ma_field),    # 이평선 위
        Column('change') > 0                   # 당일 상승
    )
    _, df = q.get_scanner_data()
    return df

# 3. 실행 버튼
if st.button("🚀 조건 검색 시작"):
    with st.spinner("가격을 분석 중입니다..."):
        try:
            df = run_scanner()
            if df is not None and not df.empty:
                st.success(f"{min_price:,}원 ~ {max_price:,}원 사이 종목 {len(df)}개를 찾았습니다!")

                # 차트 링크 생성
                def get_link(ticker, interval):
                    return f"https://tradingview.com:{ticker}&interval={interval}"

                df['차트보기'] = df['name'].apply(lambda x: get_link(x, 'D'))
                df['주봉'] = df['name'].apply(lambda x: get_link(x, 'W'))
                df['월봉'] = df['name'].apply(lambda x: get_link(x, 'M'))

                # 컬럼 이름 변경
                rename_map = {'name': '종목티커', 'close': '현재가', 'volume': '거래량', 'change': '등락률', ma_field: f'{ma_period}일이평'}
                df = df.rename(columns=rename_map)

                # 결과 출력
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
                st.warning(f"{min_price:,}원 ~ {max_price:,}원 범위에 조건에 맞는 종목이 없습니다.")
        except Exception as e:
            st.error(f"오류 발생: {e}")

st.divider()
st.info("원하는 주가 범위를 입력하고 검색 버튼을 다시 눌러주세요.")
