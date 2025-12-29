# Doc Manager V4 사용자 메뉴얼

이 문서는 **Doc Manager V4 (AI 기반 문서 관리 시스템)**의 사용법을 안내합니다.

---

## 1. 시스템 개요

Doc Manager V4는 사용자가 작성한 마크다운 노트를 자동으로 감지하여 **요약(L1)**하고, 관련 문서를 **클러스터링(L2)**하여 인사이트를 도출하는 "Headless" AI 시스템입니다.

### 주요 기능
*   **자동 감지**: `01_Sources` 폴더에 파일이 생성/수정되면 자동으로 처리합니다.
*   **AI 요약**: 문서의 카테고리(Idea, Work 등)에 맞는 프롬프트를 사용하여 요약을 생성합니다.
*   **피드백 루프**: 생성된 요약에 대해 사용자가 `Review` 파일을 통해 평가(Good/Bad)하고 수정 요청을 할 수 있습니다.
*   **지식 연결**: 벡터 임베딩을 사용하여 유사한 문서를 찾고, L2(상위 개념) 문서를 자동 생성합니다.
*   **학습 데이터화**: 쌓인 데이터를 AI 학습용(SFT/DPO)으로 내보낼 수 있습니다.

---

## 2. 설치 및 실행

이 시스템은 Docker를 통해 손쉽게 실행할 수 있습니다.

### 실행 방법
프로젝트 루트 폴더에서 다음 명령어를 실행하세요:

```bash
docker compose up -d
# 또는
docker compose up -d --build
```

### 서비스 확인
*   **메인 대시보드**: `http://localhost:8501`
*   **Doc Manager 모니터링**: `http://localhost:8506`

---

## 3. 사용 워크플로우

### 1단계: 문서 작성 (Input)
Obsidian Vault의 `01_Sources` 폴더에 마크다운 파일을 작성하세요.
*   예: `01_Sources/Idea/NewAppIdea.md`

### 2단계: 자동 처리 (Wait)
약 10~30초 후(모델 성능에 따라 다름), 시스템이 자동으로 다음을 수행합니다:
1.  DB에 원본 저장.
2.  벡터 임베딩 생성.
3.  LLM을 통한 L1 요약 생성.
4.  `99_Shadow_Library/L1/` 폴더에 요약 파일(.md)과 리뷰 파일(.review.md) 생성.

### 3단계: 검토 및 피드백 (Review)
`99_Shadow_Library/L1/` 폴더에 생성된 `[L1] Filename.review.md` 파일을 엽니다.

```yaml
---
review_id: ...
l1_id: ...
rating: PENDING  <-- GOOD, OK, BAD 중 선택
decision: PENDING <-- ACCEPT, REBUILD, DISCARD 중 선택
issues: []
---
```

*   `rating`과 `decision`을 수정하고 저장하면 시스템이 이를 DB에 반영합니다.
*   `decision: REBUILD`로 설정하면 요약을 재생성합니다 (구현 예정).

### 4단계: 인사이트 확인 (L2)
관련된 문서가 쌓이면 시스템이 자동으로 **L2 Insight**를 생성하여 `99_Shadow_Library/L2/` 폴더에 저장합니다.

### ⚠️ 자동화 트리거 (Triggers)
*   **L1 (요약)**: **실시간 자동**. `01_Sources` 폴더의 파일 변경을 감지하는 즉시(1~2초 내) 처리가 시작됩니다.
    *   **L1 방지 (Draft Mode)**: 문서 앞부분(Frontmatter)에 `status: draft` 또는 `draft: true`를 추가하면 요약 생성을 건너뜁니다.
    *   예시:
        ```yaml
        ---
        status: draft
        ---
        ```
*   **L2 (인사이트)**:
    *   **자동 스케줄**: 매일 **새벽 1시**에 시스템이 자동으로 실행되어 새로운 인사이트를 찾습니다.
    *   **수동 트리거**: `http://localhost:8506` 대시보드의 **"L2 Insights"** 탭에서 **[🚀 Run L2 Clustering Job]** 버튼을 눌러 즉시 실행할 수 있습니다.

## 4. 수정 및 삭제 (Modification & Deletion)

### 문서 수정 (Modification)
`01_Sources`에 있는 원본 노트를 수정하고 저장하면, 시스템이 이를 감지하여 자동으로 **새로운 버전(v2, v3...)의 L1 요약**을 생성합니다.
*   기존의 L1 요약은 DB에서 `SUPERSEDED` 상태로 변경됩니다.
*   새로운 `.review.md` 파일이 생성되거나 갱신됩니다.

### 문서 삭제 (Deletion)
*   **원본 삭제**: `01_Sources`에서 파일을 삭제해도, 이미 생성된 지식(L1, L2)은 DB에 기록으로 남습니다. `99_Shadow_Library`에 있는 해당 요약 파일은 직접 삭제해도 무방합니다.
*   **Shadow 파일 삭제**: `99_Shadow_Library`의 파일들은 언제든 삭제해도 안전합니다. 원본이 있다면 시스템이 필요 시 다시 생성하거나, 재생성을 요청할 수 있습니다.

---

## 5. 설정 (Configuration)

### 프롬프트 관리 (Prompt Management)
`90_Configuration/Prompts/` 폴더에서 AI의 응답 방식을 제어할 수 있습니다.

1.  **매핑 설정 (`prompt_config.md`)**:
    *   어떤 카테고리의 문서에 어떤 프롬프트 파일을 사용할지 지정합니다.
    *   파일 속성(Frontmatter)에 `Category: filename.md` 형식으로 직접 설정하세요. (계층 구조 없이 평면적으로 작성)
    *   **계층적 매칭 지원**: 서브폴더 구조를 인식합니다. 예를 들어 `Personal/Study` 폴더에 별도 프롬프트를 지정하면 해당 폴더 내 파일들에 적용됩니다. (매칭 실패 시 상위 폴더 -> default 순으로 자동 폴백)
    *   매핑되지 않은 카테고리는 `default` 설정을 따릅니다.
2.  **프롬프트 수정**:
    *   개별 프롬프트 파일(`prompt.Personal.md` 등)을 수정하면 시스템이 이를 자동으로 감지합니다.
    *   **YAML 속성 구조**: 옵시디언에서 편집하기 쉽도록 속성들이 밖으로 꺼내져 있습니다:
        ```yaml
        ---
        model: "gpt-oss-120b"
        provider: "llama.cpp"
        temperature: 0.3
        ---
        ```
    *   수정 후 저장하면 새로운 프롬프트 버전이 DB에 자동으로 등록됩니다.
3.  **리뷰 연동**:
    *   생성된 `.review.md` 파일 내에 해당 요약에 사용된 프롬프트 파일명이 기록됩니다.

---

## 6. 모니터링

`http://localhost:8506` 대시보드에서 다음을 확인할 수 있습니다:
*   전체 문서 및 요약 통계.
*   원본 문서와 생성된 요약 비교.
*   리뷰 내역 및 처리 상태.
