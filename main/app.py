"""
= 대덕소프트웨어마이스터고등학교 학사일정 AI 챗봇 (Local AI) =
🍫 팀명: 초코비 / 개발자: 윤지원, 이가영
"""
from dday import get_dday_list
import streamlit as st
from datetime import date, timedelta
import requests
import urllib3
import ollama
import json

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ──────────────────────────────── API 및 AI 설정 ──────────────────────────────── #
NICE_API_URL = "https://open.neis.go.kr/hub/SchoolSchedule"

ATPT_OFCDC_SC_CODE = "G10"  # 대전광역시교육청
SD_SCHUL_CODE = "7430310"    # 대덕소프트웨어마이스터고등학교
API_KEY = ""                 # 나이스 API 키 (선택)

LOCAL_MODEL_NAME = "gemma4"


# ──────────────────────────────── 페이지 세팅 ──────────────────────────────── #
st.set_page_config(
    page_title="🍫 초코비 - 대마고 학사일정 서비스",
    page_icon="🍫",
    layout="centered"
)


# ──────────────────────────────── 나이스 API 데이터 호출 ──────────────────────────────── #
def fetch_raw_schedule(from_ymd: str, to_ymd: str) -> list:
    """지정한 기간 사이의 전체 학사일정을 가져옵니다."""
    params = {
        "KEY": API_KEY,
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
    return records


# ──────────────────────────────── 1단계: AI 질문 분석 (조회 범위만 설정) ──────────────────────────────── #
def parse_user_intent_with_ai(user_question: str) -> dict:
    today = date.today()
    current_year = today.year

    prompt = f"""
너는 학생 질문에서 학사일정 API를 조회할 시작일(AA_FROM_YMD)과 종료일(AA_TO_YMD) 범위만 추출하는 파서다.

[오늘 날짜]: {today.strftime('%Y-%m-%d')}

[검색 범위 지침]
- 1학기 관련 질문: {current_year}0301 ~ {current_year}0731
- 2학기 관련 질문: {current_year}0801 ~ {current_year+1}0228
- 특정 월(예: 6월): 해당 월의 1일 ~ 말일 (예: {current_year}0601 ~ {current_year}0630)
- 지정이 없는 경우: {current_year}0301 ~ {current_year+1}0228

[학생 질문]: "{user_question}"

다음 JSON 형식으로만 답해라 (다른 텍스트 금지):
{{
  "AA_FROM_YMD": "YYYYMMDD",
  "AA_TO_YMD": "YYYYMMDD"
}}
"""

    try:
        response = ollama.generate(
            model=LOCAL_MODEL_NAME, 
            prompt=prompt,
            format="json"
        )
        data = json.loads(response['response'])
        if "AA_FROM_YMD" in data and "AA_TO_YMD" in data:
            return data
    except Exception:
        pass

    # Fallback 로직
    text = user_question.lower()
    from_ymd = f"{current_year}0301"
    to_ymd = f"{current_year+1}0228"

    if "2학기" in text:
        from_ymd = f"{current_year}0801"
        to_ymd = f"{current_year+1}0228"
    elif "1학기" in text:
        from_ymd = f"{current_year}0301"
        to_ymd = f"{current_year}0731"

    return {"AA_FROM_YMD": from_ymd, "AA_TO_YMD": to_ymd}


# ──────────────────────────────── 2단계: AI 답변 통합 제어 ──────────────────────────────── #
def ask_ai_with_context(user_question: str) -> str:
    today = date.today()
    text = user_question.strip().lower()

    # 1. 단기 상대 날짜 사전 처리
    if "오늘" in text:
        from_ymd = to_ymd = today.strftime("%Y%m%d")
    elif "내일" in text:
        from_ymd = to_ymd = (today + timedelta(days=1)).strftime("%Y%m%d")
    elif "어제" in text:
        from_ymd = to_ymd = (today - timedelta(days=1)).strftime("%Y%m%d")
    elif "모레" in text:
        from_ymd = to_ymd = (today + timedelta(days=2)).strftime("%Y%m%d")
    else:
        intent = parse_user_intent_with_ai(user_question)
        from_ymd = intent.get("AA_FROM_YMD", today.strftime("%Y0301"))
        to_ymd = intent.get("AA_TO_YMD", today.strftime("%Y1231"))

    # 2. 지정된 기간 동안의 전체 학사일정 가져오기 (키워드 필터링 안 함!)
    raw_events = fetch_raw_schedule(from_ymd, to_ymd)
    schedule_data = "\n".join(raw_events) if raw_events else "등록된 학사일정이 없습니다."

    # 3. AI가 전체 학사일정에서 질문에 답을 찾아 전달
    final_prompt = f"""
너는 학사일정을 안내하는 AI다. 

[학교 학사일정 전체 목록]
{schedule_data}

[학생 질문]
"{user_question}"

[답변 작성 지침]
1. [학교 학사일정 전체 목록]을 확인하고, 학생이 물어본 일정(중간고사, 기말고사, 지필평가, 시험, 방학 등)과 관련된 모든 일자를 찾아서 답변해라.
2. 고등학교 학사일정에서 '중간고사', '기말고사'는 '지필평가', '1차 평가', '고사' 등으로 등록되어 있을 수 있으니 문맥에 맞게 찾아라.
3. 해당하는 일정이 있으면 일자를 마크다운 리스트(- YYYY-MM-DD: 일정명)로 모두 나열해라.
4. 만약 검색된 학사일정 전체 목록 내에 관련된 행사가 전혀 없다면 "등록된 학사일정이 없습니다."라고 답해라.
5. 인사말이나 쓸데없는 설명 없이 정답 목록만 짧게 출력해라.
"""

    try:
        response = ollama.generate(model=LOCAL_MODEL_NAME, prompt=final_prompt)
        return response['response'].strip()
    except Exception as e:
        return f"AI 응답 생성 중 오류가 발생했습니다: {e}"


# ──────────────────────────────── 화면 1: AI 챗봇 ──────────────────────────────── #
def render_chatbot_page():
    st.markdown("""
        <div style="text-align: center; padding: 10px;">
            <h1 style="color: #8B4513; margin-bottom: 0px;">🍫 초코비</h1>
            <p style="color: #666; font-size: 16px;"><b>대덕소프트웨어마이스터고등학교 학사일정 AI 챗봇</b></p>
            <p style="color: #aaa; font-size: 13px;">개발: 윤지원, 이가영 | Windows 11 호환</p>
        </div>
        <hr>
    """, unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "🍫 **초코비 학사일정 챗봇**입니다.\n조회하고 싶은 날짜나 기간, 학사일정(기말고사, 방학 등)을 입력해주세요."}
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("질문을 입력하세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🍫 학사일정 분석 및 조회 중..."):
                response = ask_ai_with_context(prompt)

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


# ──────────────────────────────── 메인 제어 ──────────────────────────────── #
def main():
    if "nav_page" not in st.session_state:
        st.session_state.nav_page = "chatbot"

    st.sidebar.markdown("### 🍫 초코비 메뉴")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("💬 학사일정 챗봇", use_container_width=True, type="primary" if st.session_state.nav_page == "chatbot" else "secondary"):
            st.session_state.nav_page = "chatbot"
            st.rerun()

    with col2:
        if st.button("⏳ 주요 일정 D-Day", use_container_width=True, type="primary" if st.session_state.nav_page == "dday" else "secondary"):
            st.session_state.nav_page = "dday"
            st.rerun()

    st.sidebar.divider()

    if st.session_state.nav_page == "chatbot":
        render_chatbot_page()
    elif st.session_state.nav_page == "dday":
        render_dday_page()


if __name__ == "__main__":
    main()