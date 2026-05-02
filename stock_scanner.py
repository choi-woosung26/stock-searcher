import streamlit as st
from tradingview_screener import Query, col
import pandas as pd
import FinanceDataReader as fdr

# 1. 페이지 설정
st.set_page_config(page_title="한국 주식 스캐너", page_icon="📈", layout="wide")

st.title("📈 한국 주식 종목 검색기")
st.markdown("이동평균선 돌파 및 52주 신고가 근처 종목을 찾습니다.")

# 2. 사이드바 설정 (변수 정의를 먼저 수행)
st.sidebar.header("🔍 검색 설정")

ma_period = st.sidebar.number_input("📊 이동평균선 (일)", 1, 500, 200)
ma_col = f"SMA{ma_period}"

min_vol = st.sidebar.number_input("📦 최소 거래량", value=100000)

st.sidebar.markdown("💰 **주가 범위 (원)**")
min_price = st.sidebar.number_input("최소 금액", value=2000)
max_price = st.sidebar.number_input("최대 금액", value=30000)

# 3. 종목 정보 로딩 함수
@st.cache_data(ttl=3600)
def load_krx_name_map():
    try:
        df = fdr.StockListing('KRX')
        code_col = next((c for c in df.columns if c in ['Code', 'Symbol', '종목코드']), 'Code')
        name_col = next((c for c in df.columns if c in ['Name', '종목명', 'name']), 'Name')

        df[code_col] = df[code_col].astype(str).str.zfill(6)
        name_map = dict(zip(df[code_col], df[name_col]))

        exclude_set = set()
        for _, row in df.iterrows():
            code = str(row[code_col]).zfill(6)
            name = str(row[name_col])
            
            # 필터링 (ETF, 스팩, 우선주 등)
            exclude_keywords = ['스팩', 'SPAC', '리츠', 'REIT', '인프라', '환기', '수익증권', 'ETF', 'ETN', 'ELW']
            if any(kw in name.upper() for kw in exclude_keywords) or not code.endswith('0'):
                exclude_set.add(code)
        return name_map, exclude_set
    except:
        return {}, set()

# 4. 스캐너 실행 함수
def run_scanner():
    try:
        q = Query().set_markets("korea")
        q.where(col('type') == 'stock') 
        q.select('name', 'close', 'volume', 'change', ma_col, 'price_52_week_high')
        q.where(
            col('volume') > min_vol,
            col('close') > col(ma_col),
            col('close') >= min_price,
            col('close') <= max_price,
        )
        q.limit(300)
        count, data = q.get_scanner_data()
        
        if data is not None and not data.empty:
            # 52주 신고가 90% 이상 필터링
            data = data[data['close'] >= data['price_52_week_high'] * 0.90]
        return data
    except:
        return pd.DataFrame()

# 5. 검색 실행 메인 로직 (변수 정의 이후에 배치)
if st.button("🔍 종목 검색 시작", use_container_width=True):
    # 이제 min_price와 max_price가 정의되어 있어 에러가 나지 않습니다.
    if min_price >= max_price:
        st.error("⚠️ 최소 금액이 최대 금액보다 작아야 합니다.")
    else:
        with st.spinner("📋 종목 정보 및 조건 검색 중..."):
            name_map, exclude_set = load_krx_name_map()
            data = run_scanner()

            if data is not None and not data.empty:
                # 데이터 가공
                data['종목코드'] = data['name'].apply(lambda x: str(x).split(':')[-1].zfill(6))
                data = data[~data['종목코드'].isin(exclude_set)]
                data['종목명'] = data['종목코드'].map(name_map)
                
                # 이름 기반 ETF 2차 필터
                data = data[data['종목명'].notna()]
                data = data[~data['종목명'].str.contains('ETF|ETN|KODEX|TIGER|RISE|ACE', na=False, case=False)]

                if data.empty:
                    st.warning("⚠️ 검색된 종목이 없습니다.")
                else:
                    st.success(f"✅ {len(data)}개 종목 발견")

                    # 테이블 표시
                    display = data[['종목명', '종목코드', 'close', 'volume', 'change', ma_col]].copy()
                    display.columns = ['종목명', '코드', '현재가', '거래량', '등락률', f'{ma_period}일 이평']
                    st.dataframe(display.style.format({
                        '현재가': '{:,.0f}', '거래량': '{:,.0f}', '등락률': '{:+.2f}%', f'{ma_period}일 이평': '{:,.0f}'
                    }), use_container_width=True, hide_index=True)

                    # 차트 버튼 (URL 구조 고정)
                    st.subheader("📊 실시간 차트 바로가기")
                    cols = st.columns(5)
                    for i, (_, row) in enumerate(data.iterrows()):
                        symbol = row['name'] # 'KRX:005930'
                        # URL 사이에 반드시 슬래시(/)와 파라미터를 정확히 조립
                        target_url = f"https://tradingview.com{symbol}"
                        with cols[i % 5]:
                            st.link_button(f"📈 {row['종목명']}", target_url, use_container_width=True)
            else:
                st.warning("⚠️ 검색 결과가 없습니다.")

st.divider()
st.caption("TradingView 및 KRX 데이터를 사용합니다. 투자 책임은 본인에게 있습니다.")
