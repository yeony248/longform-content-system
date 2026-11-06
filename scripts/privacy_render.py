# 가림본 만들기: 편집에 쓰는 구간만 가림 상자를 입혀 렌더한다. 나머지 시간은 검은 화면으로 채워
# 원본과 길이·시각이 같다(컷 초안의 시각을 그대로 쓸 수 있다). 소리는 원본 그대로.
# 실행: python privacy_render.py <project.json> [출력.mp4]
# 상자: 가림/boxes.json(privacy_scan.py) + project.json privacy.regions(직접 정한 고정 영역)
#   regions 예: [{"t0": 0, "t1": 1800, "x0": 0, "y0": 80, "x1": 300, "y1": 1000, "why": "사이드바"}]
# 큰 상자(가로·세로 150px 이상)는 블러, 작은 상자는 모자이크(블러 반경이 상자 크기에 묶여 글자가 다시 읽힌다).
import json, os, subprocess, sys, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capcut_draft as cd

proj = cd.load_project(sys.argv[1]); prof = cd.load_profile()
src = proj["source_video"]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + "_가림본.mp4"
boxes = json.load(open(os.path.join(proj["_dir"], "가림", "boxes.json"), encoding="utf-8")) \
    if os.path.exists(os.path.join(proj["_dir"], "가림", "boxes.json")) else []
boxes += proj.get("privacy", {}).get("regions", [])
enc = prof.get("encoder", "libx264")
ENC = ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "19"] if enc == "h264_nvenc" else ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18"]

pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height,r_frame_rate:format=duration", "-of", "json", src],
                               capture_output=True, text=True, check=True).stdout)
W, H = pr["streams"][0]["width"], pr["streams"][0]["height"]
n, dnm = pr["streams"][0]["r_frame_rate"].split("/"); FPS = int(n) / int(dnm)
DUR = float(pr["format"]["duration"])
snap = lambda t: round(round(t * FPS) / FPS, 6)   # 조각 경계를 프레임에 맞춘다

used = []
for a, b in sorted((max(0, a - 1), min(DUR, b + 1)) for a, b in proj["cuts"]):
    if used and a <= used[-1][1]:
        used[-1] = (used[-1][0], max(used[-1][1], b))
    else:
        used.append((a, b))
pieces, t = [], 0.0   # (시작, 끝, 가림 렌더 여부)
for a, b in used:
    if a > t:
        pieces.append((t, a, False))
    x = a
    while x < b:
        pieces.append((x, min(b, x + 8), True)); x += 8
    t = b
if t < DUR:
    pieces.append((t, DUR, False))
pieces = [(snap(a), snap(b), u) for a, b, u in pieces if snap(b) > snap(a)]


def chain(a, b):
    act = [x for x in boxes if x["t1"] > a and x["t0"] < b]
    if not act:
        return None
    fc, last = [], "[0:v]"
    for i, x in enumerate(act):
        x0, y0 = max(0, int(x["x0"])), max(0, int(x["y0"]))
        w, h = min(W, int(x["x1"])) - x0, min(H, int(x["y1"])) - y0
        if w < 4 or h < 4:
            continue
        if w >= 150 and h >= 150:
            eff = f"boxblur={min(20, min(w, h) // 2 - 1)}:2"
        else:
            eff = f"scale={max(1, w // 12)}:{max(1, h // 12)},scale={w}:{h}:flags=neighbor"
        fc.append(f"{last}split[m{i}][c{i}];[c{i}]crop={w}:{h}:{x0}:{y0},{eff}[b{i}];"
                  f"[m{i}][b{i}]overlay={x0}:{y0}:enable='between(t,{max(0, x['t0'] - a):.3f},{x['t1'] - a:.3f})'[v{i}]")
        last = f"[v{i}]"
    return (";".join(fc), last) if fc else None


tmp = tempfile.mkdtemp(); lst = []
for k, (a, b, u) in enumerate(pieces):
    p = os.path.join(tmp, f"p{k:05d}.mp4"); dur = b - a
    common = ["-t", f"{dur:.6f}", "-r", f"{FPS}", "-s", f"{W}x{H}", "-pix_fmt", "yuv420p", *ENC, "-an", p]
    if not u:
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={FPS}", *common]
    else:
        c = chain(a, b)
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.6f}", "-t", f"{dur:.6f}", "-i", src]
        if c:
            cmd += ["-filter_complex", c[0], "-map", c[1]]
        cmd += common
    subprocess.run(cmd, check=True)
    lst.append("file '" + p.replace("\\", "/") + "'\n")
    print(f"\r조각 {k + 1}/{len(pieces)}", end="", flush=True)
open(os.path.join(tmp, "list.txt"), "w", encoding="utf-8").write("".join(lst))
vid = os.path.join(tmp, "v.mp4")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "list.txt"), "-c", "copy", vid], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vid, "-i", src, "-map", "0:v", "-map", "1:a?", "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k", "-shortest", out], check=True)
shutil.rmtree(tmp, ignore_errors=True)
print(f"\n가림본: {out}\n다음: python privacy_scan.py <project.json> --check \"{out}\" 로 남은 글자가 0건인지 확인")
