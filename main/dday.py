from datetime import datetime

# 대표 학사일정 데이터 (날짜 형식: YYYY-MM-DD)
# 필요에 따라 날짜와 일정 이름을 자유롭게 수정/추가하세요!
ACADEMIC_EVENTS = [
    {"title": "2학기 수강신청", "date": "2026-08-18"},
    {"title": "2학기 개강", "date": "2026-09-01"},
    {"title": "중간고사", "date": "2026-10-20"},
    {"title": "기말고사", "date": "2026-12-15"},
    {"title": "겨울방학 (종강)", "date": "2026-12-22"},
]

def get_dday_list():
    """
    오늘 날짜 기준으로 각 학사일정까지 남은 D-Day를 계산해주는 함수
    """
    today = datetime.now().date()
    result = []

    for event in ACADEMIC_EVENTS:
        # 문자열 날짜를 datetime 객체로 변환
        event_date = datetime.strptime(event["date"], "%Y-%m-%d").date()
        
        # 오늘과의 날짜 차이 계산
        diff = (event_date - today).days

        # D-Day 라벨 만들기
        if diff > 0:
            dday_str = f"D-{diff}"
        elif diff == 0:
            dday_str = "D-Day (오늘!)"
        else:
            dday_str = f"종료됨 (D+{abs(diff)})"

        result.append({
            "title": event["title"],
            "date": event["date"],
            "dday": dday_str,
            "days_left": diff
        })

    # 남은 일수가 적은 순서(다가오는 순)로 정렬해서 반환
    result.sort(key=lambda x: x["days_left"])
    return result

# 테스트용 (이 파일을 직접 실행할 때만 동작)
if __name__ == "__main__":
    ddays = get_dday_list()
    for d in ddays:
        print(f"[{d['dday']}] {d['title']} ({d['date']})")