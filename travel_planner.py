import argparse
import json
import os
import sys
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import openai

# .env 파일 로드
load_dotenv()

# ── API 키 로드 ──────────────────────────────────────────
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")

# Windows cp949 콘솔에서 일부 이모지/비ASCII가 깨져서 UnicodeEncodeError가 날 수 있으므로
# 로그는 ASCII 기반으로 유지하고, 키가 없어도 프로그램이 종료되지 않도록 처리합니다.
if not LLM_API_KEY:
    print("[WARN] LLM_API_KEY not configured. The app will use a local fallback recommendation.")
    print("[WARN] Add LLM_API_KEY=your_key to .env or your environment to enable live LLM calls.")

# ── OpenAI 클라이언트 설정 ────────────────────────────────
client = None
if LLM_API_KEY:
    client = openai.OpenAI(
        api_key=LLM_API_KEY,
        base_url="https://copa.codyssey.kr/v1"
    )

MODEL_NAME = "gemini-3-flash"

# ── 결과 폴더 생성 ────────────────────────────────────────
Path("results").mkdir(exist_ok=True)

# ── 오류 목록 ─────────────────────────────────────────────
errors = []


def reset_errors():
    errors.clear()


def get_fallback_recommendation(date_str):
    month = datetime.strptime(date_str, "%Y-%m-%d").month
    city_map = {
        1: "제주",
        2: "제주",
        3: "경주",
        4: "강릉",
        5: "서울",
        6: "속초",
        7: "부산",
        8: "부산",
        9: "경주",
        10: "전주",
        11: "서울",
        12: "제주",
    }
    city = city_map.get(month, "제주")
    return {
        "recommended_city": city,
        "weather": "계절에 맞는 여행 분위기를 기대할 수 있는 지역입니다.",
        "events": ["지역 대표 축제", "시티투어", "기본 일정 추천"],
        "reason": "실시간 API 키가 없어 로컬 기본 추천을 적용했습니다. 여행 시기와 계절 특성을 반영해 안전하게 추천합니다."
    }


# ── 1단계: LLM으로 여행지 추천 ────────────────────────────
def get_travel_recommendation(date_str):
    print("\n[1/3] 1차 추천 생성 중(LLM)...")

    if client is None:
        print("  - LLM key unavailable. Using local fallback recommendation.")
        errors.append({"step": "llm_recommendation", "type": "KEY_MISSING", "message": "LLM_API_KEY missing"})
        return get_fallback_recommendation(date_str)

    prompt = f"""
당신은 국내 여행 전문가입니다.
여행 날짜: {date_str}

아래 JSON 형식으로만 답변하세요. 다른 텍스트는 절대 포함하지 마세요.

{{
  "recommended_city": "도시명",
  "weather": "해당 시기 날씨 요약",
  "events": ["행사1", "행사2", "행사3"],
  "reason": "추천 이유 2~4문장"
}}
"""

    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "당신은 JSON만 출력하는 여행 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            content = response.choices[0].message.content.strip()

            # JSON 파싱 시도
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            result = json.loads(content)
            print(f"  - recommended_city: \"{result.get('recommended_city', '알 수 없음')}\"")
            return result

        except json.JSONDecodeError:
            if attempt == 0:
                print("  - 파싱 실패, 재시도 중...")
            else:
                print("  - JSON 파싱 최종 실패")
                errors.append({"step": "llm_recommendation", "type": "PARSE_ERROR", "message": "JSON 파싱 실패"})
                return {"recommended_city": "제주", "weather": "알 수 없음", "events": [], "reason": "파싱 실패로 기본값 사용"}

        except Exception as e:
            print(f"  - ERROR: {e}")
            errors.append({"step": "llm_recommendation", "type": "API_ERROR", "message": str(e)})
            return {"recommended_city": "제주", "weather": "알 수 없음", "events": [], "reason": "API 오류로 기본값 사용"}


# ── 2단계: 카카오 맛집 검색 ───────────────────────────────
def search_restaurants(city):
    print("\n[2/3] 맛집 검색 중(Kakao Local API)...")

    if not KAKAO_API_KEY:
        print("  - KAKAO_API_KEY not set. The restaurant section will be left empty.")
        errors.append({"step": "place_search", "type": "KEY_MISSING", "message": "KAKAO_API_KEY not set"})
        return []

    try:
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
        params = {"query": f"{city} 맛집", "size": 5}

        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code == 401:
            print("  - ERROR: authentication failed (401). Check your key settings.")
            errors.append({"step": "place_search", "type": "AUTH_ERROR", "message": "HTTP 401"})
            return []

        if response.status_code == 403:
            print("  - ERROR: authentication failed (403). Check your key settings.")
            errors.append({"step": "place_search", "type": "AUTH_ERROR", "message": "HTTP 403"})
            return []

        response.raise_for_status()
        data = response.json()
        places = data.get("documents", [])

        if not places:
            print("  - Search returned 0 results")
            errors.append({"step": "place_search", "type": "EMPTY_RESULT", "message": f"0 results for query={city} 맛집"})
            return []

        restaurants = []
        for p in places:
            restaurants.append({
                "name": p.get("place_name", ""),
                "address": p.get("road_address_name") or p.get("address_name", ""),
                "category": p.get("category_name", ""),
                "url": p.get("place_url", ""),
                "x": p.get("x", ""),
                "y": p.get("y", "")
            })

        print(f"  - Restaurant search completed: {len(restaurants)} places found")
        return restaurants

    except Exception as e:
        print(f"  - ERROR: {e}")
        errors.append({"step": "place_search", "type": "API_ERROR", "message": str(e)})
        return []


# ── 3단계: LLM으로 최종 리포트 생성 ──────────────────────
def generate_report(date_str, recommendation, restaurants):
    print("\n[3/3] 최종 리포트 생성 중(LLM)...")

    restaurant_text = ""
    if restaurants:
        for r in restaurants:
            restaurant_text += f"- {r['name']} | {r['address']} | {r['category']} | {r['url']}\n"
    else:
        restaurant_text = "데이터 없음"

    prompt = f"""
다음 정보를 바탕으로 국내 여행 리포트를 Markdown 형식으로 작성하세요.

여행 날짜: {date_str}
추천 도시: {recommendation.get('recommended_city')}
날씨: {recommendation.get('weather')}
행사/축제: {', '.join(recommendation.get('events', []))}
추천 이유: {recommendation.get('reason')}
맛집 목록:
{restaurant_text}

아래 형식으로 작성하세요:

# {date_str} 국내 여행 추천 리포트
## 추천 지역
## 추천 이유
## 날씨 요약
## 행사/축제
## 맛집 추천
## 1일 일정 제안
## 오류 요약
"""

    if client is None:
        print("  - LLM unavailable; generating a local fallback report.")
        errors.append({"step": "report_generation", "type": "KEY_MISSING", "message": "LLM_API_KEY missing"})
        return f"# {date_str} 국내 여행 추천 리포트\n\n## 추천 지역\n{recommendation.get('recommended_city')}\n\n## 추천 이유\n{recommendation.get('reason')}\n\n## 날씨 요약\n{recommendation.get('weather')}\n\n## 행사/축제\n{', '.join(recommendation.get('events', [])) or '없음'}\n\n## 맛집 추천\n데이터 없음\n\n## 1일 일정 제안\n- 오전: 지역 명소 방문\n- 오후: 추천 관광지 체험\n- 저녁: 현지 음식 체험\n\n## 오류 요약\n- [report_generation] KEY_MISSING: LLM_API_KEY missing"

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "당신은 여행 리포트를 작성하는 전문가입니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        report = response.choices[0].message.content.strip()
        print("  - 리포트 생성 완료")
        return report

    except Exception as e:
        print(f"  - ERROR: {e}")
        errors.append({"step": "report_generation", "type": "API_ERROR", "message": str(e)})
        return f"# {date_str} 국내 여행 추천 리포트\n\n리포트 생성 실패: {e}"


# ── 결과 저장 ─────────────────────────────────────────────
def save_results(date_str, recommendation, restaurants, report):
    # JSON 저장
    json_data = {
        "date": date_str,
        "recommendation": recommendation,
        "restaurants": restaurants,
        "errors": errors
    }
    json_path = f"results/{date_str}_travel_data.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    # Markdown 저장
    md_path = f"results/{date_str}_travel_plan.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report)
        if errors:
            f.write("\n\n## 오류 요약\n")
            for err in errors:
                f.write(f"- [{err['step']}] {err['type']}: {err['message']}\n")

    return json_path, md_path


# ── 메인 ──────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="국내 여행지 추천 프로그램")
    parser.add_argument("--date", required=True, help="여행 날짜 (YYYY-MM-DD)")
    args = parser.parse_args()

    # 날짜 형식 검증
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print("ERROR: invalid date format. Example: --date \"2025-08-01\"")
        exit(1)

    reset_errors()

    print("=" * 40)
    print(" 국내 여행지 추천 프로그램")
    print(f"Date: {args.date}")
    print("=" * 40)

    # 실행
    recommendation = get_travel_recommendation(args.date)
    city = recommendation.get("recommended_city", "제주")
    restaurants = search_restaurants(city)
    report = generate_report(args.date, recommendation, restaurants)
    json_path, md_path = save_results(args.date, recommendation, restaurants, report)

    print("\n" + "=" * 40)
    print("Completed successfully")
    print(f"JSON : {json_path}")
    print(f"Report: {md_path}")
    print(f"Done. Check {md_path} for the result.")


if __name__ == "__main__":
    main()