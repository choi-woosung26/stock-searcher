import streamlit as st
from tradingview_screener import Query, col
import pandas as pd
import FinanceDataReader as fdr

# ── 설정 및 페이지 구성 ──────────────────────────────────
st.set_page_config(page_title="한국 주식 스캐너", page_icon="📈", layout="wide")

st.title("📈 한국 주식 종목 검색기")
st.markdown("이동평균선 돌파 및 52주 신고가 근처 종목을 찾습니다.")

# ── 데이터 로딩 함수 (ETF/스팩/우선주 제거 로직) ──────────
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
            
            exclude_keywords = ['스팩', 'SPAC', '리츠', 'REIT', '인프라', '환기', '수익증권', 'ETF', 'ETN', 'ELW']
            if any(kw in name.upper() for kw in exclude_keywords) or not code.endswith('0'):
                exclude_set.add(code)

        return name_map, exclude_set
    except Exception as e:
        st.error(f"종목 정보 로딩 실패: {e}")
        return {}, set()

# ── 검색 함수 ──────────────────────────────────────
def run_scanner(ma_col, min_vol, min_price, max_price):
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
        
        if data is not None and not data.empty and 'price_52_week_high' in data.columns:
            data = data[data['close'] >= data['price_52_week_high'] * 0.95]
        return data
    except Exception as e:
        st.error(f"스캔 오류: {e}")
        return pd.DataFrame()

# ── 메인 실행 로직 ──────────────────────────────────────
if st.button("🔍 종목 검색 시작", use_container_width=True):
    if min_price >= max_price:
        st.error("최소 금액이 최대 금액보다 작아야 합니다.")
    else:
        with st.spinner("📋 종목 정보 로딩 중..."):
            name_map, exclude_set = load_krx_name_map()

        with st.spinner("🔍 조건에 맞는 종목 검색 중..."):
            data = run_scanner(ma_col, min_vol, min_price, max_price)

            if data is not None and not data.empty:
                data['종목코드'] = data['name'].apply(lambda x: str(x).split(':')[-1].zfill(6))
                data = data[~data['종목코드'].isin(exclude_set)]
                data['종목명'] = data['종목코드'].map(name_map)
                data = data[data['종목명'].notna()]
                data = data[~data['종목명'].str.contains('ETF|ETN|KODEX|TIGER|RISE|ACE|SOL|KBSTAR', na=False, case=False)]

                if data.empty:
                    st.warning("⚠️ 검색된 종속이 없습니다.")
                else:
                    st.success(f"✅ {len(data)}개 종목 발견")

                    # 테이블 표시
                    display = data[['종목명', '종목코드', 'close', 'volume', 'change', ma_col, 'price_52_week_high']].copy()
                    display.columns = ['종목명', '코드', '현재가', '거래량', '등락률', f'{ma_period}일 이평', '52주 신고가']
                    st.dataframe(display.style.format({
                        '현재가': '{:,.0f}', '거래량': '{:,.0f}', '등락률': '{:+.2f}%',
                        f'{ma_period}일 이평': '{:,.0f}', '52주 신고가': '{:,.0f}'
                    }), use_container_width=True, hide_index=True)

                    # ── 차트 버튼 (이 부분이 핵심 수정 사항입니다) ──
                    st.subheader("📊 실시간 차트 바로가기")
                    cols_ui = st.columns(5)
                    for i, (_, row) in enumerate(data.iterrows()):
                        # 1. 원본 심볼(KRX:025860)을 가져옵니다.
                        full_symbol = str(row['name']) 
                        
                        # 2. URL을 수동으로 조립하지 않고 고정된 주소 뒤에 심볼만 붙입니다.
                        # 반드시 '://tradingview.com 포함되어야 합니다.
                        target_url = f"https://tradingview.com{full_symbol}"
                        
                        with cols_ui[i % 5]:
                            st.link_button(f"📈 {row['종목명']}", target_url, use_container_width=True)
            else:
                st.warning("⚠️ 결과가 없습니다.")

st.divider()
st.caption("데이터 제공: TradingView & KRX.")
