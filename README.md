# longform-content-system 설치 안내

버전: v2 (2026-11-06) · 바뀐 점은 맨 아래 "버전 기록"

강의·줌 녹화 한 편으로 유튜브 롱폼, 세로 숏폼 2~3개, 블로그 초안을 만드는 Claude Code 스킬입니다.
편집 결과는 캡컷 PC 초안으로 받고, 다듬기·내보내기·게시는 직접 합니다.

## 필요한 것
- Windows 10/11 + 캡컷 PC (macOS는 글자 자동 가림(OCR)을 쓸 수 없고 나머지는 됩니다)
- Claude Code
- Python 3.11 또는 3.12 (권장). 3.13 이상이나 3.9 이하는 받아쓰기 부품을 직접 빌드하느라 설치가 아주 오래 걸리거나 실패할 수 있습니다.
- ffmpeg (명령창에서 `ffmpeg -version`이 나와야 합니다)
- 엔비디아 그래픽카드가 있으면 받아쓰기·렌더가 빨라집니다. 없으면 자동으로 작은 받아쓰기 모델(small)을 씁니다.

## 설치
1. 이 폴더를 통째로 `%USERPROFILE%\.claude\skills\longform-content-system` 에 넣습니다.
   GitHub에서 받을 때는 Releases의 zip을 받아 풀거나, 아래 명령을 씁니다.
   ```
   git clone https://github.com/yeony248/longform-content-system "%USERPROFILE%\.claude\skills\longform-content-system"
   ```
2. 명령창에서:
   ```
   pip install faster-whisper pycapcut
   ```
3. 캡컷에서 템플릿 초안 두 개를 만들어 둡니다.
   1. 롱폼 템플릿: 16:9 새 프로젝트에 평소 자막 서식으로 자막 한 줄을 넣고 저장
   2. 숏폼 템플릿: 9:16 프로젝트에 첫 번째 글자 트랙은 훅(위쪽 큰 문구), 두 번째 글자 트랙은 자막 서식으로 한 줄씩 넣고 저장
4. 점검: `python %USERPROFILE%\.claude\skills\longform-content-system\scripts\check_env.py` 로 빠진 것이 없는지 봅니다.
5. Claude Code에서 "콘텐츠 시스템 설정해줘"라고 하면 채널 이름, 링크, 색, 글꼴, 효과음, 템플릿 초안 이름을 묻고 `%USERPROFILE%\.content-system\profile.json`을 만듭니다.

## 걸리는 시간 (대략)

| 단계 | 시간 | 비고 |
|---|---|---|
| 스킬 폴더 넣기 | 몇 초 | |
| `pip install` | 1~5분 | 권장 Python 버전일 때 |
| Python·ffmpeg 새로 설치 | 10~20분 | 없는 PC만 |
| 템플릿 초안 두 개 만들기 | 10분 | 캡컷에서 직접 |
| 설정 인터뷰 | 10~15분 | 질문에 답하는 만큼 |
| 첫 받아쓰기 때 모델 내려받기 | 몇 분~30분 | 한 번만. large-v3 약 3GB, medium 약 1.5GB, small 약 0.5GB |

설치가 20분 넘게 같은 화면이면 아래 "설치가 오래 걸릴 때"를 봅니다.

## 설치가 오래 걸릴 때
1. 화면 마지막 줄을 봅니다.
   - `Building wheel for av` 또는 `ctranslate2` 같은 줄에서 멈춰 있으면, 미리 만들어진 설치 파일이 없는 Python 버전이라 직접 빌드하는 중입니다. Ctrl+C로 멈추고 Python 3.12를 설치한 뒤 `py -3.12 -m pip install faster-whisper pycapcut`로 다시 설치합니다.
   - `Downloading` 이나 모델 이름(large-v3)이 보이면 모델을 내려받는 중입니다. 인터넷이 느리면 오래 걸립니다. 기다리거나, 더 작은 모델을 씁니다(아래).
   - `nvidia-cudnn`, `nvidia-cublas` 같은 큰 파일을 받고 있으면 그래픽카드용 부품입니다. 그래픽카드가 없으면 받을 필요가 없습니다.
2. 더 작은 모델 쓰기: `%USERPROFILE%\.content-system\profile.json`에 `"whisper_model": "medium"` 또는 `"small"`을 넣습니다. 작을수록 빠르지만 받아쓰기 정확도가 낮아집니다.
3. `python --version`과 화면 마지막 몇 줄을 Claude에게 붙여 주면 원인을 찾아 줍니다.

## 쓰는 법
- "이 줌 녹화로 유튜브 롱폼 만들자" → 받아쓰기, 구간 제안, 컷 초안부터 시작
- "롱폼에서 숏폼 뽑아줘" → 후보 표 → 확인 후 숏폼 캡컷 초안
- "블로그 초안도" → 블로그 글 초안과 캡처

## 들어 있지 않은 것
- 효과음, 배경음악, 글꼴, 배경 이미지 같은 파일은 들어 있지 않습니다. 각자 가진 파일 경로를 설정에 적습니다.
- 업로드와 게시는 요청할 때만, 비공개까지만 합니다. 게시 버튼은 직접 누릅니다.

## 주의
- 스크립트는 같은 이름의 캡컷 초안이 있으면 덮어쓰지 않고 멈춥니다. 그래도 처음 쓸 때는 캡컷 초안 폴더를 한 번 백업해 두기를 권합니다.
- 캡컷 업데이트로 초안 파일 형식이 바뀌면 스크립트가 맞지 않을 수 있습니다.

## 라이선스
MIT 라이선스입니다. 자유롭게 쓰고 고치고 나눠도 되며, LICENSE 파일의 저작권 표시를 함께 남겨 주세요.

## 버전 기록
- v2: 받아쓰기 모델을 고를 수 있게 함(그래픽카드가 없으면 small 자동), 환경 점검에 Python 버전·모델 크기 표시, 설치 시간표와 "설치가 오래 걸릴 때" 안내 추가, MIT 라이선스 포함
- v1: 첫 배포
