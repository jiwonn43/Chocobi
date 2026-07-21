"""
= 대덕소프트웨어마이스터고등학교 학사일정 챗봇 =
🍫 팀명: 초코비 / 개발자: 윤지원, 이가영
"""

import streamlit as st
from datetime import date, timedelta, datetime
import requests

# ──────────────────────────────── API 설정 ──────────────────────────────── #
# 나이스 Open API 공식 Endpoint (학사일정)
NICE_API_URL = "https://open.neis.go.kr/hub/SchoolSchedule"

ATPT_OFCDC_SC_CODE = "G10"  # 대전광역시교육청
SD_SCHUL_CODE = "7430310"    # 대덕소프트웨어마이스터고등학교
API_KEY = ""                 # 발급받은 API 키가 있다면 입력 (없어도 기본 작동)


# ──────────────────────────────── 페이지 세팅 ──────────────────────────────── #
st.set_page_config(
    page_title="🍫 초코비 - 대마고 학사일정 챗봇",
    page_icon="🍫",
    layout="centered"
)


# ──────────────────────────────── API 호출 함수 ──────────────────────────────── #
def fetch_school_schedule(search_date: date) -> list:
    """
    지정한 날짜(date)의 대마고 학사일정을 조회합니다.
    """
    date_str = search_date.strftime("%Y%m%d")  # YYYYMMDD 포맷
    
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
        response = requests.get(NICE_API_URL, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            
            # API 응답 성공 여부 확인
            if "SchoolSchedule" in data:
                schedule_data = data["SchoolSchedule"][1]["row"]
                events = [item["EVENT_NM"] for item in schedule_data if "EVENT_NM" in item]
                return events
            else:
                # 일정 데이터가 없는 경우 (RESULT.INFO-200 등)
                return []
        else:
            st.error(f"API 요청 실패 (상태 코드: {response.status_code})")
            return []
    except Exception as e:
        st.error(f"통신 중 오류가 발생했습니다: {e}")
        return []


def parse_user_input(text: str) -> date | None:
    """
    사용자 입력("오늘", "내일", "2026-05-15" 등)을 date 객체로 변환합니다.
    """
    text = text.strip().lower()
    today = date.today()

    if text in ["오늘", "today"]:
        return today
    elif text in ["내일", "tomorrow"]:
        return today + timedelta(days=1)
    elif text in ["어제", "yesterday"]:
        return today - timedelta(days=1)
    elif text in ["글피"]:
        return today + timedelta(days=2)
    else:
        # YYYY-MM-DD 또는 YYYYMMDD 등의 날짜 형식 파싱 시도
        for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d", "%m-%d", "%m/%d"):
            try:
                dt = datetime.strptime(text, fmt)
                # 연도가 생략된 경우 올해 연도 적용
                if fmt in ("%m-%d", "%m/%d"):
                    dt = dt.replace(year=today.year)
                return dt.date()
            except ValueError:
                continue
    return None


# ──────────────────────────────── 메인 화면 구성 ──────────────────────────────── #
def main():
    # 헤더
    st.markdown("""
        <div style="text-align: center; padding: 10px;">
            <h1 style="color: #8B4513; margin-bottom: 0px;">🍫 초코비</h1>
            <p style="color: #666; font-size: 16px;"><b>대덕소프트웨어마이스터고등학교 학사일정 챗봇</b></p>
            <p style="color: #aaa; font-size: 13px;">개발: 윤지원, 이가영 | Windows 11 호환</p>
        </div>
        <hr>
    """, unsafe_allow_html=True)

    # 세션 상태(대화 기록) 초기화
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "안녕하세요! 🍫 **초코비**입니다.\n알고 싶은 날짜를 입력해 주세요! (예: `오늘`, `내일`, `2026-05-15`)"}
        ]

    # 기존 대화 내용 출력
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 입력 처리
    if prompt := st.chat_input("날짜를 입력하세요 (예: 오늘, 내일, 5-20)..."):
        # 1. 사용자 메시지 표시
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. 날짜 해석 및 API 조회
        target_date = parse_user_input(prompt)

        with st.chat_message("assistant"):
            if target_date:
                formatted_date_str = target_date.strftime("%Y년 %m월 %d일")
                with st.spinner(f"🔍 {formatted_date_str} 학사일정을 조회 중입니다..."):
                    events = fetch_school_schedule(target_date)

                if events:
                    event_list_text = "\n".join([f"- **{e}**" for e in events])
                    response = f"📅 **{formatted_date_str}** 학사일정입니다:\n\n{event_list_text}"
                else:
                    response = f"📅 **{formatted_date_str}**에는 등록된 학사일정이 없습니다. (휴일 또는 일정 없음)"
            else:
                response = "❓ 날짜 형식을 인식하지 못했습니다.\n\n`오늘`, `내일`, 또는 `2026-05-15`, `5-15` 형태로 입력해 주세요!"

            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()