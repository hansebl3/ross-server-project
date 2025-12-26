# CSV & DB Time Series Analyzer

리눅스 서버에서 도커(Docker) 컨테이너로 실행되는 웹 애플리케이션입니다.
CSV 파일 또는 MariaDB 데이터베이스에서 시계열 데이터를 로드하여 분석하고 시각화합니다.

## 주요 기능 (Key Features)

### 1. 일반 분석 모드 (General Analysis)
*   **데이터 소스:**
    *   **CSV 파일:** 로컬 PC의 CSV 파일을 업로드하여 분석.
    *   **MariaDB:** 데이터베이스에 접속하여 특정 테이블의 데이터를 날짜 범위로 조회.
*   **데이터 전처리:**
    *   시간 컬럼 자동 감지 및 파싱.
    *   고급 필터링 (컬럼, 연산자, 값) 기능 제공.
*   **시각화:**
    *   **전체 시계열 개요:** 전체 데이터의 흐름을 한눈에 파악.
    *   **시간 범위 선택:** 슬라이더를 통해 관심 구간을 정밀하게 선택.
    *   **트렌드 그래프 & 히스토그램:** 선택된 구간의 데이터 추이와 분포 확인.
    *   **커스터마이징:** X축, Y축 레이블 사용자 정의 가능.
*   **데이터 내보내기:** 필터링된 데이터를 CSV 파일로 다운로드.

### 2. 자동 검증 모드 (Auto Validation)
*   **목적:** PLC 데이터와 Vision 데이터를 비교 분석하여 공정 이상 유무를 검증.
*   **데이터 소스:**
    *   **Database:** MariaDB에서 PLC(`tb_unit_data`) 및 Vision(`tb_result`) 데이터 로드.
    *   **CSV Files:** PLC 및 Vision 데이터 CSV 파일을 직접 업로드하여 분석.
*   **워크플로우:**
    1.  **데이터 로드:** 날짜 범위를 지정하여 데이터 로드.
    2.  **Step 1 (PLC 필터링):** Unit 1~4 순차적으로 진행.
        *   시간 범위 및 압력(D5017) 임계값 설정.
        *   실시간 그래프 프리뷰 제공.
    3.  **Step 2 & 3 (시각화):**
        *   **3x3 그리드 분석:** 각 Unit 별로 8개의 그래프(온도, 압력, RPM 트렌드/히스토그램, Vision 데이터 히스토그램)를 한 화면에 표시.
        *   **번들 이미지 저장:** Plotly 모드바를 통해 전체 그리드를 하나의 이미지로 저장 가능.
*   **편의 기능:**
    *   그래프 타이틀 및 UI 텍스트 "Unit"으로 통일.
    *   설정값(필터 범위 등) 자동 저장 및 재사용.
    *   CSV 데이터 내보내기 (Unit 별).

## 시스템 구조 (Refactoring)
코드는 유지보수성을 위해 모듈화되어 있습니다.
*   `app.py`: 메인 애플리케이션 진입점 및 네비게이션.
*   `modes/`:
    *   `general_analysis.py`: 일반 분석 모드 로직.
    *   `auto_validation.py`: 자동 검증 모드 로직.
*   `config_manager.py`: 설정 파일(`db_config.json`) 관리.
*   `data_loader.py`: CSV 및 DB 데이터 로딩 유틸리티.
*   `visualizer.py`: Plotly 차트 생성 유틸리티.

## Docker 실행 방법

### 1. 이미지 빌드
```bash
docker build -t csv-analyzer .
```

### 2. 컨테이너 실행
DB 설정(`db_config.json`)을 호스트와 공유하여 설정을 유지하려면 아래 명령어로 실행하세요.
```bash
docker run -d \
  --network host \
  -v $(pwd)/db_config.json:/app/db_config.json \
  --name csv-analyzer-app \
  csv-analyzer
```

### 3. 접속
브라우저에서 [http://localhost:8501](http://localhost:8501) 로 접속하세요.
