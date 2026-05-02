import streamlit as st
from tradingview_screener import Query, Column
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="한국주식 스캐너", page_icon="📈", layout="wide")
st.title("🇰🇷 한국 시장 종목 검색기")

# 2. 사이드바 설정
st.sidebar.header("🔍 검색 설정")
min_vol = st.sidebar.number_input("최소 거래량", value=100000, step=10000)
min_price = st.sidebar.number_input("최소 주가", value=1000, step=500)
max_price = st.sidebar.number_input("최고 주가", value=1000000, step=10000)
ma_period = st.sidebar.number_input("이평선 기간", value=20, min_value=1)
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

# 3. 메인 실행 버튼
if st.button("🚀 종목 검색 시작"):
    with st.spinner("최신 데이터를 불러오는 중..."):
        try:
            df = run_scanner()
            if not df.empty:
                # [수정] 트레이딩뷰 차트 주소를 더 명확하게 생성
                # 예: https://tradingview.com
                df['차트보기'] = df['name'].apply(lambda x: f"https://tradingview.com{x}/")
                
                # 컬럼명 변경
                df = df.rename(columns={'description': '종목명', 'close': '현재가', 'volume': '거래량', 'change': '등락률'})
                
                st.success(f"{len(df)}개의 종목을 찾았습니다. 종목명을 클릭하거나 차트 링크를 눌러보세요.")

                # [필살기] 데이터 프레임 출력 방식을 가장 안정적인 버전으로 변경
                st.dataframe(
                    df[['종목명', '현재가', '거래량', '등락률', '차트보기']],
                    column_config={
                        "차트보기": st.column_config.LinkColumn(
                            "차트 열기", 
                            display_text="여기 클릭 ↗",
                            validate=r"^https://.*" # URL 유효성 검사 추가
                        ),
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
st.info("💡 데스크탑 팁: '여기 클릭' 위에서 '마우스 휠(가운데 버튼)'을 누르면 새 탭으로 즉시 열립니다.")
