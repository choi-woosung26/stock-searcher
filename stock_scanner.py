import streamlit as st
from tradingview_screener import Query, col
import pandas as pd
import FinanceDataReader as fdr

st.set_page_config(page_title="주식 스캐너", page_icon="📈", layout="wide")

st.title("📈 한국 주식 종목 검색기")
st.markdown("이동평균선 돌파 · 52주 신고가 근처 종목을 찾습니다.")

# ── 사이드바 설정 (버튼보다 먼저 정의) ────────────────────────────
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

high_ratio = st.sidebar.slider(
    "📈 52주 신고가 대비 최소 비율 (%)",
    min_value=80, max_value=100, value=95, step=1,
    help="현재가가 52주 신고가의 몇 % 이상인 종목만 표시합니다."
)

# ── 한글 종목명 + 제외 목록 로딩 ────────────────────────────────
@st.cache_data(ttl=3600)
def load_krx_name_map():
    try:
        df = fdr.StockListing('KRX')

        # 컬럼명 자동 탐지
        code_col = next((c for c in df.columns if c in ['Code', 'Symbol', '종목코드', 'code']), None)
        name_col = next((c for c in df.columns if c in ['Name', '종목명', 'name', '이름']), None)

        if code_col is None or name_col is None:
            st.warning(f"컬럼 탐지 실패. 실제 컬럼: {list(df.columns)}")
            return {}, set()

        df[code_col] = df[code_col].astype(str).str.zfill(6)
        name_map = dict(zip(df[code_col], df[name_col]))

        exclude_set = set()
        for _, row in df.iterrows():
            code = str(row[code_col]).zfill(6)
            name = str(row[name_col])

            # ① 코드 끝자리가 '0'이 아닌 경우 제외 (우선주·파생상품 등)
            if not code.endswith('0'):
                exclude_set.add(code)
                continue

            # ② 이름 기반 키워드 제외
            exclude_keywords = [
                '스팩', 'SPAC', '리츠', 'REIT', '인프라', '환기',
                '수익증권', 'ETF', 'ETN', 'ELW'
            ]
            if any(kw in name.upper() for kw in exclude_keywords):
                exclude_set.add(code)

        return name_map, exclude_set

    except Exception as e:
        st.warning(f"종목 정보 로딩 실패: {e}")
        return {}, set()

# ── 스캐너 실행 ──────────────────────────────────────────────────
def run_scanner(ma_col, min_vol, min_price, max_price, high_ratio):
    count, data = (
        Query()
        .set_markets("korea")
        .select('name', 'close', 'volume', 'change', ma_col, 'price_52_week_high')
        .where(
            col('type') == 'stock',          # ← 파일2: stock 타입만 조회
            col('volume') > min_vol,
            col('close') > col(ma_col),
            col('close') >= min_price,
            col('close') <= max_price,
        )
        .limit(300)
        .get_scanner_data()
    )
    if data is not None and not data.empty and 'price_52_week_high' in data.columns:
        data = data[data['close'] >= data['price_52_week_high'] * (high_ratio / 100)]
    return data

# ── 트레이딩뷰 차트 URL 생성 ─────────────────────────────────────
def get_chart_url(ticker):
    # ticker 예시: 'KRX:005930'  →  올바른 URL 조립
    symbol = ticker if ":" in str(ticker) else f"KRX:{ticker}"
    return f"https://www.tradingview.com/chart/?symbol={symbol}"

# ── 검색 실행 ────────────────────────────────────────────────────
if st.button("🔍 종목 검색 시작", use_container_width=True):
    if min_price >= max_price:
        st.error("⚠️ 최소 금액이 최대 금액보다 작아야 합니다.")
    else:
        with st.spinner("📋 종목 정보 로딩 중... (최초 1회만 시간이 걸립니다)"):
            name_map, exclude_set = load_krx_name_map()

        with st.spinner("🔍 조건에 맞는 종목 검색 중..."):
            try:
                data = run_scanner(ma_col, min_vol, min_price, max_price, high_ratio)

                if data is not None and not data.empty:

                    # 종목코드 추출
                    data['종목코드'] = (
                        data['name']
                        .apply(lambda x: str(x).split(':')[-1])
                        .str.zfill(6)
                    )

                    # ── 1차 필터: 코드 기반 exclude_set ──────────────────
                    before = len(data)
                    if exclude_set:
                        data = data[~data['종목코드'].isin(exclude_set)]

                    # ── 한글 종목명 매핑 ──────────────────────────────────
                    data['종목명'] = data['종목코드'].map(name_map)

                    # 매핑 실패 시 재시도
                    def find_name(row):
                        if pd.notna(row['종목명']):
                            return row['종목명']
                        code = str(row['name']).split(':')[-1].zfill(6)
                        return name_map.get(code, str(row['name']).split(':')[-1])

                    data['종목명'] = data.apply(find_name, axis=1)

                    # ── 2차 필터: 이름 기반 ETF 재확인 ──────────────────
                    etf_pattern = r'ETF|ETN|KODEX|TIGER|RISE|ACE|KBSTAR|HANARO|ARIRANG|SOL|KOSEF'
                    data = data[data['종목명'].notna()]
                    data = data[~data['종목명'].str.contains(etf_pattern, case=False, na=False)]

                    after = len(data)

                    if data.empty:
                        st.warning("⚠️ 조건에 맞는 종목이 없습니다. 조건을 완화해 보세요.")
                    else:
                        excluded = before - after
                        msg = f"✅ {after}개 종목 발견"
                        if excluded > 0:
                            msg += f"  (ETF·스팩·우선주 등 {excluded}개 제외)"
                        st.success(msg)

                        # 표시용 컬럼 정리
                        show_cols = ['종목명', '종목코드', 'close', 'volume', 'change', ma_col, 'price_52_week_high']
                        show_cols = [c for c in show_cols if c in data.columns]
                        display = data[show_cols].copy()
                        display.rename(columns={
                            'close': '현재가(원)',
                            'volume': '거래량',
                            'change': '등락률(%)',
                            ma_col: f'{ma_period}일 이평선',
                            'price_52_week_high': '52주 신고가',
                        }, inplace=True)

                        fmt = {
                            '현재가(원)': '{:,.0f}',
                            '거래량': '{:,.0f}',
                            '등락률(%)': '{:+.2f}',
                            f'{ma_period}일 이평선': '{:,.0f}',
                            '52주 신고가': '{:,.0f}',
                        }
                        st.dataframe(
                            display.style.format(fmt),
                            use_container_width=True,
                            hide_index=True
                        )

                        # ── 차트 바로가기 버튼 ───────────────────────────
                        st.subheader("📊 트레이딩뷰 차트 바로가기")
                        cols_ui = st.columns(5)
                        for i, (_, row) in enumerate(data.iterrows()):
                            url = get_chart_url(row['name'])   # 'KRX:005930' → 올바른 URL
                            label = row['종목명']
                            with cols_ui[i % 5]:
                                st.link_button(f"📈 {label}", url, use_container_width=True)

                else:
                    st.warning("⚠️ 조건에 맞는 종목이 현재 없습니다.")

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

st.divider()
st.caption("본 프로그램은 트레이딩뷰 및 KRX 공개 데이터를 활용하며 투자 권유를 목적으로 하지 않습니다.")

