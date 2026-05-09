"""
weather_api.py
==============
공공데이터포털 기상청 단기예보 API - Python 연동 예제
평가 제출용 | 기상청_단기예보 ((구)동네예보) 조회서비스

필요 패키지:
    pip install requests
"""

import requests
from datetime import datetime, timedelta

# ──────────────────────────────────────────
#  설정: 본인 API 인증키를 여기에 입력하세요
# ──────────────────────────────────────────
API_KEY = "5aee2bb9f6aeb0b3f495180b5033fa9b57451318182b13272dbede77b8a40486"

# 서울 격자 좌표 (기상청 제공 격자 기준)
NX = 60
NY = 127

# API 엔드포인트
BASE_URL = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"


def get_base_datetime():
    """
    기상청 단기예보 발표 기준 날짜·시간 계산
    발표 시각: 02, 05, 08, 11, 14, 17, 20, 23시 (발표 후 10분부터 조회 가능)
    """
    now = datetime.now()
    slots = [2, 5, 8, 11, 14, 17, 20, 23]

    base_hour = 23  # 기본값
    for h in reversed(slots):
        if now.hour > h or (now.hour == h and now.minute >= 10):
            base_hour = h
            break
    else:
        # 자정 이후 02:10 전 → 전날 23시 기준
        now = now - timedelta(days=1)

    base_date = now.strftime("%Y%m%d")
    base_time = f"{base_hour:02d}00"
    return base_date, base_time


def get_ultra_srt_ncst():
    """
    초단기실황 조회 (현재 기온·강수·바람·습도 등)
    """
    now = datetime.now()
    # 초단기실황: 매 시 45분 이후 조회 가능 (이전 정시 기준)
    if now.minute < 45:
        base_hour = (now.hour - 1) % 24
    else:
        base_hour = now.hour
    base_date = now.strftime("%Y%m%d")
    base_time = f"{base_hour:02d}00"

    url = f"{BASE_URL}/getUltraSrtNcst"
    params = {
        "serviceKey": API_KEY,
        "numOfRows": 20,
        "pageNo": 1,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": NX,
        "ny": NY,
    }

    res = requests.get(url, params=params, timeout=10)
    res.raise_for_status()
    data = res.json()

    items = data["response"]["body"]["items"]["item"]
    result = {item["category"]: item["obsrValue"] for item in items}
    return result


def get_village_fcst():
    """
    단기예보 조회 (오늘 ~ 내일 모레까지 3시간 간격 예보)
    """
    base_date, base_time = get_base_datetime()

    url = f"{BASE_URL}/getVilageFcst"
    params = {
        "serviceKey": API_KEY,
        "numOfRows": 300,
        "pageNo": 1,
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": NX,
        "ny": NY,
    }

    res = requests.get(url, params=params, timeout=10)
    res.raise_for_status()
    data = res.json()

    items = data["response"]["body"]["items"]["item"]

    # 시간대별로 정리
    fcst = {}
    for item in items:
        key = item["fcstDate"] + item["fcstTime"]
        if key not in fcst:
            fcst[key] = {}
        fcst[key][item["category"]] = item["fcstValue"]

    return fcst


def sky_to_text(sky_code, pty_code="0"):
    """하늘 상태 코드 → 한국어 텍스트"""
    pty_map = {"0": "", "1": "비", "2": "비/눈", "3": "눈", "4": "소나기"}
    sky_map = {"1": "맑음", "3": "구름 많음", "4": "흐림"}
    if pty_code != "0":
        return pty_map.get(pty_code, "알 수 없음")
    return sky_map.get(sky_code, "알 수 없음")


def print_current_weather():
    """현재 날씨 출력"""
    print("=" * 50)
    print("  공공데이터포털 기상청 API - 현재 날씨 조회")
    print("=" * 50)

    try:
        ncst = get_ultra_srt_ncst()

        temp   = ncst.get("T1H", "N/A")   # 기온 (°C)
        rain   = ncst.get("RN1", "N/A")   # 1시간 강수량 (mm)
        sky    = ncst.get("SKY", "N/A")   # 하늘 상태
        pty    = ncst.get("PTY", "0")     # 강수 형태
        reh    = ncst.get("REH", "N/A")   # 습도 (%)
        wsd    = ncst.get("WSD", "N/A")   # 풍속 (m/s)
        vec    = ncst.get("VEC", "N/A")   # 풍향 (deg)

        sky_text = sky_to_text(sky, pty)

        print(f"\n📍 서울 (격자 nx={NX}, ny={NY})")
        print(f"  기온       : {temp}°C")
        print(f"  하늘 상태   : {sky_text}")
        print(f"  습도       : {reh}%")
        print(f"  풍속       : {wsd} m/s")
        print(f"  풍향       : {vec}°")
        print(f"  1시간 강수   : {rain} mm")

    except Exception as e:
        print(f"\n[오류] {e}")
        print("→ API_KEY가 올바른지, 발급 후 활성화(1시간 내외 소요)됐는지 확인하세요.")


def print_forecast():
    """단기예보 출력 (다음 12시간)"""
    print("\n" + "=" * 50)
    print("  단기예보 (이후 12시간)")
    print("=" * 50)

    try:
        fcst = get_village_fcst()
        keys = sorted(fcst.keys())[:8]  # 3시간 간격 → 8개 = 24시간

        for key in keys:
            data = fcst[key]
            date = key[:8]
            time = key[8:]
            tmp  = data.get("TMP", "--")   # 기온
            pop  = data.get("POP", "--")   # 강수확률
            sky  = data.get("SKY", "1")
            pty  = data.get("PTY", "0")
            sky_text = sky_to_text(sky, pty)
            print(f"  {date[4:6]}/{date[6:8]} {time[:2]}:00  "
                  f"{tmp:>3}°C  강수확률 {pop:>2}%  {sky_text}")

    except Exception as e:
        print(f"\n[오류] {e}")


if __name__ == "__main__":
    print_current_weather()
    print_forecast()
    print("\n[완료] weather_dashboard.html을 브라우저에서 열어 웹 버전도 확인하세요.")
