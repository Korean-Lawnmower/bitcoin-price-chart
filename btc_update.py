import requests
import os
from datetime import datetime, timedelta, timezone
import json
import sys

# API 주소
URL = 'https://blockchain.info/ticker'

# 타겟 currency
usd = "USD"
kor = "KRW"

# 파일 경로
README_PATH = "README.md"
HISTORY_PATH = "history.txt"

def fetch_api(usd, kor) -> dict[str, object]:
    """
    blockchain.com 에서 지원하는 통화별 비트코인 가격 변동 api
    timestamp 와 함께 return
    실패 시 빈 dict 반환
    """
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()  # 200이 아닌 경우 예외 발생
        data = response.json()
    except requests.RequestException as e:
        print(f"[ERROR] API 요청 실패: {e}", file=sys.stderr)
        return {}
    except ValueError as e:
        print(f"[ERROR] JSON 파싱 실패: {e}", file=sys.stderr)
        return {}

    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

    # 데이터 유효성 체크
    if usd not in data or kor not in data:
        print("[ERROR] 응답 데이터에 필요한 통화 정보가 없습니다.", file=sys.stderr)
        return {}

    return {
        "timestamp": now,
        "USD": data[usd]["last"],
        "KRW": data[kor]["last"]
    }

def update_history(fetched_object):
    """
    history.txt 업데이트
    fetch_api 의 값이 {}이 아니라면 가장 오래된 timestamp 을 제외 후 해당 값 업데이트
    최대 10개의 timestamp 만 보존
    """
    if not fetched_object:
        print("[WARNING] 새 데이터가 없으므로 history 업데이트를 건너뜁니다.", file=sys.stderr)
        return

    history = []
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                print("[WARNING] history.txt 파싱 실패, 새로 생성합니다.", file=sys.stderr)
                history = []

    # Append new record
    history.append(fetched_object)

    # Keep only last 10
    if len(history) > 10:
        history = history[-10:]

    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def update_readme():
    """
    history.txt를 바탕으로 README.md를 ASCII 선 그래프로 업데이트
    각 포인트는 '*'로 표시, 기울기는 '/' '\' 또는 '_'로 연결
    """
    if not os.path.exists(HISTORY_PATH):
        print("[ERROR] history.txt 파일이 없습니다.", file=sys.stderr)
        return

    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        history = json.load(f)

    if not history:
        print("[ERROR] history.txt 가 비어 있습니다.", file=sys.stderr)
        return

    usd_prices = [item["USD"] for item in history]
    krw_prices = [item["KRW"] for item in history]
    timestamps = [item["timestamp"] for item in history]

    def make_ascii_line_chart(values, height=8):
        """
        Create an ASCII line chart from numeric values.
        '*' marks actual data points.
        '/' and '\' show slopes, '_' shows flat movement.
        """
        min_v, max_v = min(values), max(values)
        if max_v == min_v:
            levels = [height // 2] * len(values)
        else:
            levels = [int((v - min_v) / (max_v - min_v) * (height - 1)) for v in values]

        # Create empty grid (top row = highest value)
        grid = [[" " for _ in range(len(values))] for _ in range(height)]

        for i, lvl in enumerate(levels):
            row = height - 1 - lvl
            grid[row][i] = "*"

            if i > 0:
                prev_lvl = levels[i - 1]
                if lvl > prev_lvl:  # going up
                    for y in range(height - 1 - prev_lvl - 1, row, -1):
                        grid[y][i - 1] = "/"
                elif lvl < prev_lvl:  # going down
                    for y in range(row + 1, height - 1 - prev_lvl):
                        grid[y][i - 1] = "\\"
                else:  # flat
                    grid[row][i - 1] = "_"

        return "\n".join("".join(r) for r in grid)

    usd_chart = make_ascii_line_chart(usd_prices)
    krw_chart = make_ascii_line_chart(krw_prices)

    price_labels = "\n".join(f"{t}: USD {u:,.2f} | KRW {k:,.0f}"
                             for t, u, k in zip(timestamps, usd_prices, krw_prices))

    KST = timezone(timedelta(hours=9))
    now_str = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

    readme_content = f"""# 📈 Bitcoin Price Tracker (ASCII Style)
    ## USD 가격 변동 
    {usd_chart}
    ## KRW 가격 변동
    {krw_chart}
    📋 가격 기록:
    {price_labels}
    
🕐 업데이트 시간 : {now_str} (KST)
"""

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(readme_content)

if __name__ == "__main__":
    data = fetch_api(usd, kor)
    print("Fetched data:", data)
    if data:
        update_history(data)
        update_readme()
    else:
        print("[ERROR] 데이터 수집 실패로 업데이트 건너뜀", file=sys.stderr)