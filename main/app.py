"""
= 대덕소프트웨어마이스터고등학교 학사일정 AI 챗봇 =
🍫 팀명: 초코비 / 개발자: 윤지원, 이가영
"""
from dday import get_dday_list
import streamlit as st
from datetime import date, timedelta
import requests
import urllib3
import time
import re
import os
from dotenv import load_dotenv

load_dotenv()

# 학교 보안망 SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ──────────────────────────────── API 및 기본 설정 ──────────────────────────────── #
NICE_API_URL = "https://open.neis.go.kr/hub/SchoolSchedule"

ATPT_OFCDC_SC_CODE = "G10"  # 대전광역시교육청
SD_SCHUL_CODE = "7430310"    # 대덕소프트웨어마이스터고등학교

# 🔑 API 키를 정확하게 넣어서 사용해 주세요!
API_KEY = os.getenv("NICE_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


# ──────────────────────────────── 1. 비상용 대마고 학사일정 백업 데이터 ──────────────────────────────── #
FALLBACK_SCHEDULE_DATA = [
    "- 2026-03-02: 1학기 개학식 및 입학식",
    "- 2026-03-16: 학부모 총회 및 학교설명회",
    "- 2026-04-15: 1학기 1차 지필평가(중간고사) 1일차",
    "- 2026-04-16: 1학기 1차 지필평가(중간고사) 2일차",
    "- 2026-04-17: 1학기 1차 지필평가(중간고사) 3일차",
    "- 2026-05-01: 재량휴업일(근로자의 날)",
    "- 2026-05-05: 어린이날 (공휴일)",
    "- 2026-05-15: 스승의 날 기념행사 및 체육대회",
    "- 2026-06-05: 개교기념일",
    "- 2026-06-29: 1학기 2차 지필평가(기말고사) 1일차",
    "- 2026-06-30: 1학기 2차 지필평가(기말고사) 2일차",
    "- 2026-07-01: 1학기 2차 지필평가(기말고사) 3일차",
    "- 2026-07-02: 1학기 2차 지필평가(기말고사) 4일차",
    "- 2026-07-17: 제헌절 / 1학기 방학식",
    "- 2026-08-17: 2학기 개학식",
    "- 2026-09-14: 추석 연휴",
    "- 2026-10-03: 개천절",
    "- 2026-10-09: 한글날",
    "- 2026-10-14: 2학기 1차 지필평가(중간고사) 1일차",
    "- 2026-10-15: 2학기 1차 지필평가(중간고사) 2일차",
    "- 2026-10-16: 2학기 1차 지필평가(중간고사) 3일차",
    "- 2026-11-05: 소마제(동아리 발표회 및 학교 축제)",
    "- 2026-12-14: 2학기 2차 지필평가(기말고사) 1일차",
    "- 2026-12-15: 2학기 2차 지필평가(기말고사) 2일차",
    "- 2026-12-16: 2학기 2차 지필평가(기말고사) 3일차",
    "- 2026-12-30: 2학기 종업식 및 방학식",
    "- 2027-01-08: 제8회 졸업식"
]


# ──────────────────────────────── 2. 날짜 범위 분석 ──────────────────────────────── #
def parse_user_intent_python(user_question: str) -> tuple[str, str]:
    today = date.today()
    current_year = today.year
    text = user_question.strip().lower()

    if "오늘" in text:
        return today.strftime("%Y%m%d"), today.strftime("%Y%m%d")
    if "내일" in text:
        dt = today + timedelta(days=1)
        return dt.strftime("%Y%m%d"), dt.strftime("%Y%m%d")
    if "어제" in text:
        dt = today - timedelta(days=1)
        return dt.strftime("%Y%m%d"), dt.strftime("%Y%m%d")
    if "모레" in text:
        dt = today + timedelta(days=2)
        return dt.strftime("%Y%m%d"), dt.strftime("%Y%m%d")

    if "이번주" in text or "이번 주" in text:
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")
    if "다음주" in text or "다음 주" in text:
        start = today - timedelta(days=today.weekday()) + timedelta(weeks=1)
        end = start + timedelta(days=6)
        return start.strftime("%Y%m%d"), end.strftime("%Y%m%d")

    if "1학기" in text:
        return f"{current_year}0301", f"{current_year}0731"
    if "2학기" in text:
        return f"{current_year}0801", f"{current_year+1}0228"

    month_match = re.search(r'(\d{1,2})\s*월', text)
    if month_match:
        m = int(month_match.group(1))
        if 1 <= m <= 12:
            import calendar
            _, last_day = calendar.monthrange(current_year, m)
            return f"{current_year}{m:02d}01", f"{current_year}{m:02d}{last_day:02d}"

    return f"{current_year}0101", f"{current_year+1}0228"


# ──────────────────────────────── 3. 나이스 API 수집 ──────────────────────────────── #
@st.cache_data(ttl=600)
def fetch_raw_schedule_cached(from_ymd: str, to_ymd: str) -> list:
    params = {
        "KEY": API_KEY.strip(),
        "Type": "json",
        "pIndex": 1,
        "pSize": 1000,
        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": SD_SCHUL_CODE,
        "AA_FROM_YMD": from_ymd,
        "AA_TO_YMD": to_ymd
    }

    records = []
    try:
        response = requests.get(NICE_API_URL, params=params, timeout=5, verify=False)
        if response.status_code == 200:
            data = response.json()
            if "SchoolSchedule" in data:
                for item in data["SchoolSchedule"]:
                    if "row" in item:
                        for row in item["row"]:
                            event_date = row.get("AA_YMD", "")
                            event_nm = row.get("EVENT_NM", "")
                            if event_date and event_nm:
                                formatted_date = f"{event_date[:4]}-{event_date[4:6]}-{event_date[6:]}"
                                records.append(f"- {formatted_date}: {event_nm}")
    except Exception:
        pass

    if not records:
        records = FALLBACK_SCHEDULE_DATA

    return records


# ──────────────────────────────── 4. Groq AI 호출 메인 ──────────────────────────────── #
def ask_groq_ai_once(user_question: str) -> str:
    from_ymd, to_ymd = parse_user_intent_python(user_question)
    raw_events = fetch_raw_schedule_cached(from_ymd, to_ymd)
    schedule_data = "\n".join(raw_events)

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
        "Content-Type": "application/json"
    }

    system_prompt = """
너는 대덕소프트웨어마이스터고등학교(대마고) 학생들을 도와주는 AI 챗봇 '초코비'이다.

[필수 작성 규칙]
1. 반드시 제공된 [학교 학사일정 목록]을 근거로 답변한다. 목록에 데이터가 풍부하게 있으므로 "등록된 일정이 없습니다"라는 답변을 최대한 피하고, 질문과 가장 유사하거나 해당 월/학기에 있는 일정들을 적극적으로 찾아 안내한다.
2. 학생이 '중간고사'를 물어보면 '1차 지필평가'를 찾고, '기말고사'를 물어보면 '2차 지필평가'를 찾아 일정을 알려준다.
3. 학생이 '방학식', '개학식', '동아리', '축제(소마제)', '10월 일정' 등을 물어보면 목록에서 정확한 날짜를 찾아 친절하게 설명한다.
4. 단순 날짜 나열에 그치지 않고, 센스 있고 친근한 고등학교 선배 느낌의 따뜻한 팁이나 응원의 한마디를 덧붙인다.
"""

    user_prompt = f"""
[학교 정보]: 대덕소프트웨어마이스터고등학교
[오늘 날짜]: {date.today().strftime('%Y-%m-%d')}
[학교 학사일정 목록]:
{schedule_data}

[학생 질문]: "{user_question}"
"""

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2
    }

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=10, verify=False)
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        else:
            return f"❌ Groq API 오류 (코드: {response.status_code})"
    except Exception as e:
        return f"❌ 통신 오류가 발생했습니다: {e}"


# ──────────────────────────────── 페이지 기본 설정 ──────────────────────────────── #
st.set_page_config(
    page_title="🍫 초코비 - 대마고 학사일정 서비스",
    page_icon="🍫",
    layout="centered"
)


# ──────────────────────────────── 화면 1: AI 챗봇 ──────────────────────────────── #
def render_chatbot_page():
    st.markdown("""
        <div style="text-align: center; padding: 10px;">
            <h1 style="color: #8B4513; margin-bottom: 0px;">🍫 초코비</h1>
            <p style="color: #666; font-size: 16px;"><b>대덕소프트웨어마이스터고등학교 학사일정 AI 챗봇</b></p>
            <p style="color: #aaa; font-size: 13px;">개발: 윤지원, 이가영</p>
        </div>
        <hr>
    """, unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "🍫 **안녕하세요! 대마고 학사일정 AI 도우미 초코비입니다.**\n궁금한 학사일정(중간고사, 기말고사, 방학, 축제 등)을 편하게 물어보세요!"}
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("질문을 입력하세요..."):
        print("")
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🍫 초코비가 학사일정을 확인 중입니다..."):
                response = ask_groq_ai_once(prompt)

            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})


# ──────────────────────────────── 화면 2: D-Day 페이지 ──────────────────────────────── #
def render_dday_page():
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

    st.subheader("📌 다가오는 주요 학사일정")

    try:
        dday_events = get_dday_list(today)
    except Exception:
        dday_events = [
            {"title": "1학기 1차 지필평가(중간고사)", "date": date(2026, 4, 15)},
            {"title": "1학기 2차 지필평가(기말고사)", "date": date(2026, 6, 29)},
            {"title": "여름방학식", "date": date(2026, 7, 17)},
            {"title": "2학기 1차 지필평가(중간고사)", "date": date(2026, 10, 14)},
            {"title": "소마제 (학교 축제)", "date": date(2026, 11, 5)},
            {"title": "2학기 2차 지필평가(기말고사)", "date": date(2026, 12, 14)}
        ]

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


# ──────────────────────────────── 메인 제어 ──────────────────────────────── #
def main():
    if "nav_page" not in st.session_state:
        st.session_state.nav_page = "chatbot"

    # 📌 사이드바 메뉴 (깔끔하게 버튼만 유지)
    st.sidebar.markdown("### 🍫 초코비 메뉴")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("💬 학사 챗봇", use_container_width=True, type="primary" if st.session_state.nav_page == "chatbot" else "secondary"):
            st.session_state.nav_page = "chatbot"
            st.rerun()

    with col2:
        if st.button("⏳ D-Day", use_container_width=True, type="primary" if st.session_state.nav_page == "dday" else "secondary"):
            st.session_state.nav_page = "dday"
            st.rerun()

    if st.session_state.nav_page == "chatbot":
        render_chatbot_page()
    elif st.session_state.nav_page == "dday":
        render_dday_page()


if __name__ == "__main__":
    main()