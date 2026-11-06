# 검수: 캡컷 초안 타임라인에서 목소리만 뽑아 다시 받아쓰고, 컷 지점·반복·군말·긴 쉼 목록을 만든다.
# 실행: python qa_voice.py "<초안 이름>" <작업폴더>
#   → <작업폴더>/검수/목소리.wav, 받아쓰기.json, 검수목록.txt
# 목소리로 보는 것: 메인 영상 트랙(첫 번째 영상 트랙)의 소리 + 이름이 "voice"인 오디오 트랙. 소리 없는 소재는 건너뛴다.
import json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capcut_draft as cd

name, work = sys.argv[1], sys.argv[2]
OUT = os.path.join(work, "검수"); os.makedirs(OUT, exist_ok=True)
d = cd.load_draft(cd.draft_path(name))
mats = {k: m for k, (_, m) in cd.material_index(d).items()}
_aud = {}


def has_audio(p):
    if p not in _aud:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", p],
                           capture_output=True, text=True)
        _aud[p] = bool(r.stdout.strip())
    return _aud[p]


vids = [t for t in d["tracks"] if t["type"] == "video"]
use = ([vids[0]] if vids else []) + [t for t in d["tracks"] if t["type"] == "audio" and t.get("name") == "voice"]
segs = []
for t in use:
    for g in t["segments"]:
        p = mats[g["material_id"]].get("path", "")
        if p and os.path.exists(p) and has_audio(p) and g.get("volume", 1.0) > 0:
            segs.append((g["target_timerange"]["start"] / cd.US, g["target_timerange"]["duration"] / cd.US,
                         g["source_timerange"]["start"] / cd.US, p))
segs.sort()
if not segs:
    sys.exit("목소리가 들어 있는 조각을 찾지 못했습니다.")
total = d["duration"] / cd.US
ins, af = [], []
for k, (a, du, ss, p) in enumerate(segs):
    ins += ["-ss", f"{ss:.3f}", "-t", f"{du:.3f}", "-i", p]
    af.append(f"[{k}:a]aresample=16000,adelay={int(a * 1000)}:all=1[a{k}]")
af.append("".join(f"[a{k}]" for k in range(len(segs))) + f"amix=inputs={len(segs)}:normalize=0:duration=longest,atrim=0:{total:.3f}[o]")
fc = os.path.join(OUT, "fc.txt"); open(fc, "w", encoding="utf-8").write(";".join(af))
wav = os.path.join(OUT, "목소리.wav")
subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex_script", fc, "-map", "[o]", "-ac", "1", wav], check=True)

from faster_whisper import WhisperModel
try:
    m = WhisperModel("large-v3", device="cuda", compute_type="float16")
except Exception:
    m = WhisperModel("large-v3", device="cpu", compute_type="int8")
res, _ = m.transcribe(wav, language="ko", word_timestamps=True, vad_filter=False, condition_on_previous_text=False)
words = [(round(w.start, 2), round(w.end, 2), w.word.strip(), round(w.probability, 2)) for s in res for w in s.words if w.word.strip()]
json.dump({"cuts": [round(a, 2) for a, *_ in segs], "words": words}, open(os.path.join(OUT, "받아쓰기.json"), "w", encoding="utf-8"), ensure_ascii=False)

fmt = lambda x: f"{int(x // 60)}:{x % 60:05.2f}"
FILL = {"어", "음", "아", "자", "그", "이제", "막", "뭐", "그니까", "약간", "좀", "네"}
lines = ["[컷 앞뒤 2초]  [단어]=받아쓰기 확신이 낮은 곳(잘렸거나 새는 말일 수 있음), |=컷 위치"]
for a, du, ss, p in segs:
    if a < 0.5:
        continue
    ctx = [w for w in words if a - 2.0 <= w[0] <= a + 2.0]
    txt = " ".join((f"[{w[2]}]" if w[3] < 0.5 else w[2]) + ("|" if w[1] <= a < (ctx[i + 1][0] if i + 1 < len(ctx) else 1e9) else "")
                   for i, w in enumerate(ctx))
    lines.append(f"컷 {fmt(a)}  {txt}")
lines.append("\n[반복]")
for i in range(len(words) - 1):
    for n in (1, 2, 3):
        x = [w[2] for w in words[i:i + n]]; y = [w[2] for w in words[i + n:i + 2 * n]]
        if len(y) == n and x == y and len("".join(x)) >= 2:
            lines.append(f"{fmt(words[i][0])}  {' '.join(x)} / {' '.join(y)}"); break
lines.append("\n[군말]")
for w in words:
    if re.sub(r"[.,?!]", "", w[2]) in FILL and w[1] - w[0] > 0.25:
        lines.append(f"{fmt(w[0])}  {w[2]} ({w[1] - w[0]:.2f}s)")
lines.append("\n[1.2초 넘는 쉼]")
for i in range(len(words) - 1):
    g = words[i + 1][0] - words[i][1]
    if g > 1.2:
        lines.append(f"{fmt(words[i][1])}  {g:.1f}초  ({words[i][2]} → {words[i + 1][2]})")
open(os.path.join(OUT, "검수목록.txt"), "w", encoding="utf-8").write("\n".join(lines))
print(f"단어 {len(words)}개, 컷 {len(segs)}개 → {OUT}")
