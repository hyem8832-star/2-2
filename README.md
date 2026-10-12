# 🗺️ 국내 여행지 추천 프로그램

LLM API와 카카오 지도 API를 활용하여  
여행 날짜를 입력하면 국내 여행지를 추천하고  
맛집 정보와 여행 리포트를 자동 생성하는 프로그램입니다.

---

## 📁 프로젝트 구조

```
travel_planner/
├── travel_planner.py   # 메인 실행 파일
├── requirements.txt    # 필요 라이브러리 목록
├── .env                # API 키 설정 (직접 생성 필요, 절대 공유 금지)
├── README.md           # 프로젝트 설명서
└── results/            # 실행 결과 저장 폴더
    ├── YYYY-MM-DD_travel_data.json
    └── YYYY-MM-DD_travel_plan.md
```

---

## ⚙️ 설치 방법

```bash
pip install -r requirements.txt
```

---

## 🔑 API 키 설정 방법

프로젝트 폴더에 `.env` 파일을 생성하고 아래와 같이 작성합니다.

```
LLM_API_KEY=여기에_LLM_API_키_입력
KAKAO_API_KEY=여기에_카카오_API_키_입력
```

### Windows PowerShell (현재 세션에만 적용)
```powershell
$env:LLM_API_KEY="YOUR_KEY"
$env:KAKAO_API_KEY="YOUR_KEY"
```

### macOS/Linux (현재 터미널 세션에만 적용)
```bash
export LLM_API_KEY="YOUR_KEY"
export KAKAO_API_KEY="YOUR_KEY"
```

> ⚠️ **주의**: 실제 키 값은 절대 README, 결과 파일, 코드에 포함하지 마세요!

---

## ▶️ 실행 방법

```bash
python travel_planner.py --date "YYYY-MM-DD"
```

### 실행 예시

```bash
python travel_planner.py --date "2025-08-01"
```

### 실행 출력 예시

```
[1/3] 1차 추천 생성 중(LLM)...
  - recommended_city: "강릉"
[2/3] 맛집 검색 중(지도/장소 API)...
  - 맛집 5곳 검색 완료
[3/3] 최종 리포트 생성 중(LLM)...
  - 리포트 생성 완료

완료! results/2025-08-01_travel_plan.md 를 확인하세요.
```

### 날짜 형식 오류 시

```
오류: 날짜 형식이 올바르지 않습니다.
사용법: python travel_planner.py --date "YYYY-MM-DD"
```

---

## 📂 결과물 확인 방법

실행 후 `results/` 폴더에 아래 파일이 생성됩니다.

| 파일명 | 설명 |
|---|---|
| `YYYY-MM-DD_travel_data.json` | 1차 추천 + 맛집 검색 원본 데이터 |
| `YYYY-MM-DD_travel_plan.md` | 최종 여행 리포트 |

### 원본 JSON 구조 예시

```json
{
  "recommended_city": "강릉",
  "weather": "8월 초 평균 28°C 내외, 맑고 더운 여름 날씨",
  "events": ["강릉 커피 축제", "해변 여름 축제"],
  "reason": "강릉은 여름철 해변과 커피 문화로 유명합니다.",
  "restaurants": [],
  "errors": [
    {"step": "place_search", "type": "AUTH_ERROR", "message": "HTTP 403"}
  ]
}
```

### 최종 리포트 구조 예시

```
# 2025-08-01 국내 여행 추천 리포트
## 추천 지역
## 추천 이유
## 날씨 요약
## 행사/축제
## 맛집 추천
## 1일 일정 제안
## 오류 요약(errors)
```

---

## ⚠️ 오류 처리 정책

| 오류 상황 | 처리 방식 |
|---|---|
| API 키 미설정 | 즉시 종료 + 설정 방법 안내 |
| 날짜 형식 오류 | 즉시 종료 + 사용법 안내 |
| 지도/장소 API 실패 | 맛집 "데이터 없음" 처리 후 리포트 계속 생성 |
| LLM JSON 파싱 실패 | 재시도 1회 후 실패 시 오류 기록 |

---

## 🔒 보안 주의 사항

- API 키는 반드시 `.env` 파일에만 저장합니다.
- `.env` 파일을 GitHub, 카카오톡, 이메일 등으로 **절대 공유하지 않습니다.**
- `.gitignore`에 `.env`를 추가하여 실수로 업로드되지 않도록 합니다.
- API 키를 코드에 직접 작성하지 않습니다.
- 키를 `.env`로 관리하면 코드 수정 없이 키 교체가 가능하고, 과금/쿼터 사고를 예방할 수 있습니다.

---

## 🛠️ 사용 기술

| 항목 | 내용 |
|---|---|
| 언어 | Python 3.10 이상 |
| LLM API | Gemini 계열 (OpenAI 호환) |
| 지도/장소 API | Kakao Local API |
| 주요 라이브러리 | requests, python-dotenv, argparse |
