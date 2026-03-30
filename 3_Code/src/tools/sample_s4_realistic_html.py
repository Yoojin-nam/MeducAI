"""
Sample N REALISTIC(EXAM) images and generate an HTML preview (question + answer + image).

This avoids running full S3->S4 for an entire run_tag when you just want a quick sanity check.

Example:
  python3 3_Code/src/tools/sample_s4_realistic_html.py \
    --base_dir /path/to/workspace/workspace/MeducAI \
    --run_tag FINAL_DISTRIBUTION_S4TEST_REALISTIC_20260101_000544 \
    --arm G \
    --n 10 \
    --seed 123 \
    --use_repaired

Notes:
- Uses current code + prompt templates to recompile S3 specs in-memory (so your latest prompt/constraint fixes apply).
- Will try to load `{base_dir}/.env` automatically (best-effort).
- Requires an API key available as GOOGLE_API_KEY, or a numbered key like GOOGLE_API_KEY_1 / GOOGLE_API_KEY_2 / ...
- Optional: set S4_IMAGE_TEMPERATURE_REALISTIC=0.10~0.15 to reduce exaggeration.
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module: {module_name} from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            s = ln.strip()
            if not s:
                continue
            try:
                out.append(json.loads(s))
            except Exception:
                continue
    return out


def _load_s1_structs_by_group(path: Path) -> Dict[str, Dict[str, Any]]:
    structs: Dict[str, Dict[str, Any]] = {}
    for rec in _read_jsonl(path):
        gid = str(rec.get("group_id") or "").strip()
        if gid:
            structs[gid] = rec
    return structs


def _short(s: str, n: int) -> str:
    t = " ".join((s or "").strip().split())
    if len(t) <= n:
        return t
    return t[: n - 1] + "…"


def _esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def _pick_paths(*, out_dir: Path, arm: str, s1_arm: str, use_repaired: bool) -> Tuple[Path, Path]:
    # S2 results
    s2_repaired = out_dir / f"s2_results__s1arm{s1_arm}__s2arm{arm}__repaired.jsonl"
    s2_base = out_dir / f"s2_results__s1arm{s1_arm}__s2arm{arm}.jsonl"
    if use_repaired and s2_repaired.exists():
        s2_path = s2_repaired
    elif s2_base.exists():
        s2_path = s2_base
    elif s2_repaired.exists():
        s2_path = s2_repaired
    else:
        raise FileNotFoundError(f"Missing S2 results. Tried: {s2_base.name}, {s2_repaired.name}")

    # S1 struct
    s1_repaired = out_dir / f"stage1_struct__arm{s1_arm}__repaired.jsonl"
    s1_base = out_dir / f"stage1_struct__arm{s1_arm}.jsonl"
    if use_repaired and s1_repaired.exists():
        s1_path = s1_repaired
    elif s1_base.exists():
        s1_path = s1_base
    elif s1_repaired.exists():
        s1_path = s1_repaired
    else:
        raise FileNotFoundError(f"Missing S1 struct. Tried: {s1_base.name}, {s1_repaired.name}")

    return s2_path, s1_path


def _extract_prompt_field(prompt: str, label: str) -> str:
    """
    Best-effort extraction from prompt_en for HTML display.
    Expected lines in prompt:
      - Question (front): ...
      - Correct answer: ...
    """
    if not prompt:
        return ""
    m = re.search(rf"(?m)^[\-\s]*{re.escape(label)}\s*:\s*(.+)$", prompt)
    return (m.group(1).strip() if m else "")


def _load_dotenv_if_present(base_dir: Path) -> None:
    """Best-effort load of .env so CLI runs match pipeline scripts."""
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return
    env_path = base_dir / ".env"
    try:
        if env_path.exists():
            load_dotenv(env_path, override=True)
        else:
            load_dotenv(override=True)
    except Exception:
        return


def _resolve_api_key_from_env() -> str:
    """
    Resolve an API key from environment.
    Priority:
      1) GOOGLE_API_KEY
      2) GOOGLE_API_KEY_1, GOOGLE_API_KEY_2, ... (smallest index found)
    """
    direct = os.getenv("GOOGLE_API_KEY", "").strip()
    if direct:
        return direct

    # Look for numbered keys.
    best_num = None
    best_key = None
    for k, v in os.environ.items():
        if not k.startswith("GOOGLE_API_KEY_"):
            continue
        suffix = k[len("GOOGLE_API_KEY_") :]
        try:
            n = int(suffix)
        except Exception:
            continue
        vv = (v or "").strip()
        if not vv:
            continue
        if best_num is None or n < best_num:
            best_num = n
            best_key = vv

    return best_key or ""


def main() -> None:
    ap = argparse.ArgumentParser(description="Sample REALISTIC S4 images and build an HTML preview.")
    ap.add_argument("--base_dir", required=True)
    ap.add_argument("--run_tag", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--s1_arm", default=None)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int, default=123)
    ap.add_argument("--use_repaired", action="store_true")
    ap.add_argument(
        "--from_s3_spec",
        action="store_true",
        help="Sample directly from s3_image_spec__armX.jsonl (ensures S3 re-run changes are reflected).",
    )
    ap.add_argument("--image_model", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    base_dir = Path(args.base_dir).resolve()
    run_tag = str(args.run_tag).strip()
    arm = str(args.arm).strip().upper()
    s1_arm = str(args.s1_arm).strip().upper() if args.s1_arm else arm
    n = max(1, int(args.n))
    seed = int(args.seed)
    use_repaired = bool(args.use_repaired)

    out_dir = base_dir / "2_Data" / "metadata" / "generated" / run_tag
    if not out_dir.exists():
        raise FileNotFoundError(f"run_tag directory not found: {out_dir}")

    # Load .env (best-effort) so the user doesn't need to manually export keys.
    _load_dotenv_if_present(base_dir)

    # Load S4 module + build client early (used by both modes)
    src_dir = base_dir / "3_Code" / "src"
    tools_dir = src_dir / "tools"
    s3_path = src_dir / "03_s3_policy_resolver.py"
    s4_path = src_dir / "04_s4_image_generator.py"
    prompt_bundle_path = tools_dir / "prompt_bundle.py"

    s4_mod = _load_module("s4_image_generator", s4_path)

    api_key = _resolve_api_key_from_env()
    if not api_key:
        raise RuntimeError(
            "Missing Google API key in environment. Set GOOGLE_API_KEY, or GOOGLE_API_KEY_1/2/... "
            "(or put it in base_dir/.env)."
        )
    client = s4_mod.build_gemini_client(api_key)

    # ------------------------------------------------------------
    # Mode A) Sample directly from S3 output file
    # ------------------------------------------------------------
    if bool(getattr(args, "from_s3_spec", False)):
        s3_spec_path = out_dir / f"s3_image_spec__arm{arm}.jsonl"
        if not s3_spec_path.exists():
            raise FileNotFoundError(f"Missing S3 image spec: {s3_spec_path}")

        all_specs = _read_jsonl(s3_spec_path)
        candidates_specs: List[Dict[str, Any]] = []
        for spec in all_specs:
            if str(spec.get("spec_kind") or "").strip() != "S2_CARD_IMAGE":
                continue
            role = str(spec.get("card_role") or "").strip().upper()
            if role not in ("Q1", "Q2"):
                continue
            prof = str(spec.get("exam_prompt_profile") or "").strip().lower()
            if "realistic" not in prof and "pacs" not in prof:
                continue
            candidates_specs.append(spec)

        if not candidates_specs:
            raise RuntimeError(f"No REALISTIC S2_CARD_IMAGE specs found in {s3_spec_path.name}")

        rnd = random.Random(seed)
        picked_specs = candidates_specs if len(candidates_specs) <= n else rnd.sample(candidates_specs, n)

        out_root = Path(args.out).resolve() if args.out else (out_dir / "reports" / "s4_realistic_sample")
        img_dir = out_root / "images"
        img_dir.mkdir(parents=True, exist_ok=True)

        rows_html: List[str] = []
        failures: List[str] = []

        for i, spec in enumerate(picked_specs, start=1):
            gid = str(spec.get("group_id") or "").strip()
            eid = str(spec.get("entity_id") or "").strip()
            entity_name = str(spec.get("entity_name") or "").strip()
            role = str(spec.get("card_role") or "").strip().upper()
            prompt_en = str(spec.get("prompt_en") or "")

            safe_gid = gid.replace(":", "_")
            safe_eid = eid.replace(":", "_")
            fname = f"SAMPLE__{i:02d}__IMG__{run_tag}__{safe_gid}__{safe_eid}__{role}.jpg"
            out_path = img_dir / fname

            ok = False
            try:
                ok, _rag, _ = s4_mod.generate_image(
                    image_spec=spec,
                    output_path=out_path,
                    client=client,
                    rag_enabled=False,
                    base_dir=base_dir,
                    image_model=args.image_model,
                    quota_limiter=None,
                    metrics_path=None,
                    run_tag=run_tag,
                )
            except Exception as e:
                failures.append(f"[generate] {gid}/{eid}/{role}: {e}")
                ok = False

            front = _extract_prompt_field(prompt_en, "Question (front)")
            answer = _extract_prompt_field(prompt_en, "Correct answer") or str(spec.get("answer_text") or "")
            modality = str(spec.get("modality") or "")
            anatomy = str(spec.get("anatomy_region") or "")
            vos = str(spec.get("view_or_sequence") or "")
            kf = spec.get("key_findings_keywords") or []
            if not isinstance(kf, list):
                kf = []
            kf_str = ", ".join([str(x).strip() for x in kf if str(x).strip()])

            img_rel = f"images/{fname}"
            img_tag = f'<img src="{_esc(img_rel)}" alt="{_esc(fname)}" />' if ok and out_path.exists() else "<div class='bad'>FAILED</div>"

            rows_html.append(
                f"""
<div class="card">
  <div class="meta">
    <div class="title">{_esc(entity_name)} <span class="small">({safe_gid} / {safe_eid} / {role})</span></div>
    <div class="kv"><b>modality</b>: {_esc(modality)} &nbsp; <b>anatomy</b>: {_esc(anatomy)} &nbsp; <b>view</b>: {_esc(vos)}</div>
    <div class="kv"><b>key_findings</b>: {_esc(kf_str)}</div>
    <div class="qa">
      <div><b>Q</b>: {_esc(_short(front, 320))}</div>
      <div><b>A</b>: {_esc(_short(answer, 220))}</div>
    </div>
  </div>
  <div class="img">
    {img_tag}
  </div>
</div>
"""
            )

        out_root.mkdir(parents=True, exist_ok=True)
        html_path = out_root / "sample_preview.html"
        failures_block = ""
        if failures:
            failures_block = "<h3>Failures</h3><pre class='failures'>" + _esc("\n".join(failures[:200])) + "</pre>"

        doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>S4 REALISTIC Sample Preview ({_esc(run_tag)})</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; color: #111; }}
  h1 {{ margin: 0 0 8px 0; font-size: 20px; }}
  .sub {{ color: #555; margin-bottom: 16px; }}
  .card {{ display: grid; grid-template-columns: 1fr 420px; gap: 16px; padding: 14px; border: 1px solid #ddd; border-radius: 10px; margin-bottom: 14px; }}
  .title {{ font-weight: 700; margin-bottom: 6px; }}
  .small {{ font-weight: 400; color: #666; font-size: 12px; }}
  .kv {{ color: #222; font-size: 13px; margin: 4px 0; }}
  .qa {{ margin-top: 10px; font-size: 13px; line-height: 1.35; }}
  .img img {{ width: 100%; height: auto; border-radius: 8px; border: 1px solid #eee; background: #fafafa; }}
  .bad {{ padding: 10px; color: #b00020; font-weight: 700; }}
  .failures {{ background: #fafafa; border: 1px solid #eee; padding: 10px; overflow-x: auto; }}
</style>
</head>
<body>
  <h1>S4 REALISTIC Sample Preview</h1>
  <div class="sub">
    run_tag: <b>{_esc(run_tag)}</b> &nbsp; arm: <b>{_esc(arm)}</b> &nbsp; source: <code>{_esc(s3_spec_path.name)}</code> &nbsp; n: <b>{len(rows_html)}</b> &nbsp; seed: <b>{seed}</b>
  </div>
  {failures_block}
  {''.join(rows_html)}
</body>
</html>
"""
        html_path.write_text(doc, encoding="utf-8")
        print(f"[OK] HTML: {html_path}")
        print(f"[OK] Images: {img_dir}")
        if failures:
            print(f"[WARN] Failures: {len(failures)} (see HTML)")
        return

    # ------------------------------------------------------------
    # Mode B) Legacy: in-memory recompilation from S2
    # ------------------------------------------------------------
    s2_path, s1_path = _pick_paths(out_dir=out_dir, arm=arm, s1_arm=s1_arm, use_repaired=use_repaired)
    s1_by_group = _load_s1_structs_by_group(s1_path)

    prompt_bundle_mod = _load_module("prompt_bundle", prompt_bundle_path)
    prompt_bundle = prompt_bundle_mod.load_prompt_bundle(str(base_dir))
    s3_mod = _load_module("s3_policy_resolver", s3_path)

    # Candidate cards (Q1/Q2 with image_hint)
    candidates: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
    for rec in _read_jsonl(s2_path):
        gid = str(rec.get("group_id") or "").strip()
        eid = str(rec.get("entity_id") or "").strip()
        if not gid or not eid:
            continue
        cards = rec.get("anki_cards") or []
        if not isinstance(cards, list):
            continue
        for card in cards:
            if not isinstance(card, dict):
                continue
            role = str(card.get("card_role") or "").strip().upper()
            if role not in ("Q1", "Q2"):
                continue
            ih = card.get("image_hint")
            if not isinstance(ih, dict) or not ih:
                continue
            candidates.append((rec, card))

    if not candidates:
        raise RuntimeError(f"No eligible candidates found in {s2_path}")

    rnd = random.Random(seed)
    picked = candidates if len(candidates) <= n else rnd.sample(candidates, n)

    out_root = Path(args.out).resolve() if args.out else (out_dir / "reports" / "s4_realistic_sample")
    img_dir = out_root / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    rows_html: List[str] = []
    failures: List[str] = []

    for i, (rec, card) in enumerate(picked, start=1):
        gid = str(rec.get("group_id") or "").strip()
        eid = str(rec.get("entity_id") or "").strip()
        entity_name = str(rec.get("entity_name") or "").strip()
        role = str(card.get("card_role") or "").strip().upper()
        image_hint = card.get("image_hint") or {}

        s1_struct = s1_by_group.get(gid, {})
        s1_visual_context = {
            "visual_type_category": s1_struct.get("visual_type_category", "General"),
            "master_table_markdown_kr": s1_struct.get("master_table_markdown_kr", ""),
        }

        try:
            spec = s3_mod.compile_image_spec(
                run_tag=run_tag,
                group_id=gid,
                entity_id=eid,
                entity_name=entity_name,
                card_role=role,
                card=card,
                image_hint=image_hint,
                s1_visual_context=s1_visual_context,
                prompt_bundle=prompt_bundle,
                image_style="realistic",
            )
        except Exception as e:
            failures.append(f"[compile] {gid}/{eid}/{role}: {e}")
            continue

        safe_gid = gid.replace(":", "_")
        safe_eid = eid.replace(":", "_")
        fname = f"SAMPLE__{i:02d}__IMG__{run_tag}__{safe_gid}__{safe_eid}__{role}.jpg"
        out_path = img_dir / fname

        ok = False
        try:
            ok, _rag, _ = s4_mod.generate_image(
                image_spec=spec,
                output_path=out_path,
                client=client,
                rag_enabled=False,
                base_dir=base_dir,
                image_model=args.image_model,
                quota_limiter=None,
                metrics_path=None,
                run_tag=run_tag,
            )
        except Exception as e:
            failures.append(f"[generate] {gid}/{eid}/{role}: {e}")
            ok = False

        front = str(card.get("front") or "")
        answer = str(spec.get("answer_text") or "")
        modality = str(spec.get("modality") or "")
        anatomy = str(spec.get("anatomy_region") or "")
        vos = str(spec.get("view_or_sequence") or image_hint.get("view_or_sequence") or "")
        kf = spec.get("key_findings_keywords") or []
        if not isinstance(kf, list):
            kf = []
        kf_str = ", ".join([str(x).strip() for x in kf if str(x).strip()])

        img_rel = f"images/{fname}"
        img_tag = f'<img src="{_esc(img_rel)}" alt="{_esc(fname)}" />' if ok and out_path.exists() else "<div class='bad'>FAILED</div>"

        rows_html.append(
            f"""
<div class="card">
  <div class="meta">
    <div class="title">{_esc(entity_name)} <span class="small">({safe_gid} / {safe_eid} / {role})</span></div>
    <div class="kv"><b>modality</b>: {_esc(modality)} &nbsp; <b>anatomy</b>: {_esc(anatomy)} &nbsp; <b>view</b>: {_esc(vos)}</div>
    <div class="kv"><b>key_findings</b>: {_esc(kf_str)}</div>
    <div class="qa">
      <div><b>Q</b>: {_esc(_short(front, 320))}</div>
      <div><b>A</b>: {_esc(_short(answer, 220))}</div>
    </div>
  </div>
  <div class="img">
    {img_tag}
  </div>
</div>
"""
        )

    out_root.mkdir(parents=True, exist_ok=True)
    html_path = out_root / "sample_preview.html"
    failures_block = ""
    if failures:
        failures_block = "<h3>Failures</h3><pre class='failures'>" + _esc("\n".join(failures[:200])) + "</pre>"

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>S4 REALISTIC Sample Preview ({_esc(run_tag)})</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; color: #111; }}
  h1 {{ margin: 0 0 8px 0; font-size: 20px; }}
  .sub {{ color: #555; margin-bottom: 16px; }}
  .card {{ display: grid; grid-template-columns: 1fr 420px; gap: 16px; padding: 14px; border: 1px solid #ddd; border-radius: 10px; margin-bottom: 14px; }}
  .title {{ font-weight: 700; margin-bottom: 6px; }}
  .small {{ font-weight: 400; color: #666; font-size: 12px; }}
  .kv {{ color: #222; font-size: 13px; margin: 4px 0; }}
  .qa {{ margin-top: 10px; font-size: 13px; line-height: 1.35; }}
  .img img {{ width: 100%; height: auto; border-radius: 8px; border: 1px solid #eee; background: #fafafa; }}
  .bad {{ padding: 10px; color: #b00020; font-weight: 700; }}
  .failures {{ background: #fafafa; border: 1px solid #eee; padding: 10px; overflow-x: auto; }}
</style>
</head>
<body>
  <h1>S4 REALISTIC Sample Preview</h1>
  <div class="sub">
    run_tag: <b>{_esc(run_tag)}</b> &nbsp; arm: <b>{_esc(arm)}</b> &nbsp; s2: <code>{_esc(s2_path.name)}</code> &nbsp; n: <b>{len(rows_html)}</b> &nbsp; seed: <b>{seed}</b>
  </div>
  {failures_block}
  {''.join(rows_html)}
</body>
</html>
"""
    html_path.write_text(doc, encoding="utf-8")

    print(f"[OK] HTML: {html_path}")
    print(f"[OK] Images: {img_dir}")
    if failures:
        print(f"[WARN] Failures: {len(failures)} (see HTML)")


if __name__ == "__main__":
    main()


