# 내보낸 롱폼 mp4에서 세로 숏폼(9:16) 캡컷 초안을 만든다. 글자 서식은 사용자 본인의 숏폼 템플릿 초안에서 복제한다.
# 구성: 위 훅 문구(영상 내내) + 가운데 16:9 원본 + 원본 아래 자막 + 끝 몇 초 "풀영상" 안내 + 효과음(있으면)
# 실행: python make_shorts_capcut.py <project.json> [번호...]   (번호를 안 주면 전부. 같은 이름 초안이 있으면 멈춘다)
#
# project.json 의 "shorts":
#   source        내보낸 롱폼 mp4 (조각 시각은 이 파일 기준 = 롱폼 최종 초안 타임라인 기준)
#   captions_from 자막 글자를 가져올 롱폼 최종 초안 이름 (없으면 자막 없이 만든다)
#   crop          롱폼에 구운 자막 띠를 잘라 낼 때 "가로:세로:x:y" (예 "1920:900:0:0"). 없으면 자르지 않는다
#   end_text      끝 안내 문구. items: [{name, hook, pieces: [[시작, 끝], ...]}]
# profile.json: shorts_template_draft(필수), shorts_layout, sfx.whoosh / sfx.ding (선택)
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capcut_draft as cd

proj = cd.load_project(sys.argv[1]); prof = cd.load_profile()
S = proj["shorts"]; L = {**dict(caption_y=-0.34, caption_scale=0.92, end_y=-0.52, end_scale=0.5, end_seconds=3.0),
                         **prof.get("shorts_layout", {})}
END = L["end_seconds"]
tpl_name = prof.get("shorts_template_draft") or S.get("template_draft")
if not tpl_name:
    sys.exit("숏폼 템플릿 초안 이름이 없습니다. references/setup.md 3번을 보세요.")
TPL = cd.draft_path(tpl_name, prof)
styles = cd.text_styles(cd.load_draft(TPL))
if not styles:
    sys.exit(f"'{tpl_name}' 초안에 글자 트랙이 없습니다. 훅 한 줄과 자막 한 줄을 넣고 저장해 주세요.")
hook_t = styles[0]; cap_t = styles[1] if len(styles) > 1 else styles[0]

# 쓸 범위만 잘라 둔 사본 (자막 띠를 자를 때만 다시 인코딩)
allp = [p for it in S["items"] for p in it["pieces"]]
T0, T1 = max(0, min(a for a, b in allp) - END - 1), max(b for a, b in allp) + 1
src = S["source"]
if S.get("crop"):
    cut = os.path.join(proj["_dir"], "숏폼", "_src_crop.mp4"); os.makedirs(os.path.dirname(cut), exist_ok=True)
    if not os.path.exists(cut):
        enc = ["-c:v", "h264_nvenc", "-cq", "18"] if prof.get("encoder") == "h264_nvenc" else ["-c:v", "libx264", "-crf", "17", "-preset", "veryfast"]
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(T0), "-t", str(T1 - T0), "-i", src, "-vf", f"crop={S['crop']}",
                        *enc, "-c:a", "aac", "-b:a", "192k", cut], check=True)
    src, base = cut, T0
else:
    base = 0.0

caps = []
if S.get("captions_from"):
    ld = cd.load_draft(cd.draft_path(S["captions_from"], prof))
    tx = {m["id"]: m for m in ld["materials"].get("texts", [])}
    tts = [t for t in ld["tracks"] if t["type"] == "text"]
    # 자막 트랙: caption_track 이름이 있으면 그 트랙, 없으면 조각이 가장 많은 글자 트랙
    tt = next((t for t in tts if t.get("name") == S.get("caption_track")), None) or max(tts, key=lambda t: len(t["segments"]), default=None)
    for g in (tt["segments"] if tt else []):
        a = g["target_timerange"]["start"] / cd.US
        caps.append((a, a + g["target_timerange"]["duration"] / cd.US, cd.text_of(tx[g["material_id"]])))
    caps.sort()

import pycapcut as cc
from pycapcut import trange
sfx = prof.get("sfx", {})


def make(it):
    pieces = [tuple(p) for p in it["pieces"]]
    main = sum(b - a for a, b in pieces); total = main + END
    tmpd, sc = cd.new_temp_draft(1080, 1920, fps=prof.get("fps", 30))
    sc.add_track(cc.TrackType.video, "원본")
    vm = cc.VideoMaterial(src)
    off = 0.0
    for a, b in pieces:
        sc.add_segment(cc.VideoSegment(vm, trange(f"{off:.3f}s", f"{b - a:.3f}s"),
                                       source_timerange=trange(f"{a - base:.3f}s", f"{b - a:.3f}s")), "원본")
        off += b - a
    lb = pieces[-1][1]   # 끝 안내 동안 마지막 장면 끝부분을 소리 없이 이어 둔다
    sc.add_segment(cc.VideoSegment(vm, trange(f"{main:.3f}s", f"{END}s"),
                                   source_timerange=trange(f"{lb - base - END:.3f}s", f"{END}s"), volume=0.0), "원본")
    fx = []
    if sfx.get("whoosh") and os.path.exists(sfx["whoosh"]):
        fx.append((0.0, sfx["whoosh"], 0.35)); o = 0.0
        for a, b in pieces[:-1]:
            o += b - a; fx.append((max(0, o - 0.12), sfx["whoosh"], 0.25))
    if sfx.get("ding") and os.path.exists(sfx["ding"]):
        fx.append((main + 0.05, sfx["ding"], 0.5))
    if fx:
        sc.add_track(cc.TrackType.audio, "효과음")
        for at, f, v in sorted(fx):
            m = cc.AudioMaterial(f); dd = min(1.0, m.duration / cd.US - 0.02)
            sc.add_segment(cc.AudioSegment(m, trange(f"{at:.3f}s", f"{dd:.3f}s"), volume=v), "효과음")
    sc.save()
    d = cd.read_temp_draft(tmpd)
    cd.add_text_track(d, "훅", [cd.text_segment(hook_t, it["hook"], 0, total)])
    items, off = [], 0.0
    for a, b in pieces:
        for ca, cb, c in caps:
            if cb <= a + 0.05 or ca >= b - 0.05:
                continue
            s, e = max(ca, a) - a + off, min(cb, b) - a + off
            items.append(cd.text_segment(cap_t, c, s, e - s, y=L["caption_y"], scale=L["caption_scale"]))
        off += b - a
    if items:
        cd.add_text_track(d, "자막", items)
    if S.get("end_text"):
        cd.add_text_track(d, "안내", [cd.text_segment(hook_t, S["end_text"], main, END, y=L["end_y"], scale=L["end_scale"])])
    d["duration"] = cd.us(total)
    d["canvas_config"].update(ratio="9:16", width=1080, height=1920)
    print(f"저장 {cd.install_draft(d, TPL, it['name'], prof)}  {total:.1f}초")


pick = [int(x) for x in sys.argv[2:]] or range(1, len(S["items"]) + 1)
for k in pick:
    make(S["items"][k - 1])
