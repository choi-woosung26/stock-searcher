import streamlit as st
from tradingview_screener import Query, Column
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="한국주식 이평선 스캐너", page_icon="📈", layout="wide")
st.title("🇰🇷 한국 시장 이동평균선 검색기")

# 2. 사이드바 검색 조건
st.sidebar.header("🔍 검색 및 지표 설정")
min_vol = st.sidebar.number_input("최소 거래량 (주)", value=100000, step=10000)
min_price = st.sidebar.number_input("최소 주가 (원)", value=1000, step=500)

# 이동평균선 기간 조절 창
ma_period = st.sidebar.number_input("이동평균선 기간 (예: 20, 60, 120)", value=20, min_value=1, max_value=300)
ma_field = f"SMA{ma_period}"

def run_scanner():
    # 볼린저 밴드(BB.upper)를 제외하고 데이터를 가져옵니다.
    q = Query().set_markets('korea').select(
        'name', 'close', 'volume', 'change', ma_field
    )
    
    q = q.where(
        Column('volume') > min_vol,
        Column('close') >= min_price,
        Column(ma_field) > 0, 
        Column('close') > Column(ma_field), # 설정한 이평선 위에 있는 종목만
        Column('change') > 0                # 오늘 상승 중인 종목만
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
                
                # 차트 링크 생성 함수
                def make_tv_link(ticker, interval):
                    return f"https://tradingview.com:{ticker}&interval={interval}"

                # 링크 데이터 추가
                df['일봉'] = df['name'].apply(lambda x: make_tv_link(x, 'D'))
                df['주봉'] = df['name'].apply(lambda x: make_tv_link(x, 'W'))
                df['월봉'] = df['name'].apply(lambda x: make_tv_link(x, 'M'))
                df['년봉'] = df['name'].apply(lambda x: make_tv_link(x, '12M'))

                # 컬럼 이름 매핑 (볼린저 밴드 제외)
                rename_map = {
                    'name': '티커',
                    'close': '현재가',
                    'volume': '거래량',
                    'change': '등락률',
                    ma_field: f'{ma_period}일이평'
                }
                df = df.rename(columns=rename_map)

                # 표 출력
                st.data_editor(
                    df,
                    column_config={
                        "일봉": st.column_config.LinkColumn("일봉", display_text="보기"),
                        "주봉": st.column_config.LinkColumn("주봉", display_text="보기"),
                        "월봉": st.column_config.LinkColumn("월봉", display_text="보기"),
                        "년봉": st.column_config.LinkColumn("년봉", display_text="보기"),
                        "현재가": st.column_config.NumberColumn(format="%d원"),
                        "거래량": st.column_config.NumberColumn(format="%d주"),
                        "등락률": st.column_config.NumberColumn(format="%.2f%%")
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.warning("조건에 맞는 종목이 없습니다. 필터 수치를 조절해 보세요.")
                
        except Exception as e:
            st.error(f"오류 발생: {e}")
            st.info("데이터를 불러오는 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.")

st.divider()
st.caption("볼린저 밴드 조건이 제거되었습니다. 이제 이평선 돌파 종목 위주로 검색됩니다.")
