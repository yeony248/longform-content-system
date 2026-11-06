# 녹화 영상을 단어 시각까지 받아쓴다 (faster-whisper).
# 실행: python transcribe.py <영상> <출력폴더> [--start 초] [--end 초] [--model large-v3] [--lang ko]
# 결과: <출력폴더>/words.json  [[시작, 끝, 단어, 확신도], ...] (원본 영상 기준 초)
#       <출력폴더>/transcript.txt  문장 단위, "분:초 ~ 분:초 | 문장"  ← 이걸 읽고 쓸 구간을 고른다
import argparse, json, os, subprocess, sys, tempfile
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("out")
ap.add_argument("--start", type=float, default=0.0); ap.add_argument("--end", type=float, default=None)
ap.add_argument("--model", default="large-v3"); ap.add_argument("--lang", default="ko")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

wav = os.path.join(tempfile.mkdtemp(), "voice.wav")
cmd = ["ffmpeg", "-v", "error", "-y", "-ss", str(a.start)]
if a.end:
    cmd += ["-t", str(a.end - a.start)]
subprocess.run(cmd + ["-i", a.video, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)

from faster_whisper import WhisperModel
try:
    m = WhisperModel(a.model, device="cuda", compute_type="float16")
except Exception:
    print("GPU를 쓸 수 없어 CPU로 받아씁니다. 1시간 영상은 수십 분 걸릴 수 있어요.")
    m = WhisperModel(a.model, device="cpu", compute_type="int8")
segs, _ = m.transcribe(wav, language=a.lang, word_timestamps=True, vad_filter=True, condition_on_previous_text=False)

fmt = lambda x: f"{int(x // 60)}:{x % 60:05.2f}"
words, lines = [], []
for s in segs:
    ws = [(round(w.start + a.start, 2), round(w.end + a.start, 2), w.word.strip(), round(w.probability, 2))
          for w in (s.words or []) if w.word.strip()]
    words += ws
    if ws:
        lines.append(f"{fmt(ws[0][0])} ~ {fmt(ws[-1][1])} | {s.text.strip()}")
json.dump(words, open(os.path.join(a.out, "words.json"), "w", encoding="utf-8"), ensure_ascii=False)
open(os.path.join(a.out, "transcript.txt"), "w", encoding="utf-8").write("\n".join(lines))
print(f"단어 {len(words)}개, 문장 {len(lines)}개 → {a.out}")
