# Vercel 배포 마무리 가이드

Vercel 배포를 위한 모든 설정 파일이 성공적으로 생성되었습니다. 현재 환경 제약으로 인해 자동 배포가 중단되었으나, 아래 단계를 통해 직접 배포를 마무리하실 수 있습니다.

## 1. 생성된 파일 확인
- `vercel.json`: 라우팅 및 빌드 설정
- `requirements.txt`: Python 의존성 목록
- `api/index.py`: 서버리스 엔트리 포인트

## 2. 배포 실행 방법
터미널에서 다음 명령어를 실행해 주세요:
```powershell
npx vercel --yes
```
*처음 실행하시는 경우 Vercel 로그인이 필요할 수 있습니다.*

## 3. 환경 변수 설정 (중요)
배포 후 Vercel Project Settings에서 다음 변수를 추가해야 정상 작동합니다:
- `GOOGLE_API_KEY`: Gemini API 키
- `GEMINI_MODEL`: `gemini-flash-latest`

## 4. 접속 확인
배포가 완료되면 Vercel에서 제공하는 URL([https://projectName.vercel.app](https://projectName.vercel.app))로 접속하여 대시보드를 확인하세요.
