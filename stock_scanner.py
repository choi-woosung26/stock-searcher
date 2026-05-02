import streamlit as st
from tradingview_screener import Query, col
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="주식 스캐너", page_icon="📈", layout="wide")

st.title("📈 한국 주식 종목 검색기")
st.markdown("이동평균선 돌파 · 신고가 근처 종목을 찾습니다.")

# ── KRX에서 한글 종목명 직접 가져오기 ─────────────────────
@st.cache_data(ttl=3600)
def load_krx_name_map():
    try:
        from io import BytesIO

        # 네이버 금융 전종목 리스트 (KOSPI + KOSDAQ)
        dfs = []
        for market in ['stockMkt', 'kosdaqMkt']:
            url = f'https://finance.naver.com/siseinfo/excel/downSise.nhn?&market={market}'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://finance.naver.com'
            }
            r = requests.get(url, headers=headers)
            df = pd.read_html(BytesIO(r.content), encoding='euc-kr')[0]
            dfs.append(df)

        df = pd.concat(dfs, ignore_index=True)

        # 컬럼 확인 후 코드/이름 추출
        # 네이버 컬럼: '종목코드', '종목명' 또는 유사한 이름
        code_col = [c for c in df.columns if '코드' in str(c)][0]
        name_col = [c for c in df.columns if '종목명' in str(c) or '이름' in str(c)][0]

        df[code_col] = df[code_col].astype(str).str.zfill(6)

        name_map = dict(zip(df[code_col], df[name_col]))

        # 제외 종목
        exclude_set = set()
        for _, row in df.iterrows():
            code = str(row[code_col]).zfill(6)
            name = str(row[name_col])

            if '스팩' in name or 'SPAC' in name.upper():
                exclude_set.add(code)
                continue
            if code.endswith('5'):
                exclude_set.add(code)
                continue
            for kw in ['리츠', '인프라', '환기', '수익증권', 'ETF', 'ETN', 'ELW']:
                if kw in name:
                    exclude_set.add(code)
                    break

        return name_map, exclude_set

    except Exception as e:
        st.warning(f"종목 정보 로딩 실패: {e}")
        return {}, set()

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

# ── 검색 함수 ──────────────────────────────────────
def run_scanner(ma_col, min_vol, min_price, max_price):
    count, data = (
        Query()
        .set_markets("korea")
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
    if data is not None and not data.empty and 'price_52_week_high' in data.columns:
        data = data[data['close'] >= data['price_52_week_high'] * 0.95]
    return data

def get_chart_url(ticker):
    symbol = ticker if ":" in str(ticker) else f"KRX:{ticker}"
    return f"https://www.tradingview.com/chart/?symbol={symbol}"

# ── 검색 실행 ──────────────────────────────────────
if st.button("🔍 종목 검색 시작", use_container_width=True):
    if min_price >= max_price:
        st.error("최소 금액이 최대 금액보다 작아야 합니다.")
    else:
        with st.spinner("종목 정보 로딩 중..."):
            name_map, exclude_set = load_krx_name_map()

        with st.spinner("조건에 맞는 종목 검색 중..."):
            try:
                data = run_scanner(ma_col, min_vol, min_price, max_price)

                if data is not None and not data.empty:

                    # 종목코드 추출
                    def extract_code(val):
                        return str(val).split(':')[-1] if ':' in str(val) else str(val)

                    data['종목코드'] = data['name'].apply(extract_code)

                    # ETF·스팩·우선주 등 제외
                    before = len(data)
                    if exclude_set:
                        data = data[~data['종목코드'].isin(exclude_set)]
                    after = len(data)

                    # 한글 종목명 매핑
                    data['종목명'] = data['종목코드'].map(name_map)
                    # 한글명 못 가져온 경우 영문코드로 표시
                    data['종목명'] = data['종목명'].fillna(data['name'])

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
                            '등락률(%)': '{:.2f}',
                            f'{ma_period}일 이평선': '{:,.0f}',
                            '52주 신고가': '{:,.0f}',
                        }
                        st.dataframe(
                            display.style.format(fmt),
                            use_container_width=True,
                            hide_index=True
                        )

                        # 차트 바로가기 버튼
                        st.subheader("📊 차트 바로가기")
                        cols_ui = st.columns(5)
                        for i, (_, row) in enumerate(data.iterrows()):
                            url = get_chart_url(row['name'])
                            label = row['종목명']
                            with cols_ui[i % 5]:
                                st.link_button(f"📈 {label}", url, use_container_width=True)

                else:
                    st.warning("⚠️ 조건에 맞는 종목이 현재 없습니다.")

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

st.divider()
st.caption("본 프로그램은 트레이딩뷰 및 KRX 공개 데이터를 활용하며 투자 권유를 목적으로 하지 않습니다.")
