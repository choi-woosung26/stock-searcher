import streamlit as st
from tradingview_screener import Query, col
import pandas as pd
import FinanceDataReader as fdr

# ── 설정 및 페이지 구성 ──────────────────────────────────
st.set_page_config(page_title="한국 주식 스캐너", page_icon="📈", layout="wide")

st.title("📈 한국 주식 종목 검색기")
st.markdown("이동평균선 돌파 및 52주 신고가 근처의 **순수 주식 종목**을 찾습니다.")

# ── 데이터 로딩 함수 (ETF/스팩/우선주 제거 로직 강화) ────────────────
@st.cache_data(ttl=3600)
def load_krx_name_map():
    try:
        df = fdr.StockListing('KRX')
        code_col = next((c for c in df.columns if c in ['Code', 'Symbol', '종목코드', 'code']), None)
        name_col = next((c for c in df.columns if c in ['Name', '종목명', 'name', '이름']), None)

        if code_col is None or name_col is None:
            return {}, set()

        df[code_col] = df[code_col].astype(str).str.zfill(6)
        name_map = dict(zip(df[code_col], df[name_col]))

        exclude_set = set()
        for _, row in df.iterrows():
            code = str(row[code_col]).zfill(6)
            name = str(row[name_col])

            # 제외 키워드 강화 (ETF, ETN, 스팩, 리츠 등)
            exclude_keywords = [
                '스팩', 'SPAC', '리츠', 'REIT', '인프라', '환기', '수익증권', 
                'ETF', 'ETN', 'ELW', '선물', '고배당', '코스피 200', '코스닥 150'
            ]
            if any(kw in name.upper() for kw in exclude_keywords):
                exclude_set.add(code)
                continue
            
            # 우선주 제외 (코드 끝이 0이 아닌 경우 대다수 우선주)
            if not code.endswith('0'):
                exclude_set.add(code)

        return name_map, exclude_set
    except Exception as e:
        st.error(f"종목 정보 로딩 실패: {e}")
        return {}, set()

# ── 검색 함수 (타입 필터 추가) ──────────────────────────────────────
def run_scanner(ma_col, min_vol, min_price, max_price):
    # Query() 단계에서 type='stock'으로 ETF 1차 차단
    count, data = (
        Query()
        .set_markets("korea")
        .where(col('type').equals('stock')) 
        .select('name', 'close', 'volume', 'change', ma_col, 'price_52_week_high')
        .where(
            col('volume') > min_vol,
            col('close') > col(ma_col),
            col('close') >= min_price,
            col('close') <= max_price,
        )
        .limit(300)
        .get_scanner_data()
    )
    # 52주 신고가 대비 95% 이상 지점 필터링
    if data is not None and not data.empty and 'price_52_week_high' in data.columns:
        data = data[data['close'] >= data['price_52_week_high'] * 0.95]
    return data

def get_chart_url(ticker):
    symbol = ticker if ":" in str(ticker) else f"KRX:{ticker}"
    return f"https://tradingview.com{symbol}"

# ── 사이드바 설정 ──────────────────────────────────
st.sidebar.header("🔍 검색 설정")

ma_period = st.sidebar.number_input(
    "📊 이동평균선 (일)",
    min_value=1, max_value=500, value=200, step=1,
    help="종가가 이 이평선보다 높은 종목을 검색합니다."
)
ma_col = f"SMA{ma_period}"

min_vol = st.sidebar.number_input("📦 최소 거래량", value=100000, step=10000)

st.sidebar.markdown("💰 **주가 범위 (원)**")
min_price = st.sidebar.number_input("최소 금액", value=2000, step=500, min_value=0)
max_price = st.sidebar.number_input("최대 금액", value=30000, step=1000, min_value=0)

# ── 메인 실행 로직 ──────────────────────────────────────
if st.button("🔍 종목 검색 시작", use_container_width=True):
    if min_price >= max_price:
        st.error("최소 금액이 최대 금액보다 작아야 합니다.")
    else:
        with st.spinner("📋 종목 정보 및 필터 로딩 중..."):
            name_map, exclude_set = load_krx_name_map()

        with st.spinner("🔍 조건에 맞는 종목 검색 중..."):
            try:
                data = run_scanner(ma_col, min_vol, min_price, max_price)

                if data is not None and not data.empty:
                    # 종목코드 추출 및 정규화
                    data['종목코드'] = data['name'].apply(lambda x: str(x).split(':')[-1].zfill(6))

                    # 1. exclude_set 기반 필터링 (ETF, 스팩, 우선주 등)
                    before = len(data)
                    data = data[~data['종목코드'].isin(exclude_set)]
                    
                    # 2. 한글명 매핑 및 이름 기반 2차 필터링
                    data['종목명'] = data['종목코드'].map(name_map)
                    data = data[data['종목명'].notna()] # 이름 매핑 안되는 유령종목 제외
                    
                    # 최종 이름 기반 필터링 (한 번 더 확실하게)
                    data = data[~data['종목명'].str.contains('ETF|ETN|스팩|SPAC|리츠|REIT|물산|홀딩스', na=False, case=False)]
                    
                    after = len(data)

                    if data.empty:
                        st.warning("⚠️ 모든 필터링 결과 조건에 맞는 '순수 주식'이 없습니다.")
                    else:
                        st.success(f"✅ {after}개 종목 발견 (지수물 및 잡주 {before - after}개 제외)")

                        # 결과 테이블 구성
                        display = data[['종목명', '종목코드', 'close', 'volume', 'change', ma_col, 'price_52_week_high']].copy()
                        display.columns = ['종목명', '코드', '현재가(원)', '거래량', '등락률(%)', f'{ma_period}일 이평', '52주 신고가']
                        
                        fmt = {
                            '현재가(원)': '{:,.0f}', '거래량': '{:,.0f}', '등락률(%)': '{:+.2f}%',
                            f'{ma_period}일 이평': '{:,.0f}', '52주 신고가': '{:,.0f}'
                        }
                        
                        st.dataframe(display.style.format(fmt), use_container_width=True, hide_index=True)

                        # 차트 바로가기 버튼
                        st.subheader("📊 실시간 차트 보기")
                        cols_ui = st.columns(5)
                        for i, (_, row) in enumerate(data.iterrows()):
                            url = get_chart_url(row['name'])
                            with cols_ui[i % 5]:
                                st.link_button(f"📈 {row['종목명']}", url, use_container_width=True)
                else:
                    st.warning("⚠️ 검색 결과가 없습니다. 조건을 조절해 보세요.")
            except Exception as e:
                st.error(f"실행 중 오류 발생: {e}")

st.divider()
st.caption("본 프로그램은 TradingView Screener API 및 KRX 데이터를 활용합니다. 모든 투자의 책임은 본인에게 있습니다.")
