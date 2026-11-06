# 편집에 쓰는 구간만 프레임을 뽑아 OCR(Windows 한국어 OCR)로 읽고, 가릴 글자 상자를 찾는다.
# 실행: python privacy_scan.py <project.json>            → <작업폴더>/가림/boxes.json, ocr_all.tsv
#       python privacy_scan.py <project.json> --check <가림본.mp4>  → 가림/check.txt (남은 글자 검사)
# 찾는 것: project.json privacy.words(업체명·사람 이름 등 직접 적은 말), 전화번호, 이메일, 카카오 채널 주소,
#         privacy.regex(직접 적은 정규식). ocr_all.tsv를 Claude가 읽어 목록에 없는 이름을 더 찾는다.
import json, os, re, subprocess, sys, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capcut_draft as cd

HERE = os.path.dirname(os.path.abspath(__file__))
proj = cd.load_project(sys.argv[1])
CHECK = "--check" in sys.argv
video = sys.argv[sys.argv.index("--check") + 1] if CHECK else proj["source_video"]
pv = proj.get("privacy", {})
STEP = pv.get("step", 0.25 if CHECK else 0.5)   # 검사는 1초 4장
OUT = os.path.join(proj["_dir"], "가림"); os.makedirs(OUT, exist_ok=True)
WORDS = [w.replace(" ", "") for w in pv.get("words", []) if w.strip()]
PATTERNS = [r"0\d{1,2}[-.)]?\d{3,4}[-.]?\d{4}", r"[\w.+-]+@[\w-]+\.[\w.]+", r"(open|pf)\.kakao\.com\S*"] + pv.get("regex", [])


def ranges():
    rs = sorted((max(0, a - 1), b + 1) for a, b in proj["cuts"])
    out = []
    for a, b in rs:
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


tmp = tempfile.mkdtemp()
times = {}
for k, (a, b) in enumerate(ranges()):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", video,
                    "-vf", f"fps=1/{STEP}", os.path.join(tmp, f"r{k:03d}_%06d.png")], check=True)
    for f in os.listdir(tmp):
        if f.startswith(f"r{k:03d}_") and f not in times:
            times[f] = round(a + (int(f[5:11]) - 1) * STEP, 2)
tsv = os.path.join(tmp, "ocr.tsv")
subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                os.path.join(HERE, "ocr_windows.ps1"), "-Dir", tmp, "-Out", tsv], check=True)
rows = []
for line in open(tsv, encoding="utf-8"):
    p = line.rstrip("\n").split("\t")
    if len(p) >= 6:
        rows.append((times[p[0]], int(p[1]), int(p[2]), int(p[3]), int(p[4]), "\t".join(p[5:])))
shutil.rmtree(tmp, ignore_errors=True)
rows.sort()
with open(os.path.join(OUT, "ocr_check.tsv" if CHECK else "ocr_all.tsv"), "w", encoding="utf-8") as f:
    f.write("시각\tx1\ty1\tx2\ty2\t글자\n")
    for r in rows:
        f.write("\t".join(map(str, r)) + "\n")


def hits(text):
    """줄 안에서 가릴 부분의 (시작 글자, 끝 글자, 이유). OCR은 단어를 붙여 내므로 공백 없이 비교한다."""
    t = text.replace(" ", "")
    out = []
    for w in WORDS:
        for m in re.finditer(re.escape(w), t):
            out.append((m.start(), m.end(), w))
    for p in PATTERNS:
        for m in re.finditer(p, t):
            out.append((m.start(), m.end(), "패턴"))
    return t, out


found = []
for tm, x1, y1, x2, y2, text in rows:
    t, hs = hits(text)
    for s, e, why in hs:
        cw = (x2 - x1) / max(1, len(t))   # 줄 상자를 글자 위치 비율로 잘라 단어 상자를 만든다
        # 글자 폭이 고르지 않아 비율 계산이 어긋나므로 양옆에 글자 한 칸씩 여유를 둔다
        found.append(dict(t=tm, x0=max(x1, int(x1 + cw * (s - 1))) - 6, y0=y1 - 6,
                          x1=min(x2, int(x1 + cw * (e + 1))) + 6, y1=y2 + 6, why=why, text=t[s:e]))

if CHECK:
    with open(os.path.join(OUT, "check.txt"), "w", encoding="utf-8") as f:
        f.write(f"남은 글자 {len(found)}건 (프레임 간격 {STEP}초)\n")
        for h in found:
            f.write(f"{h['t']:.2f}s  {h['text']}  ({h['x0']},{h['y0']})-({h['x1']},{h['y1']})\n")
    print(f"남은 글자 {len(found)}건 → 가림/check.txt")
    sys.exit()


def same(a, b):
    ix = max(0, min(a["x1"], b["x1"]) - max(a["x0"], b["x0"])); iy = max(0, min(a["y1"], b["y1"]) - max(a["y0"], b["y0"]))
    inter = ix * iy
    ua = (a["x1"] - a["x0"]) * (a["y1"] - a["y0"]) + (b["x1"] - b["x0"]) * (b["y1"] - b["y0"]) - inter
    return ua > 0 and inter / ua > 0.4


boxes = []  # 같은 자리에 이어서 나오는 상자는 한 상자로 묶고 앞뒤 여유를 둔다
for h in sorted(found, key=lambda x: x["t"]):
    for b in boxes:
        if same(b, h) and h["t"] - b["t1"] <= STEP * 1.5 + 0.01:
            b["t1"] = h["t"]
            for k, f in (("x0", min), ("y0", min), ("x1", max), ("y1", max)):
                b[k] = f(b[k], h[k])
            break
    else:
        boxes.append(dict(t0=h["t"], t1=h["t"], x0=h["x0"], y0=h["y0"], x1=h["x1"], y1=h["y1"], why=h["why"], text=h["text"]))
pad = STEP / 2 + 0.3
for b in boxes:
    b["t0"] = round(max(0, b["t0"] - pad), 2); b["t1"] = round(b["t1"] + pad, 2)
json.dump(boxes, open(os.path.join(OUT, "boxes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"OCR 줄 {len(rows)}개, 가릴 상자 {len(boxes)}개 → 가림/boxes.json")
print("ocr_all.tsv 를 읽고 목록에 없는 이름·업체명이 보이면 privacy.words 에 더해 다시 돌린다.")
