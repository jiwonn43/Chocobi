"""
= 대덕소프트웨어마이스터고등학교 D-Day 모듈 =
🍫 팀명: 초코비 / 개발자: 윤지원, 이가영
"""

import streamlit as st
from datetime import date, datetime
import requests
import urllib3

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ──────────────────────────────── API 설정 ──────────────────────────────── #
NICE_API_URL = "https://open.neis.go.kr/hub/SchoolSchedule"
ATPT_OFCDC_SC_CODE = "G10"  # 대전광역시교육청
SD_SCHUL_CODE = "7430310"    # 대덕소프트웨어마이스터고등학교
API_KEY = ""                 # 나이스 API 키 (선택)


def fetch_monthly_schedule(year: int, month: int) -> list:
    """특정 연월(YYYYMM)의 학사일정을 조회합니다."""
    ym_str = f"{year}{month:02d}"
    params = {
        "KEY": API_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": SD_SCHUL_CODE,
        "AA_YMD": ym_str
    }
    try:
        response = requests.get(NICE_API_URL, params=params, timeout=3, verify=False)
        if response.status_code == 200:
            data = response.json()
            if "SchoolSchedule" in data:
                return data["SchoolSchedule"][1]["row"]
    except Exception:
        pass
    return []


def get_all_upcoming_events(today: date) -> list:
    """
    오늘 이후 학사일정 수집
    - 연속 4일 이상 지속되는 일정(여름방학 등)은 제외
    """
    emoji_map = {
        "중간고사": "📝", "기말고사": "📝", "방학식": "🎄", "입학식": "🌸",
        "졸업식": "🎓", "발표회": "💡", "체육대회": "🏃", "축제": "🎉", "개학식": "🏫"
    }

    raw_events_by_name = {}

    # 올해 남은 달 탐색 (현재 월 ~ 12월)
    for m in range(today.month, 13):
        monthly_data = fetch_monthly_schedule(today.year, m)
        for item in monthly_data:
            event_name = item.get("EVENT_NM", "").strip()
            ymd_str = item.get("AA_YMD", "")

            # 토요휴업일/일요휴업일/빈값 제외
            if not event_name or not ymd_str or "휴업일" in event_name or "일요" in event_name:
                continue

            try:
                event_date = datetime.strptime(ymd_str, "%Y%m%d").date()
            except ValueError:
                continue

            if event_date >= today:
                if event_name not in raw_events_by_name:
                    raw_events_by_name[event_name] = []
                raw_events_by_name[event_name].append(event_date)

    filtered_events = []

    # 4일 이상 연속되는 장기 일정 제외
    for event_name, dates in raw_events_by_name.items():
        if len(dates) >= 4:
            continue

        dates.sort()
        start_date = dates[0]

        emoji = "📌"
        for k, v in emoji_map.items():
            if k in event_name:
                emoji = v
                break

        filtered_events.append({
            "id": f"{event_name}_{start_date}",
            "title": f"{emoji} {event_name}",
            "raw_title": event_name,
            "date": start_date
        })

    # API 결과 보완용 기본 예비 일정
    fallback_events = [
        {"id": "mid_2", "title": "📝 2학기 중간고사", "raw_title": "2학기 중간고사", "date": date(today.year, 10, 15)},
        {"id": "proj_1", "title": "💡 프로젝트 발표회", "raw_title": "프로젝트 발표회", "date": date(today.year, 11, 20)},
        {"id": "final_2", "title": "📝 2학기 기말고사", "raw_title": "2학기 기말고사", "date": date(today.year, 12, 14)},
        {"id": "vacation", "title": "🎄 겨울방학식", "raw_title": "겨울방학식", "date": date(today.year, 12, 24)},
        {"id": "sports", "title": "🏃 교내 체육대회", "raw_title": "체육대회", "date": date(today.year, 10, 5)},
        {"id": "festival", "title": "🎉 초코비 축제", "raw_title": "축제", "date": date(today.year, 11, 5)},
    ]

    existing_ids = {ev["id"] for ev in filtered_events}
    for fb in fallback_events:
        if fb["date"] >= today and fb["id"] not in existing_ids:
            filtered_events.append(fb)

    return filtered_events


def get_dday_list(today: date = None) -> list:
    """
    app.py에서 불러오는 메인 D-Day 추출 함수
    - 시험 D-60 이상: 제외
    - 시험 D-50 이내: 무조건 우선 포함
    - 날짜가 오늘과 가장 가까운 순서대로 4개 선정
    """
    if today is None:
        today = date.today()

    all_events = get_all_upcoming_events(today)

    priority_events = []  # 필수 포함 (D-50 이내 시험)
    regular_events = []   # 일반 후보

    for ev in all_events:
        is_exam = "중간고사" in ev["raw_title"] or "기말고사" in ev["raw_title"]
        dday = (ev["date"] - today).days

        # 1. 시험인데 D-60 이상이면 제외
        if is_exam and dday >= 60:
            continue

        # 2. 시험인데 D-50 이내면 필수 우선순위
        if is_exam and 0 <= dday <= 50:
            priority_events.append(ev)
        else:
            regular_events.append(ev)

    # 날짜 가까운 순 정렬
    priority_events.sort(key=lambda x: x["date"])
    regular_events.sort(key=lambda x: x["date"])

    # 필수 시험부터 담고 남은 자리는 가까운 일반 일정을 채움
    selected = priority_events[:4]
    needed = 4 - len(selected)
    if needed > 0:
        selected.extend(regular_events[:needed])

    # 최종 날짜순 정렬
    selected.sort(key=lambda x: x["date"])
    return selected


def render_dday_page():
    """D-Day 전용 화면 렌더링 함수"""
    st.markdown("""
        <div style="text-align: center; padding: 10px;">
            <h1 style="color: #8B4513; margin-bottom: 0px;">⏳ 최근 학사일정 D-Day</h1>
            <p style="color: #666;">오늘 날짜와 가장 가까운 학사 일정을 한눈에</p>
        </div>
        <hr>
    """, unsafe_allow_html=True)

    today = date.today()
    st.write(f"📅 **오늘 날짜:** `{today.strftime('%Y년 %m월 %d일')}`")
    st.markdown("<br>", unsafe_allow_html=True)

    st.subheader("📌 다가오는 학사일정")

    dday_events = get_dday_list(today)

    if not dday_events:
        st.info("현재 등록된 다가오는 학사일정이 없습니다.")
        return

    for event in dday_events:
        target_date = event["date"]
        diff = (target_date - today).days

        if diff > 0:
            dday_str = f"D-{diff}"
            badge_color = "#3182ce"
        elif diff == 0:
            dday_str = "D-DAY 🎉"
            badge_color = "#e53e3e"
        else:
            dday_str = f"D+{abs(diff)}"
            badge_color = "#718096"

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{event['title']}** (`{target_date.strftime('%Y-%m-%d')}`)")
        with col2:
            st.markdown(
                f"<span style='background-color:{badge_color}; color:white; padding:4px 8px; "
                f"border-radius:5px; font-weight:bold;'>{dday_str}</span>", 
                unsafe_allow_html=True
            )
        st.divider()


if __name__ == "__main__":
    st.set_page_config(page_title="🍫 초코비 - 대마고 D-Day", page_icon="⏳", layout="centered")
    render_dday_page()