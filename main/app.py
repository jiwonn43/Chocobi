"""
= 대덕소프트웨어마이스터고등학교 학사일정 AI 챗봇 (Local AI) =
🍫 팀명: 초코비 / 개발자: 윤지원, 이가영
"""
from dday import get_dday_list
import streamlit as st
from datetime import date, timedelta, datetime
import requests
import urllib3
import ollama

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ──────────────────────────────── API 및 AI 설정 ──────────────────────────────── #
NICE_API_URL = "https://open.neis.go.kr/hub/SchoolSchedule"

ATPT_OFCDC_SC_CODE = "G10"  # 대전광역시교육청
SD_SCHUL_CODE = "7430310"    # 대덕소프트웨어마이스터고등학교
API_KEY = ""                 # 나이스 API 키 (선택)

# 🤖 컴퓨터에 설치된 로컬 AI 모델명
LOCAL_MODEL_NAME = "gemma4"


# ──────────────────────────────── 페이지 세팅 ──────────────────────────────── #
st.set_page_config(
    page_title="🍫 초코비 - 대마고 학사일정 챗봇",
    page_icon="🍫",
    layout="centered"
)


# ──────────────────────────────── API 호출 함수 ──────────────────────────────── #
def fetch_single_day_schedule(target_date: date) -> list:
    """하루 치 학사일정을 조회합니다."""
    date_str = target_date.strftime("%Y%m%d")
    params = {
        "KEY": API_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
        "SD_SCHUL_CODE": SD_SCHUL_CODE,
        "AA_YMD": date_str
    }
    try:
        response = requests.get(NICE_API_URL, params=params, timeout=3, verify=False)
        if response.status_code == 200:
            data = response.json()
            if "SchoolSchedule" in data:
                for item in data["SchoolSchedule"]:
                    if "row" in item:
                        return [row["EVENT_NM"] for row in item["row"] if "EVENT_NM" in row]
    except Exception:
        pass
    return []


def fetch_schedule_range(start_date: date, end_date: date) -> str:
    """지정한 날짜 범위의 학사일정 텍스트를 생성합니다."""
    records = []
    curr = start_date
    while curr <= end_date:
        events = fetch_single_day_schedule(curr)
        date_str = curr.strftime("%Y-%m-%d(%a)")
        if events:
            records.append(f"- {date_str}: {', '.join(events)}")
        else:
            records.append(f"- {date_str}: 일정 없음")
        curr += timedelta(days=1)
    return "\n".join(records)


# ──────────────────────────────── 날짜 계산 전담 함수 (Python) ──────────────────────────────── #
def determine_target_date_range(user_text: str) -> tuple[date, date, str]:
    """사용자 질문을 분석하여 정확한 (시작일, 종료일, 범위 설명)을 계산합니다."""
    today = date.today()
    text = user_text.strip().lower()

    weekdays = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}

    # 1. '저번주' / '지난주'
    if "저번주" in text or "저번 주" in text or "지난주" in text or "지난 주" in text:
        last_week_monday = today - timedelta(days=today.weekday() + 7)
        
        for day_name, day_code in weekdays.items():
            if f"{day_name}요일" in text or f"{day_name}욜" in text:
                target = last_week_monday + timedelta(days=day_code)
                return target, target, f"저번주 {day_name}요일({target.strftime('%Y-%m-%d')})"
        
        last_week_sunday = last_week_monday + timedelta(days=6)
        return last_week_monday, last_week_sunday, f"저번주({last_week_monday.strftime('%Y-%m-%d')} ~ {last_week_sunday.strftime('%Y-%m-%d')})"

    # 2. '다음주'
    if "다음주" in text or "다음 주" in text:
        next_week_monday = today + timedelta(days=(7 - today.weekday()))
        
        for day_name, day_code in weekdays.items():
            if f"{day_name}요일" in text or f"{day_name}욜" in text:
                target = next_week_monday + timedelta(days=day_code)
                return target, target, f"다음주 {day_name}요일({target.strftime('%Y-%m-%d')})"
        
        next_week_sunday = next_week_monday + timedelta(days=6)
        return next_week_monday, next_week_sunday, f"다음주({next_week_monday.strftime('%Y-%m-%d')} ~ {next_week_sunday.strftime('%Y-%m-%d')})"

    # 3. '이번주'
    if "이번주" in text or "이번 주" in text or "주간" in text:
        this_week_monday = today - timedelta(days=today.weekday())
        
        for day_name, day_code in weekdays.items():
            if f"{day_name}요일" in text or f"{day_name}욜" in text:
                target = this_week_monday + timedelta(days=day_code)
                return target, target, f"이번주 {day_name}요일({target.strftime('%Y-%m-%d')})"
        
        this_week_sunday = this_week_monday + timedelta(days=6)
        return this_week_monday, this_week_sunday, f"이번주({this_week_monday.strftime('%Y-%m-%d')} ~ {this_week_sunday.strftime('%Y-%m-%d')})"

    # 4. 상대 단어 처리
    if "어제" in text:
        target = today - timedelta(days=1)
        return target, target, f"어제({target.strftime('%Y-%m-%d')})"
    elif "내일" in text:
        target = today + timedelta(days=1)
        return target, target, f"내일({target.strftime('%Y-%m-%d')})"
    elif "모레" in text:
        target = today + timedelta(days=2)
        return target, target, f"모레({target.strftime('%Y-%m-%d')})"

    # 기본값: 오늘 기준 이번 주 전체
    this_week_monday = today - timedelta(days=today.weekday())
    this_week_sunday = this_week_monday + timedelta(days=6)
    return this_week_monday, this_week_sunday, f"이번주({this_week_monday.strftime('%Y-%m-%d')} ~ {this_week_sunday.strftime('%Y-%m-%d')})"


# ──────────────────────────────── AI 답변 생성 (간결성 극대화) ──────────────────────────────── #
def ask_ai_with_context(user_question: str) -> str:
    """인사말 및 부연 설명 없이 오직 학사일정만 간결하게 출력합니다."""
    today = date.today()
    start_date, end_date, date_label = determine_target_date_range(user_question)
    schedule_data = fetch_schedule_range(start_date, end_date)

    prompt = f"""
너는 학사일정 정보만 정확히 전달하는 출력 시스템이다.

[조회 기간]
{date_label}

[조회된 학사일정 데이터]
{schedule_data}

[학생 질문]
"{user_question}"

[출력 규칙 - 엄격 준수]
1. "안녕하세요", "요청하신 내용입니다", "감사합니다" 등의 인사말, 서론, 결론을 절대 포함하지 마라.
2. 질문에 해당하는 날짜의 학사일정 정보만 마크다운 목록 형태(- )로 바로 출력해라.
3. 일정이 없는 경우 "등록된 학사일정이 없습니다." 한 줄만 출력해라.
4. 오직 날짜와 학사일정 내용만 간결하게 핵심만 답변해라.
"""

    try:
        response = ollama.generate(model=LOCAL_MODEL_NAME, prompt=prompt)
        return response['response'].strip()
    except Exception as e:
        return f"AI 응답 생성 중 오류가 발생했습니다: {e}"


# ──────────────────────────────── 메인 화면 구성 ──────────────────────────────── #
def main():
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
            {"role": "assistant", "content": "🍫 **초코비 학사일정 챗봇**입니다.\n조회하고 싶은 날짜나 기간을 입력해주세요."}
        ]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("질문을 입력하세요..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("🍫 학사일정 확인 중..."):
                response = ask_ai_with_context(prompt)

            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()