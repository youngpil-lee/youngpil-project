# 테스트 실행 가이드

## 1. 개요
본 프로젝트는 **Python 3.11 또는 3.12** 환경에서 최적화되어 있습니다.
현재 시스템에 설치된 **Python 3.14 (Preview)** 버전에서는 `numpy`, `pykrx` 등 핵심 라이브러리가 아직 지원되지 않아 실제 데이터 수집이 불가능할 수 있습니다.

이에 따라, 핵심 로직의 정상 작동을 검증하기 위해 **Mock(모의 데이터) 테스트**를 수행하였습니다.

## 2. 테스트 결과
`test_mock.py` 실행 결과, 다음 기능이 정상 작동함을 확인하였습니다.

1.  **스크리너 (Screener)**
    *   상승률 상위 종목 수집 로직 (Mock 데이터)
    *   수급 데이터 결합 로직
    *   DataFrame 생성 및 필터링
2.  **시그널 생성 (Signal Generator)**
    *   VCP 패턴 감지 알고리즘 (변동성 축소 확인)
    *   점수 산출 (Scorer): 수급 + 차트 + 뉴스 점수 합산
    *   자금 관리 (Position Sizing): 진입가, 손절가, 수량 계산
3.  **결과물**
    *   삼성전자, SK하이닉스 등 테스트 종목에 대해 `OPEN` 시그널 생성 확인
    *   점수: 85점 (S급 시그널)

## 3. 실행 방법
### Mock 테스트 (로직 검증용)
```bash
py test_mock.py
```

### 실제 실행 (Python 3.11/3.12 필요)
```bash
python run.py
```
*   1번 메뉴: 수급 스크리닝
*   2번 메뉴: VCP 시그널 생성

## 4. 문제 해결
`ImportError: No module named 'pykrx'` 또는 `numpy` 설치 오류 발생 시:
*   Python 버전을 3.11로 다운그레이드하거나 가상환경(venv/conda)을 사용하세요.
*   `pip install pandas pykrx google-generativeai python-dotenv schedule` 재설치
