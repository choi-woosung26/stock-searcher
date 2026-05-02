import streamlit as st
from tradingview_screener import Query, Column
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="한국주식 멀티 스캐너", page_icon="📈", layout="wide")
st.title("🇰🇷 한국 시장 전용 스마트 검색기")

# 2. 사이드바 검색 조건
st.sidebar.header("🔍 검색 및 지표 설정")
min_vol = st.sidebar.number_input("최소 거래량 (주)", value=100000, step=10000)
min_price = st.sidebar.number_input("최소 주가 (원)", value=1000, step=500)

# 이동평균선 기간 조절 창 추가
ma_period = st.sidebar.number_input("이동평균선 기간 설정 (예: 20, 60, 120)", value=20, min_value=1, max_value=300)
ma_field = f"SMA{ma_period}"  # 트레이딩뷰 필드명 생성 (SMA20, SMA60 등)

def run_scanner():
    # 선택한 이평선 기간을 포함하여 데이터 가져오기
    q = Query().set_markets('korea').select(
        'name', 'close', 'volume', 'change', ma_field, 'BB.upper'
    )
    
    # 조건 설정
    q = q.where(
        Column('volume') > min_vol,
        Column('close') >= min_price,
        Column('close') > Column(ma_field),    # 설정한 이평선 위
        Column('close') > Column('BB.upper'),   # 볼린저밴드 상단 돌파
        Column('change') > 0
    )
    
    _, df = q.get_scanner_data()
    return df

# 3. 실행 버튼 및 결과 출력
if st.button("🚀 조건 검색 시작"):
    with st.spinner("데이터 분석 중..."):
        try:
            df = run_scanner()
            
            if df is not None and not df.empty:
                st.success(f"조건에 맞는 종목 {len(df)}개를 찾았습니다!")
                
                # 4. 차트 링크 생성 함수 (일, 주, 월, 년봉)
                # 트레이딩뷰는 URL 파라미터로 봉 주기를 조절할 수 있습니다.
                def make_tv_link(ticker, interval):
                    # interval: D(일), W(주), M(월), 12M(년)
                    return f"https://tradingview.com:{ticker}&interval={interval}"

                # 각 주기별 링크 컬럼 추가
                df['일봉'] = df['name'].apply(lambda x: make_tv_link(x, 'D'))
                df['주봉'] = df['name'].apply(lambda x: make_tv_link(x, 'W'))
                df['월봉'] = df['name'].apply(lambda x: make_tv_link(x, 'M'))
                df['년봉'] = df['name'].apply(lambda x: make_tv_link(x, '12M'))

                # 컬럼 이름 정리
                df.columns = ['티커', '현재가', '거래량', '등락률', f'{ma_period}일이평', 'BB상단', '일봉차트', '주봉차트', '월봉차트', '년봉차트']

                # 표 출력 (링크 클릭 가능하도록 설정)
                st.write("💡 아래 차트 링크를 클릭하면 트레이딩뷰 차트로 바로 이동합니다.")
                st.data_editor(
                    df,
                    column_config={
                        "일봉차트": st.column_config.LinkColumn("일봉 확인", display_text="보기"),
                        "주봉차트": st.column_config.LinkColumn("주봉 확인", display_text="보기"),
                        "월봉차트": st.column_config.LinkColumn("월봉 확인", display_text="보기"),
                        "년봉차트": st.column_config.LinkColumn("년봉 확인", display_text="보기"),
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.warning("조건에 맞는 종목이 없습니다.")
                
        except Exception as e:
            st.error(f"오류 발생: {e}")
            st.info("선택한 이동평균선 기간이 트레이딩뷰에서 지원되지 않을 수 있습니다. (기본 20, 50, 100, 200 추천)")
