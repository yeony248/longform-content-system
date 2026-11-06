# 받아쓰기(words.json)와 쓸 구간(project.json의 cuts)으로 롱폼 컷 초안을 캡컷에 새로 만든다.
# 영상: 구간을 이어 붙인 메인 트랙 1줄. 자막: 문장 흐름대로 나눈 자막 1줄(서식은 템플릿 초안에서 복제).
# 실행: python make_cut_draft.py <project.json> [--dry]
#   --dry 이면 초안은 만들지 않고 <작업폴더>/컷초안_자막.txt 만 쓴다(구간·자막 확인용).
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capcut_draft as cd

proj = cd.load_project(sys.argv[1]); DRY = "--dry" in sys.argv
prof = cd.load_profile()
W, H = proj.get("canvas", [1920, 1080])
video = proj.get("masked_video") or proj["source_video"]   # 가림본이 있으면 그걸 쓴다(시각은 원본과 같아야 한다)
words = json.load(open(os.path.join(proj["_dir"], proj.get("words", "받아쓰기/words.json")), encoding="utf-8"))
cuts = [tuple(x) for x in proj["cuts"]]
cap = proj.get("captions", {})
MAXC = cap.get("max_chars", 16)
FIX = [tuple(x) for x in cap.get("fix", [])]            # 받아쓰기 오타 고치기 [["틀린 말", "맞는 말"], ...]
FILLER = set(cap.get("fillers", ["네", "어", "자", "아", "음", "그"]))


def fix(t):
    for a, b in FIX:
        t = t.replace(a, b)
    return t


def chunks(a, b):
    """구간 [a, b] 안의 단어를 자막 덩어리로 묶는다. 시각은 원본 기준."""
    ws = [(max(s, a), min(e, b), w.strip()) for s, e, w, *_ in words if e > a + 0.05 and s < b - 0.05 and w.strip()]
    # 길이 0인 단어가 같은 시각에 줄줄이 붙은 곳은 받아쓰기가 지어낸 반복이다
    ws = [x for i, x in enumerate(ws) if not (x[1] - x[0] < 0.03 and i and abs(x[0] - ws[i - 1][0]) < 0.03)]
    i = 0  # 받아쓰기가 같은 말(2~8단어)을 연달아 두 번 적은 곳을 한 번으로
    while i < len(ws):
        for n in range(8, 1, -1):
            if len(ws[i + n:i + 2 * n]) == n and [x[2] for x in ws[i:i + n]] == [x[2] for x in ws[i + n:i + 2 * n]]:
                del ws[i + n:i + 2 * n]; break
        i += 1
    out, cur = [], []
    for s, e, w in ws:
        txt = " ".join(x[2] for x in cur + [(s, e, w)])
        if cur and (len(txt) > MAXC or s - cur[-1][1] > 0.6 or re.search(r"[.?!]$", cur[-1][2])):
            out.append(cur); cur = []
        cur.append((s, e, w))
    if cur:
        out.append(cur)
    merged = []  # 4글자 이하 꼬리는 앞 자막에 붙인다
    for c in out:
        if merged and len(" ".join(x[2] for x in c)) <= 4 and c[0][0] - merged[-1][-1][1] < 0.6:
            merged[-1] = merged[-1] + c
        else:
            merged.append(c)
    res = []
    for c in merged:
        t = fix(re.sub(r"[.,]", "", " ".join(x[2] for x in c)).strip())
        if t and t.replace("?", "") not in FILLER:
            res.append((c[0][0], c[-1][1], t))
    return res


subs, pos = [], 0.0
for a, b in cuts:
    for s, e, t in chunks(a, b):
        subs.append((pos + s - a, max(e - s, 0.4), t))
    pos += b - a
total = pos
subs.sort()
for i in range(len(subs) - 1):  # 겹치지 않게
    st, du, t = subs[i]
    if st + du > subs[i + 1][0]:
        subs[i] = (st, max(subs[i + 1][0] - st, 0.2), t)

fmt = lambda x: f"{int(x // 60)}:{x % 60:05.2f}"
open(os.path.join(proj["_dir"], "컷초안_자막.txt"), "w", encoding="utf-8").write(
    "\n".join(f"{fmt(st)} ~ {fmt(st + du)} | {t}" for st, du, t in subs))
print(f"길이 {fmt(total)}, 구간 {len(cuts)}개, 자막 {len(subs)}개")
if DRY:
    sys.exit()

tpl_name = proj.get("longform_template_draft") or prof.get("longform_template_draft")
if not tpl_name:
    sys.exit("자막 서식을 가져올 롱폼 템플릿 초안 이름이 없습니다. references/setup.md 3번을 보세요.")
tpl_dir = cd.draft_path(tpl_name, prof)
styles = cd.text_styles(cd.load_draft(tpl_dir))
if not styles:
    sys.exit(f"'{tpl_name}' 초안에 자막(글자) 트랙이 없습니다. 자막 한 줄을 넣고 저장해 주세요.")

import pycapcut as cc
from pycapcut import trange
tmpd, script = cd.new_temp_draft(W, H, fps=prof.get("fps", 30))
script.add_track(cc.TrackType.video, "main")
vm = cc.VideoMaterial(video)
off = 0.0
for a, b in cuts:
    script.add_segment(cc.VideoSegment(vm, trange(f"{off:.3f}s", f"{b - a:.3f}s"),
                                       source_timerange=trange(f"{a:.3f}s", f"{b - a:.3f}s")), "main")
    off += b - a
script.save()
d = cd.read_temp_draft(tmpd)
cd.add_text_track(d, "자막", [cd.text_segment(styles[0], t, st, du) for st, du, t in subs])
d["duration"] = cd.us(total)
name = proj.get("drafts", {}).get("cut") or f"{proj.get('name', '롱폼')}(컷 초안)"
print("저장:", cd.install_draft(d, tpl_dir, name, prof))
