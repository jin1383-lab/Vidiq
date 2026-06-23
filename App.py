import streamlit as st
import pandas as pd
import requests
import isodate
from datetime import datetime, timezone

st.set_page_config(page_title="Pixeling Analytics Pro", page_icon="🌙", layout="wide")

st.markdown("""<style>
    .stApp { background-color: #0B0F19 !important; color: #E5E7EB; }
    .brand-title { font-size: 24pt; font-weight: 800; background: linear-gradient(135deg, #FF0055, #4FACFE); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .url-wrapper { background: #161D30; border-radius: 8px; padding: 10px; border: 1px solid #24314D; color: #34D399; font-family: monospace; font-size: 9pt; margin-bottom: 15px; }
    .mvp-hero-card { background: linear-gradient(135deg, #1A1225, #131B2E); border-radius: 12px; padding: 20px; margin-bottom: 20px; border: 1px solid #FF3366; }
    .grid-card { background: #131B2E; border-radius: 10px; border: 1px solid #212B41; padding: 15px; margin-bottom: 20px; height: auto; }
    .metric-box { background: #1A2338; border-radius: 6px; padding: 8px; margin-top: 5px; border: 1px solid #24314D; font-size: 9pt; }
    .thumb-link img { transition: transform 0.2s ease, opacity 0.2s ease; }
    .thumb-link img:hover { transform: scale(1.02); opacity: 0.85; cursor: pointer; }
</style>""", unsafe_allow_html=True)

st.markdown('<div class="brand-title">Pixeling VidIQ Matrix 📊</div><div style="color:#9CA3AF;font-size:9pt;">YouTube Realtime Engagement & Trend Chart Engine</div><br>', unsafe_allow_html=True)

try: API_KEY = st.secrets["YOUTUBE_API_KEY"]
except: API_KEY = st.sidebar.text_input("API KEY", type="password")

CATEGORY_MAP = {
    "전체 (All)": None, "영화 & 애니메이션": "1", "자동차 & 탈것": "2", "음악": "10", 
    "반려동물 & 동물": "15", "스포츠": "17", "여행 & 이벤트": "19", "게임": "20", 
    "인물 & 블로그": "22", "코미디": "23", "엔터테인먼트": "24", "뉴스 & 정치": "25", 
    "노하우 & 스타일": "26", "교육": "27", "과학 & 기술": "28"
}

@st.cache_data(ttl=600)
def fetch_vidiq_trending_data(days, cc, fmt, cat_id):
    if not API_KEY: return pd.DataFrame()
    url = "https://www.googleapis.com/youtube/v3/videos"
    data = []
    next_page_token = None
    max_loops = 4 if fmt == "숏폼 전용" else 2
    
    now = datetime.now(timezone.utc)
    
    for _ in range(max_loops):
        p = {"part": "id,snippet,contentDetails,statistics", "chart": "mostPopular", "regionCode": cc, "maxResults": 50, "key": API_KEY}
        if cat_id: p["videoCategoryId"] = cat_id
        if next_page_token: p["pageToken"] = next_page_token
            
        try: res = requests.get(url, params=p).json()
        except: break
        if "error" in res or "items" not in res: break

        for item in res["items"]:
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            v_id = item.get("id")
            
            try: secs = isodate.parse_duration(item["contentDetails"].get("duration", "PT0S")).total_seconds()
            except: secs = 0
            m_type = "Shorts" if secs <= 60 else "Long-form"
            if (fmt == "롱폼 전용" and m_type != "Long-form") or (fmt == "숏폼 전용" and m_type != "Shorts"): continue
            
            published_at_str = snippet.get("publishedAt")
            try:
                published_at = datetime.strptime(published_at_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                elapsed_days = (now - published_at).days + (now - published_at).seconds / 86400.0
                if elapsed_days < 0.1: elapsed_days = 0.1
            except:
                elapsed_days = 1.0
            
            raw_likes = int(stats.get("likeCount", 0))
            raw_comments = int(stats.get("commentCount", 0))
            raw_views = int(stats.get("viewCount", 0))
            
            calc_likes = int((raw_likes / elapsed_days) * days)
            calc_comments = int((raw_comments / elapsed_days) * days)
            calc_views = int((raw_views / elapsed_days) * days)
            
            engagement_score = calc_likes + (calc_comments * 2) 
            
            if m_type == "Shorts":
                rpm = 110 if cc == "KR" else 150 if cc == "US" else 120
            else:
                rpm = 4500 if cc == "KR" else 9000 if cc == "US" else 5500
                
            estimated_revenue = int((calc_views / 1000) * rpm)
            currency_symbol = "₩" if cc == "KR" else "$" if cc == "US" else "¥"
            
            # 그래프 레이블 가독성을 위한 채널 타이틀 축소 처리
            short_name = snippet.get("channelTitle", "익명")
            if len(short_name) > 8: short_name = short_name[:7] + ".."

            data.append({
                "video_url": f"https://youtu.be/{v_id}",
                "name": snippet.get("channelTitle", "익명"),
                "short_name": short_name,
                "handle": f"@{snippet.get('channelId')[:12]}",
                "type": m_type, 
                "views": calc_views,
                "likes": calc_likes,
                "comments": calc_comments,
                "score": engagement_score,
                "rev": estimated_revenue,
                "symbol": currency_symbol,
                "img": snippet.get("thumbnails", {}).get("high", {}).get("url", "")
            })
            
        next_page_token = res.get("nextPageToken")
        if not next_page_token: break

    df = pd.DataFrame(data)
    if df.empty: return df
    
    # 참여도 기준 상위 정렬
    df = df.drop_duplicates(subset=["handle"]).sort_values(by="score", ascending=False).reset_index(drop=True)
    return df.head(20)

st.sidebar.markdown("### ⚡ VIDIQ ANALYTICS CONTROL")
selected_cat_label = st.sidebar.selectbox("CATEGORY", list(CATEGORY_MAP.keys()))
target_cat_id = CATEGORY_MAP[selected_cat_label]

media_filter = st.sidebar.selectbox("FORMAT", ["전체 통합", "롱폼 전용", "숏폼 전용"])
period_label = st.sidebar.select_slider("PERIOD", options=["1D", "7D", "30D"])
days_param = 7 if period_label == "7D" else (30 if period_label == "30D" else 1)

nations = ["South Korea (KR)", "United States (US)", "Japan (JP)"]
selected_nation = st.sidebar.selectbox("NATION", nations)
country_code = "US" if "US" in selected_nation else "JP" if "JP" in selected_nation else "KR"
run_engine = st.sidebar.button("RUN ENGINE & GENERATE VISUALS", type="primary", use_container_width=True)

if run_engine and API_KEY:
    with st.spinner(f"⚡ 실시간 메트릭 스캔 및 VidIQ 그래프 렌더링 중..."): 
        df = fetch_vidiq_trending_data(days_param, country_code, media_filter, target_cat_id)
        
    if not df.empty:
        st.markdown(f'<div class="url-wrapper">🔗 VIDIQ VISUALIZATION ENGINE ACTIVE | 인터랙티브 트렌드 스케일러 분석 완료</div>', unsafe_allow_html=True)
        
        # 👑 1위 MVP 대형 단독 레이아웃
        m = df.iloc[0]
        c = "color:#F87171;" if m['type'] == "Shorts" else "color:#60A5FA;"
        st.markdown(f"""<div class="mvp-hero-card"><div style="display:flex;justify-content:space-between;font-size:9pt;font-weight:600;"><span style="color:#00F2FE;">📊 REALTIME ANALYSIS MVP</span><span style="{c}">{m['type']}</span></div><div style="display:flex;align-items:center;gap:15px;margin-top:10px;"><a href="{m['video_url']}" target="_blank" class="thumb-link"><img src="{m['img']}" style="width:100px;height:70px;border-radius:6px;object-fit:cover;"></a><div style="flex-grow:1;"><div style="font-size:14pt;font-weight:800;color:#FFF;">{m['name']}</div><div style="color:#9CA3AF;font-size:9pt;">{m['handle']}</div></div><div><div class="metric-box"><span style="color:#A78BFA;">📈 {period_label} 환산뷰:</span> <b>{m['views']:,}회</b></div><div class="metric-box"><span style="color:#F87171;">❤️ {period_label} 좋아요:</span> <b>{m['likes']:,}개</b></div><div class="metric-box"><span style="color:#38BDF8;">💬 {period_label} 댓글수:</span> <b>{m['comments']:,}개</b></div></div></div></div>""", unsafe_allow_html=True)
        
        # 📊 ----------------- VidIQ 인터랙티브 차트 매립 구역 -----------------
        st.markdown("<h4 style='font-weight:700;color:#FFF;margin-bottom:5px;'>📈 VidIQ Engagement Analytics Trend</h4>", unsafe_allow_html=True)
        
        # 데이터프레임 인덱스 가공
        chart_df = df.copy()
        chart_df = chart_df.set_index("short_name")
        
        # 차트 분할 배치 (2컬럼)
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.markdown("<div style='font-size:10pt;color:#9CA3AF;margin-bottom:8px;'>채널별 환산 조회수 추이 (수평 비교용)</div>", unsafe_allow_html=True)
            # 1. 20개 채널 조회수 선형 차트 렌더링
            st.line_chart(chart_df["views"], height=260, color="#4FACFE")
            
        with chart_col2:
            st.markdown("<div style='font-size:10pt;color:#9CA3AF;margin-bottom:8px;'>채널별 참여 지표 (좋아요 및 댓글 볼륨 바)</div>", unsafe_allow_html=True)
            # 2. 좋아요 및 댓글 복합 누적 막대 그래프 렌더링
            st.bar_chart(chart_df[["likes", "comments"]], height=260, color=["#FF0055", "#38BDF8"])
            
        st.markdown("<hr style='border:0.5px solid #212B41;margin:30px 0;'>", unsafe_allow_html=True)
        # -------------------------------------------------------------------

        st.markdown(f"<h5 style='font-weight:700;color:#E5E7EB;margin-bottom:15px;'>👥 TOP 2 - {len(df)} DETAILED TREND METRIC</h5>", unsafe_allow_html=True)
        g_data = df.iloc[1:].reset_index(drop=True)
        
        total_rows = (len(g_data) + 2) // 3
        grid_rows = [st.columns(3) for _ in range(total_rows)]
        
        for idx in range(len(g_data)):
            row_pos = idx // 3
            col_pos = idx % 3
            item = g_data.iloc[idx]
            tc = "color:#F87171;" if item['type'] == "Shorts" else "color:#60A5FA;"
            
            with grid_rows[row_pos][col_pos]:
                st.markdown(f"""<div class="grid-card">
                    <div>
                        <div style="display:flex;justify-content:space-between;font-size:8pt;"><b>TOP {idx+2}</b><span style="{tc}">{item['type']}</span></div>
                        <a href="{item['video_url']}" target="_blank" class="thumb-link">
                            <img src="{item['img']}" style="width:100%;height:120px;border-radius:6px;object-fit:cover;margin:8px 0;border:1px solid #24314D;">
                        </a>
                        <div style="font-size:10.5pt;font-weight:700;color:#FFF;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{item['name']}</div>
                        <div style="color:#9CA3AF;font-size:8.5pt;margin-bottom:8px;">{item['handle']}</div>
                    </div>
                    <div>
                        <div class="metric-box"><span style="color:#A78BFA;">📈 조회수:</span> <b>{item['views']:,}</b></div>
                        <div class="metric-box"><span style="color:#F87171;">❤️ 좋아요:</span> <b>{item['likes']:,}</b></div>
                        <div class="metric-box"><span style="color:#38BDF8;">💬 댓글수:</span> <b>{item['comments']:,}</b></div>
                    </div>
                </div>""", unsafe_allow_html=True)
    else: 
        st.warning(f"⚠️ {selected_nation} 트렌딩 피드에서 조건에 맞는 데이터를 확보하지 못했습니다.")
else: 
    st.info("💡 사이드바 설정을 세팅하고 [RUN ENGINE & GENERATE VISUALS]를 돌려 그래프 대시보드를 생성하세요.")
