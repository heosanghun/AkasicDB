# ⛵ AkasicDB: Intelligent Yard Copilot

![AkasicDB Version](https://img.shields.io/badge/version-1.0.0-emerald.svg)
![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

**AkasicDB**는 해양·항만 물류산업의 지능형 혁신(AX)을 위해 설계된 **차세대 Omni RAG 엔진 및 XAI 대시보드**입니다. 복잡한 항만 야드 운영 과정에서 발생하는 수많은 변수(선박 접안 지연, 재취급률, 장비 동선 등)를 그래프(Graph), 관계형(Relational), 벡터(Vector) DB로 통합하여 실시간으로 최적의 의사결정을 지원합니다.

---

## ✨ 핵심 아키텍처 (Core Architecture)

### 1. ⚡ Triple-Store 병합 엔진 (Omni RAG)
기존의 RAG 시스템이 벡터 DB만을 활용하는 한계를 극복하기 위해, AkasicDB는 세 가지 데이터베이스를 단일 연산자(Traversal-Join-Similarity Operator) 안에서 초고속으로 병합 처리합니다.
- **Graph Store (`g_store`)**: 선박 ➔ 야드블록 ➔ 컨테이너 ➔ 장비로 이어지는 **다중 홉(Multi-hop) 위상 기하학** 매핑
- **Relational Store (`r_store`)**: 타임스탬프, 엔티티 타입 등 메타데이터 필터링
- **Vector Store (`v_store`)**: 코사인 유사도를 활용한 비정형 문서(Chunk) 및 이미지 매칭

> 이 아키텍처는 **10,000개 이상의 합성 데이터(Synthetic Data)**를 대상으로 진행한 부하 테스트(Benchmark)에서 **0.1ms 대의 극단적으로 빠른 쿼리 탐색 속도**를 증명했습니다.

### 2. 🎨 프리미엄 Chat-Centric UI/UX
복잡한 데이터를 한눈에 파악할 수 있도록, 글로벌 IT 기업(Apple, OpenAI 등) 트렌드를 반영한 **Midnight Dark Theme & Glassmorphism** 기반의 대화형 중심(Chat-centric) 인터페이스를 탑재했습니다.
- **Analysis Drawer (분석 서랍):** AI의 답변 말풍선에 생성되는 `[📊 View Evidence]` 버튼 클릭 시, 우측에서 3종류의 XAI 뷰(네트워크 그래프, 테이블, 이미지 청크)가 슬라이딩되어 출력됩니다.
- **실시간 스트리밍 (SSE):** AI의 분석 결과가 서버 통신을 거쳐 타자기처럼 실시간으로 타이핑(Streaming)되는 완벽한 사용자 경험을 제공합니다.

---

## 🚀 6대 주요 상용화 기능

1. **지능형 라우터 (Semantic Router):** 사용자의 질의를 분석하여 1만 개 데이터 중 최적의 시작 노드(Vessel, Block 등)를 자동 타겟팅.
2. **대화 내역 영구 저장 (SQLite):** `chat_history.db`를 통해 과거의 질문과 세션 기록을 안전하게 보존.
3. **Data Upload Wizard:** 항만 매뉴얼, SOP 문서 등을 업로드하고 청킹(Chunking)할 수 있는 관리자 화면 UI.
4. **사용자 보안 로그인:** 사번(Employee ID) 기반 보안 접근 제어 (오버레이 적용).
5. **AI 피드백 루프:** 답변 하단의 `[👍/👎]` 버튼을 통한 품질 평가 인터페이스.
6. **보고서 내보내기 (Export):** 추출된 XAI 증거 자료를 `[📥 Export]` 버튼으로 외부 공유 가능 (UI 레벨 구현).

---

## 🛠 시스템 요구사항 및 실행 방법

### 의존성 설치
```bash
pip install flask
```
*(기본적인 Python 표준 라이브러리 `sqlite3`, `json`, `collections` 등을 사용하며 의존성을 최소화했습니다.)*

### 서버 구동
```bash
python akasic/api/server.py
```
1. 위 명령어를 실행하면 엔진이 부팅되며 **약 10,650개의 항만 합성 데이터**를 메모리에 실시간으로 생성 및 적재합니다.
2. 부팅이 완료되면 웹 브라우저에서 `http://localhost:5000`에 접속합니다.
3. "심스리얼리티", "3B 블록 추가 이송", "1A 블록 혼잡도" 등의 키워드를 입력하여 강력한 Omni RAG 검색을 테스트해 보세요.

---

## 🤝 Partners
* **개발 및 원천 기술사:** 심스리얼리티 (Sims Reality)
* **공동 연구:** (주)토탈소프트뱅크 (TSB)

이 프로젝트는 항만 야드 운영 최적화 솔루션 실증을 위한 프로토타입으로, 추후 sLLM 탑재 및 CATOS(터미널운영시스템) 연동을 통해 확장될 예정입니다.
