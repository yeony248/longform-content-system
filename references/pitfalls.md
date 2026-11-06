# 자주 걸리는 함정

## 캡컷 초안
- 캡컷이 연 초안 폴더를 지우거나 덮어쓰면 사용자 편집이 사라진다. 새 이름으로만 만든다.
- 캡컷은 `Timelines/<main_timeline_id>/draft_content.json`을 실제로 연다. 루트 `draft_content.json`과 둘 다 쓴다. 목록 등록은 `root_meta_info.json`(백업 후 수정), `draft_meta_info.json`, `Timelines/project.json`, `timeline_layout.json`. `capcut_draft.install_draft()`가 이걸 한다.
- 캡컷이 켜져 있는 동안 새 초안을 넣으면 목록에 바로 안 보일 수 있다. 캡컷을 다시 켠다.
- 시간 단위는 마이크로초. 조각을 자를 때 `source_timerange.start += 자른 앞부분 × 속도`.
- 조각을 복사할 때 `extra_material_refs`(속도·애니메이션 등)도 새 id로 복사해 붙인다.
- 새 영상·소리 트랙은 pycapcut 임시 초안에서 만들어 옮겨야 형식이 맞는다. 글자는 사용자 초안에서 복제한다.
- 메인 트랙에 빈칸이 생기면 캡컷이 뒤 조각을 당겨 다른 트랙과 어긋난다. 끼워 넣기·지우기는 메인 트랙 안에서.
- 사용자가 캡컷에서 열어 둔 영상 파일을 덮어쓰지 않는다. 다시 렌더한 결과는 새 이름(clips_v2, clips_v3 …)으로 만들고 초안의 경로만 바꾼다.
- 사용자가 초안을 고치며 시작점을 옮기는 경우가 있다. 되돌리지 말고 "의도한 것인지" 묻는다.

## ffmpeg
- `-loop 1` 이미지 입력은 `-t`로 길이를 정하지 않으면 끝나지 않는다(파일이 수 GB까지 커진다).
- 입력이 수백 개면 Windows 명령줄 길이 한도(WinError 206)를 넘는다. 같은 파일은 한 번만 넣고 `asplit`, 필터는 `-filter_complex_script` 파일로.
- overlay 필터는 `enable`이 꺼진 시간에도 매 프레임 계산된다. 상자가 많으면 몇 초 단위 조각으로 나눠 그 조각에 걸린 상자만 넣는다(`privacy_render.py` 방식).
- 소리 없는 클립(요약 카드 등)을 오디오 필터에 넣으면 "Stream specifier ':a'" 오류가 난다. ffprobe로 소리가 있는 것만 넣는다.

## 받아쓰기·OCR
- Whisper는 같은 말을 두 번 적거나, 길이 0인 단어를 줄줄이 지어낼 때가 있다. `make_cut_draft.py`가 걸러 낸다.
- 도구 이름·외래어 오타는 `captions.fix`로 고친다. 프로젝트마다 쌓아 두면 다음에 다시 쓴다.
- Windows PowerShell 5.1은 스크립트 속 한글을 깨뜨린다. OCR 스크립트에는 한글을 넣지 않고 결과 거르기는 Python에서 한다.
- OCR은 단어를 붙여서 낸다("홍길동카페"). 공백 없이 비교한다.

## 기타
- Python 한글 출력이 깨지면 결과를 파일로 쓴다.
- bash 히어독 안 Python 문자열에 Windows 경로(`\U…`)나 따옴표가 섞이면 깨진다. 패치 코드는 파일로 써서 실행한다.
- 파일 이름이 NFD(맥에서 만든 한글 파일)면 경로 비교가 실패한다. `glob`으로 찾는다.
- HyperFrames: `.clip` 요소에 CSS transform과 GSAP 트윈을 같이 쓰지 않는다. 강조색 바탕 위 흰 글자는 대비 검사에서 떨어지기 쉽다.
- 목소리 복제(마지막 인사 등)를 쓴다면 강의 녹화 몇 초보다 깨끗한 말소리 30초 정도로 학습한 쪽이 억양이 자연스러웠다. 본인 목소리이고 본인이 동의한 경우만.
