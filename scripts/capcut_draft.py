# 캡컷(CapCut PC) 초안 공통 도구: 설정 읽기, 초안 읽기·백업, 글자 서식 복제, 새 이름으로 초안 설치
# 다른 스크립트가 import 해서 쓴다. 직접 실행하면 캡컷 초안 폴더와 초안 목록을 보여 준다.
import json, os, sys, copy, uuid, time, shutil, platform
try:
    sys.stdout.reconfigure(encoding="utf-8")  # 한글 출력이 깨지지 않게
except Exception:
    pass

US = 1_000_000
us = lambda x: int(round(x * US))
nid = lambda: str(uuid.uuid4()).upper()

PROFILE_PATH = os.environ.get("CONTENT_SYSTEM_PROFILE") or os.path.join(os.path.expanduser("~"), ".content-system", "profile.json")


def load_profile():
    """설정 인터뷰(references/setup.md)에서 만든 개인 설정. 없으면 빈 설정."""
    if os.path.exists(PROFILE_PATH):
        return json.load(open(PROFILE_PATH, encoding="utf-8"))
    return {}


def load_project(path):
    p = json.load(open(path, encoding="utf-8"))
    p["_dir"] = os.path.dirname(os.path.abspath(path))
    return p


def drafts_dir(profile=None):
    profile = profile if profile is not None else load_profile()
    if profile.get("capcut_drafts_dir"):
        return profile["capcut_drafts_dir"]
    if platform.system() == "Windows":
        return os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft")
    return os.path.expanduser("~/Movies/CapCut/User Data/Projects/com.lveditor.draft")


def draft_path(name, profile=None):
    return os.path.join(drafts_dir(profile), name)


def is_locked(d):
    """캡컷에서 열려 있는 초안이면 True. 이런 초안은 읽기만 한다."""
    return os.path.exists(os.path.join(d, ".locked"))


def main_json_path(d):
    """캡컷이 실제로 여는 파일은 Timelines/<main_timeline_id>/draft_content.json 이다."""
    pj = os.path.join(d, "Timelines", "project.json")
    if os.path.exists(pj):
        tl = json.load(open(pj, encoding="utf-8"))["main_timeline_id"]
        p = os.path.join(d, "Timelines", tl, "draft_content.json")
        if os.path.exists(p):
            return p
    return os.path.join(d, "draft_content.json")


def load_draft(d):
    return json.load(open(main_json_path(d), encoding="utf-8"))


def backup_draft(d, backup_dir):
    """읽기 전에 초안 파일을 작업 폴더 _백업/ 에 복사해 둔다."""
    os.makedirs(backup_dir, exist_ok=True)
    dst = os.path.join(backup_dir, f"{os.path.basename(d)}_{time.strftime('%Y%m%d-%H%M%S')}.json")
    shutil.copy(main_json_path(d), dst)
    return dst


def material_index(d):
    M = d["materials"]
    return {x["id"]: (k, x) for k, v in M.items() if isinstance(v, list) for x in v if isinstance(x, dict) and "id" in x}


def text_of(mat):
    try:
        return json.loads(mat["content"])["text"]
    except Exception:
        return mat.get("recognize_text", "")


def text_styles(d):
    """초안의 글자 트랙마다 첫 글자 조각의 (소재, 조각, 딸린 소재들)을 꺼낸다. 트랙 순서 그대로."""
    mid = material_index(d)
    out = []
    for t in d["tracks"]:
        if t["type"] != "text" or not t["segments"]:
            continue
        g = t["segments"][0]
        out.append((copy.deepcopy(mid[g["material_id"]][1]), copy.deepcopy(g),
                    [(mid[r][0], copy.deepcopy(mid[r][1])) for r in g.get("extra_material_refs", []) if r in mid]))
    return out


def text_segment(tpl, text, start, dur, y=None, scale=None):
    """서식 템플릿을 복제해 새 글자 조각을 만든다. 글꼴·색·테두리·애니메이션이 그대로 따라온다."""
    mat, seg, extras = copy.deepcopy(tpl[0]), copy.deepcopy(tpl[1]), copy.deepcopy(tpl[2])
    mat["id"] = nid()
    for key in ("content", "base_content"):
        if key not in mat or not mat[key]:
            continue
        ct = json.loads(mat[key])
        st = ct["styles"][0] if ct.get("styles") else None
        if st is not None:
            st["range"] = [0, len(text)]
            ct["styles"] = [st]
        ct["text"] = text
        mat[key] = json.dumps(ct, ensure_ascii=False)
    mat["recognize_text"] = text
    refs, add = [], []
    for k, m in extras:
        m["id"] = nid(); refs.append(m["id"]); add.append((k, m))
    seg.update(id=nid(), material_id=mat["id"], extra_material_refs=refs,
               target_timerange={"start": us(start), "duration": us(dur)})
    if y is not None:
        seg["clip"]["transform"]["y"] = y
    if scale is not None:
        seg["clip"]["scale"] = {"x": scale, "y": scale}
    return mat, seg, add


def add_text_track(d, name, items):
    """items: text_segment()가 돌려준 (소재, 조각, 딸린 소재) 목록"""
    M = d["materials"]
    segs = []
    for mat, seg, add in items:
        M.setdefault("texts", []).append(mat)
        for k, m in add:
            M.setdefault(k, []).append(m)
        segs.append(seg)
    d["tracks"].append({"attribute": 0, "flag": 0, "id": nid(), "is_default_name": False,
                        "name": name, "segments": segs, "type": "text"})


def check_refs(d):
    ids = set(material_index(d))
    miss = [r for tk in d["tracks"] for g in tk["segments"]
            for r in g.get("extra_material_refs", []) + [g["material_id"]] if r not in ids]
    if miss:
        raise SystemExit(f"초안 안에서 찾을 수 없는 소재 id {len(miss)}개: {miss[:3]}")


def new_temp_draft(width, height, fps=30):
    """영상·소리 트랙은 pycapcut 임시 초안에서 만들어야 형식이 맞는다."""
    import tempfile
    import pycapcut as cc
    tmpd = tempfile.mkdtemp()
    script = cc.DraftFolder(tmpd).create_draft("tmp", width, height, fps=fps)
    return tmpd, script


def read_temp_draft(tmpd):
    d = json.load(open(os.path.join(tmpd, "tmp", "draft_content.json"), encoding="utf-8"))
    shutil.rmtree(tmpd, ignore_errors=True)
    return d


SKIP = ("*.bak", "*.tmp", ".locked", "draft_content.json*", "Resources", "subdraft", "matting",
        "smart_crop", "qr_upload", "draft_cover.jpg")


def install_draft(d, template_dir, name, profile=None):
    """d(초안 JSON)를 template_dir 초안의 폴더 틀을 빌려 새 이름으로 캡컷에 등록한다.
    같은 이름이 있으면 아무것도 하지 않고 멈춘다(사용자가 고친 초안을 덮어쓰지 않기 위해)."""
    root_dir = drafts_dir(profile)
    dst = os.path.join(root_dir, name)
    if os.path.exists(dst):
        raise SystemExit(f"'{name}' 초안이 이미 있습니다. 덮어쓰지 않고 멈춥니다. 이름을 바꿔 다시 실행하세요.")
    check_refs(d)
    new_tl = nid(); d["id"] = new_tl
    txt = json.dumps(d, ensure_ascii=False)
    shutil.copytree(template_dir, dst, ignore=shutil.ignore_patterns(*SKIP))
    tdir = os.path.join(dst, "Timelines")
    if os.path.isdir(tdir):
        for x in os.listdir(tdir):
            p = os.path.join(tdir, x)
            if os.path.isdir(p):
                shutil.rmtree(p)
    os.makedirs(os.path.join(tdir, new_tl), exist_ok=True)
    for f in (os.path.join(dst, "draft_content.json"), os.path.join(tdir, new_tl, "draft_content.json")):
        open(f, "w", encoding="utf-8").write(txt)
    now = int(time.time() * US)
    pj = os.path.join(tdir, "project.json")
    proj = json.load(open(pj, encoding="utf-8")) if os.path.exists(pj) else {}
    proj.update(id=new_tl, main_timeline_id=new_tl, create_time=now, update_time=now)
    proj["timelines"] = [{"create_time": now, "id": new_tl, "is_marked_delete": False, "name": "타임라인 01", "update_time": now}]
    json.dump(proj, open(pj, "w", encoding="utf-8"), ensure_ascii=False)
    json.dump({"dockItems": [{"dockIndex": 0, "ratio": 1, "timelineIds": [new_tl], "timelineNames": ["타임라인 01"]}],
               "layoutOrientation": 1}, open(os.path.join(dst, "timeline_layout.json"), "w", encoding="utf-8"))
    draft_id = nid()
    mp = os.path.join(dst, "draft_meta_info.json")
    meta = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {}
    meta.update(draft_fold_path=dst.replace("\\", "/"), draft_id=draft_id, draft_name=name,
                tm_duration=d["duration"], tm_draft_create=now, tm_draft_modified=now)
    json.dump(meta, open(mp, "w", encoding="utf-8"), ensure_ascii=False)
    rp = os.path.join(root_dir, "root_meta_info.json")
    if os.path.exists(rp):
        shutil.copy(rp, rp + f".bak.{time.strftime('%Y%m%d-%H%M%S')}")
        root = json.load(open(rp, encoding="utf-8"))
        store = root.setdefault("all_draft_store", [])
        base = next((x for x in store if x.get("draft_name") == os.path.basename(template_dir)), store[0] if store else {})
        ent = copy.deepcopy(base)
        ent.update(draft_cover=os.path.join(dst, "draft_cover.jpg"), draft_fold_path=dst.replace("\\", "/"),
                   draft_id=draft_id, draft_json_file=os.path.join(dst, "draft_content.json"), draft_name=name,
                   tm_draft_create=now, tm_draft_modified=now, tm_duration=d["duration"])
        store.insert(0, ent)
        json.dump(root, open(rp, "w", encoding="utf-8"), ensure_ascii=False)
    return dst


if __name__ == "__main__":
    root = drafts_dir()
    print("캡컷 초안 폴더:", root)
    if os.path.isdir(root):
        ds = sorted((x for x in os.listdir(root) if os.path.isdir(os.path.join(root, x))),
                    key=lambda x: -os.path.getmtime(os.path.join(root, x)))
        for x in ds[:int(sys.argv[1]) if len(sys.argv) > 1 else 20]:
            print(("[열림] " if is_locked(os.path.join(root, x)) else "       ") + x)
