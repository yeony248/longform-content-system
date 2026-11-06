# 환경 점검: 이 스킬에 필요한 프로그램과 설정이 있는지 한 번에 본다.
# 실행: python check_env.py
import importlib.util, json, os, platform, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capcut_draft as cd

ok = lambda b: "있음" if b else "없음"
print("운영체제:", platform.system(), platform.release())
v = sys.version_info
print(f"Python: {v.major}.{v.minor}.{v.micro}" + ("" if (3, 10) <= (v.major, v.minor) <= (3, 12)
      else "  → 권장 3.11~3.12. 다른 버전은 faster-whisper 부품을 직접 빌드하느라 설치가 아주 오래 걸리거나 실패할 수 있다"))
for exe in ("ffmpeg", "ffprobe"):
    print(f"{exe}: {ok(shutil.which(exe))}")
for mod, pipn in (("faster_whisper", "faster-whisper"), ("pycapcut", "pycapcut")):
    print(f"{mod}: {ok(importlib.util.find_spec(mod))}" + ("" if importlib.util.find_spec(mod) else f"  → pip install {pipn}"))
g = cd.gpu_count() > 0
print("GPU 받아쓰기(CUDA):", ok(g), "" if g else "(CPU로 동작, 기본 모델 small)")
print("받아쓰기 모델:", p_model := (cd.load_profile().get("whisper_model") or ("large-v3" if g else "small")),
      "(처음 받아쓸 때 내려받음: large-v3 약 3GB, medium 약 1.5GB, small 약 0.5GB)")
if shutil.which("ffmpeg"):
    encs = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    print("h264_nvenc(엔비디아 인코더):", ok("h264_nvenc" in encs))
print("Windows OCR(가림 검사):", ok(platform.system() == "Windows"), "(macOS는 가림 상자를 직접 정해야 한다)")
d = cd.drafts_dir()
print("캡컷 초안 폴더:", d, ok(os.path.isdir(d)))
p = cd.load_profile()
print("개인 설정:", cd.PROFILE_PATH, ok(bool(p)))
for k in ("longform_template_draft", "shorts_template_draft"):
    v = p.get(k)
    print(f"  {k}: {v or '(설정 안 됨)'}" + (f"  {ok(os.path.isdir(cd.draft_path(v, p)))}" if v else ""))
for k, v in p.get("sfx", {}).items():
    print(f"  효과음 {k}: {ok(os.path.exists(v))}  {v}")
