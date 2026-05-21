"""vault.propose_edit — the system's central write path.

Lifecycle:
  1. Auth + identity from header (caller already did this)
  2. Resolve target file (existing) or new path (creation)
  3. Open a branch `proposal/<agent>/<yyyymmdd-NNN>` from main
  4. Apply the patch on disk (write new file content)
  5. Commit on the branch with agent identity in the message
  6. Validate: schema + source check
  7. Classify: build Proposal and call classify()
  8. Decide routing:
       reject     → abandon branch, return reasons
       routine    → fast-forward merge to main, trigger /sync
       attention  → merge to main, notify roles (audit)
       material   → leave on branch, write rows to review_queue
  9. Write proposals row + audit_events row
 10. Return id + verdict
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import uuid
from datetime import date
from pathlib import Path
from typing import Any

import frontmatter
import httpx
from git import Repo

from mneme_classifier import Proposal, classify
from mneme_schemas import load as load_schemas, normalize

from ..audit import emit
from ..auth import Identity
from ..db import get_pool


VAULT_PATH = Path(os.environ.get("VAULT_PATH", "/vault"))
MANIFEST_PATH = Path(os.environ.get("MNEME_MANIFEST_PATH", "/manifest"))
INDEX_SYNC_URL = os.environ.get("INDEX_SYNC_URL", "http://index-sync:8003")

# Identify the body sections we know are likely competitor-data sections
COMPETITOR_SECTION_HINTS = ("competitor", "vs", "competitive")


def _slug_segment(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return s or "x"


def _branch_name(agent_id: str, seq: int) -> str:
    today = date.today().strftime("%Y%m%d")
    return f"proposal/{_slug_segment(agent_id)}/{today}-{seq:03d}"


def _ensure_repo() -> Repo:
    if not (VAULT_PATH / ".git").exists():
        # Initialize on first use (matches Makefile init-vault)
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=VAULT_PATH, check=True)
        subprocess.run(["git", "config", "user.email", "seed@mneme.local"], cwd=VAULT_PATH, check=True)
        subprocess.run(["git", "config", "user.name", "Mneme Seed"], cwd=VAULT_PATH, check=True)
        subprocess.run(["git", "add", "-A"], cwd=VAULT_PATH, check=True)
        subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "seed: empty"], cwd=VAULT_PATH, check=True)
    return Repo(VAULT_PATH)


def _apply_sections(body: str, sections: list[dict[str, Any]]) -> str:
    """Apply section-level patches.

    Each section dict has at minimum {path, patch} where `path` is the H2
    heading and `patch` is the replacement text for that section's body.
    If `path == "_append"` we tack the patch onto the end of the file.
    If the section doesn't exist, we append it as a new H2.
    """
    out = body
    for section in sections:
        path = section.get("path") or ""
        patch = section.get("patch", "")
        if path == "_append":
            out = out.rstrip() + "\n\n" + patch.strip() + "\n"
            continue
        # find and replace the section
        pattern = re.compile(rf"(^##\s+{re.escape(path)}\s*$)([\s\S]*?)(?=^##\s|\Z)",
                             re.MULTILINE)
        if pattern.search(out):
            out = pattern.sub(lambda m: f"{m.group(1)}\n\n{patch.strip()}\n\n", out)
        else:
            out = out.rstrip() + f"\n\n## {path}\n\n{patch.strip()}\n"
    return out


def _body_delta_pct(before: str, after: str) -> float:
    before_len = max(len(before), 1)
    diff = abs(len(after) - len(before))
    return 100.0 * diff / before_len


def _looks_like_competitor_touch(target_type: str, sections: list[dict[str, Any]]) -> bool:
    if target_type == "competitive-landscape":
        return True
    for s in sections:
        path = (s.get("path") or "").lower()
        if any(h in path for h in COMPETITOR_SECTION_HINTS):
            return True
    return False


def _looks_like_label_adjacent_claim(text: str) -> bool:
    lowered = text.lower()
    return any(t in lowered for t in (
        "first-line", "second-line", "superior", "best in class", "first in class",
        "indicated for", "label expansion",
    ))


def _looks_like_regulatory_assertion(text: str) -> bool:
    lowered = text.lower()
    return any(t in lowered for t in (
        "fda approved", "fda approval", "label change", "boxed warning",
        "post-marketing requirement",
    ))


async def _next_seq(conn) -> int:
    today = date.today().strftime("%Y%m%d")
    n = await conn.fetchval(
        "SELECT count(*) FROM proposals WHERE id LIKE $1",
        f"prop-{today}-%",
    )
    return int(n or 0) + 1


def _build_proposal(
    *,
    target_path: str,
    target_type: str,
    target_frontmatter: dict[str, Any],
    sections: list[dict[str, Any]],
    rationale: str,
    sources: list[dict[str, Any]],
    agent_id: str,
    agent_quality_score: float,
    body_delta_pct: float,
) -> Proposal:
    combined_text = " ".join(
        (s.get("patch") or "") for s in sections
    ) + " " + rationale
    return Proposal(
        target_path=target_path,
        target_type=target_type,
        target_frontmatter=target_frontmatter,
        change_sections=sections,
        body_delta_pct=body_delta_pct,
        rationale=rationale,
        claimed_sources=sources,
        agent_id=agent_id,
        agent_quality_score=agent_quality_score,
        contradictions=[],
        touches_competitor_data=_looks_like_competitor_touch(target_type, sections),
        asserts_regulatory_change=_looks_like_regulatory_assertion(combined_text),
        changes_governance_fields=False,
        has_label_adjacent_claim=_looks_like_label_adjacent_claim(combined_text),
        requires_source=(target_type != "entity-profile"),
    )


async def _trigger_sync(path: str) -> None:
    """Best-effort POST to index-sync /sync. Don't block on failure."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(f"{INDEX_SYNC_URL}/sync", json={"path": path})
    except Exception as e:
        # Don't fail the proposal because the index sync hiccupped
        print(f"warn: index-sync /sync failed for {path}: {e}")


async def propose_edit(
    identity: Identity,
    *,
    id: str | None,
    new_type: str | None,
    new_path: str | None,
    change: dict[str, Any],
    rationale: str,
    sources: list[dict[str, Any]],
    agent_quality_score: float = 0.95,
) -> dict[str, Any]:
    repo = _ensure_repo()
    pool = await get_pool()
    sections = change.get("sections") or []

    async with pool.acquire() as conn:
        seq = await _next_seq(conn)
    branch = _branch_name(identity.user_id, seq)
    today = date.today().strftime("%Y%m%d")
    prop_id = f"prop-{today}-{seq:03d}"

    # Resolve target file
    if id:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, path, type, frontmatter, body FROM files WHERE id = $1",
                id,
            )
        if not row:
            return {"error": f"file not found: {id}"}
        target_path = row["path"]
        target_type = row["type"]
        fm = row["frontmatter"]
        if isinstance(fm, str):
            fm = json.loads(fm)
        old_body = row["body"]
        old_full = frontmatter.Post(content=old_body, **fm)
    else:
        if not new_path or not new_type:
            return {"error": "id, or both new_path and new_type, required"}
        target_path = new_path
        target_type = new_type
        fm = {
            "id": f"kb-{_slug_segment(Path(new_path).stem)}",
            "type": new_type,
            "title": Path(new_path).stem.replace("-", " ").title(),
            "version": 1,
            "owners": [identity.user_id],
            "status": "proposed",
            "last_verified": date.today().isoformat(),
            "review_cycle": 14,
            "classification": "internal",
            "audience": list(identity.audience or ["bu:commercial-onco"]),
            "residency": ["us"],
            "entities": change.get("entities") or {},
            "sources": sources,
            "confidence": "medium",
        }
        old_body = f"# {fm['title']}\n"

    new_body = _apply_sections(old_body, sections)
    # Bump version on every successful proposal touching an existing file
    if id:
        fm["version"] = int(fm.get("version") or 1) + 1
        fm["last_verified"] = date.today().isoformat()
    new_full = frontmatter.Post(content=new_body, **fm)
    rendered = frontmatter.dumps(new_full)
    delta_pct = _body_delta_pct(old_body, new_body)

    # Validate schema (M0: hard fail on schema error → reject verdict)
    schemas = load_schemas(MANIFEST_PATH)
    schema_errors = schemas.validate(target_type, normalize(fm))

    # Source check (every claim must cite at least one source if the type requires it)
    requires_source = (target_type != "entity-profile")
    source_errors: list[str] = []
    if requires_source and not sources:
        source_errors.append("no sources provided")

    # Build & classify
    proposal = _build_proposal(
        target_path=target_path,
        target_type=target_type,
        target_frontmatter=fm,
        sections=sections,
        rationale=rationale,
        sources=sources,
        agent_id=identity.user_id,
        agent_quality_score=agent_quality_score,
        body_delta_pct=delta_pct,
    )
    verdict = classify(proposal)

    # If schema invalid, override to a hard reject (more specific than R1)
    if schema_errors:
        verdict_label = "reject"
        verdict_rule = "SCHEMA-invalid"
        verdict_reason = "Schema validation failed: " + "; ".join(schema_errors[:5])
        verdict_route = None
        verdict_cosign: list[str] = []
        verdict_trace = [{"rule": "SCHEMA-invalid", "matched": True, "reason": verdict_reason}]
    else:
        verdict_label = verdict.label
        verdict_rule = verdict.rule
        verdict_reason = verdict.reason
        verdict_route = verdict.route
        verdict_cosign = list(verdict.co_sign)
        verdict_trace = [t.to_dict() for t in verdict.trace]

    # Always perform branch + commit so the change has a real audit trail —
    # even rejected proposals are a record. Then merge or leave for review
    # based on the verdict.
    full_path = VAULT_PATH / target_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    original_branch = repo.active_branch.name if not repo.head.is_detached else "main"
    repo.git.checkout("-b", branch)
    full_path.write_text(rendered)
    repo.git.add(target_path)
    commit_msg = (
        f"proposal: {prop_id} on {target_path}\n\n"
        f"By: {identity.user_id}\n"
        f"Verdict: {verdict_label} ({verdict_rule})\n"
        f"Rationale: {rationale}\n"
    )
    repo.git.commit("-m", commit_msg, "--author", f"{identity.user_id} <{identity.user_id}@mneme.local>")

    state: str
    triggered_sync = False
    if verdict_label == "reject":
        # Don't merge. Leave branch for forensics; we could prune later.
        repo.git.checkout(original_branch)
        state = "rejected"
    elif verdict_label in ("routine", "attention"):
        # Merge to main
        repo.git.checkout(original_branch)
        repo.git.merge(branch, "--no-ff", "-m", f"merge {prop_id}: {verdict_label}")
        state = "merged"
        triggered_sync = True
    else:
        # material → leave on branch, queue for review
        repo.git.checkout(original_branch)
        state = "needs_review"

    # Persist proposal + queue + audit
    diff = [{"path": s.get("path"), "before": _section_excerpt(old_body, s.get("path")),
             "after": s.get("patch")} for s in sections]
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO proposals
            (id, branch, target_id, target_path, agent_id, rationale,
             verdict_label, verdict_rule, verdict_trace, diff, sources, state,
             created_at, decided_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(),
                    CASE WHEN $12 IN ('merged','rejected') THEN NOW() ELSE NULL END)
            """,
            prop_id, branch, id, target_path, identity.user_id, rationale,
            verdict_label, verdict_rule, json.dumps(verdict_trace),
            json.dumps(diff), json.dumps(sources), state,
        )

        if state == "needs_review":
            roles = verdict_cosign or [verdict_route] if verdict_route else verdict_cosign
            for role in roles:
                if not role:
                    continue
                await conn.execute(
                    """INSERT INTO review_queue (proposal_id, reviewer_role)
                       VALUES ($1, $2) ON CONFLICT DO NOTHING""",
                    prop_id, role,
                )

        await emit(
            conn,
            event_type="propose",
            subject=identity.user_id,
            target=prop_id,
            metadata={
                "tool": "vault.propose_edit",
                "target_path": target_path,
                "verdict_label": verdict_label,
                "verdict_rule": verdict_rule,
                "state": state,
                "branch": branch,
            },
        )
        if state == "merged":
            await emit(
                conn,
                event_type="merge",
                subject=identity.user_id,
                target=prop_id,
                metadata={"branch": branch, "target_path": target_path},
            )
        if state == "rejected":
            await emit(
                conn,
                event_type="reject_validate",
                subject=identity.user_id,
                target=prop_id,
                metadata={"reason": verdict_reason},
            )

    if triggered_sync:
        # Don't await — fire and forget so propose_edit returns fast
        asyncio.create_task(_trigger_sync(target_path))

    return {
        "proposal_id": prop_id,
        "branch": branch,
        "verdict": {
            "label": verdict_label,
            "rule": verdict_rule,
            "co_sign": verdict_cosign,
            "route": verdict_route,
            "reason": verdict_reason,
            "trace": verdict_trace,
        },
        "validation": {
            "schema_errors": schema_errors,
            "source_errors": source_errors,
        },
        "state": state,
    }


def _section_excerpt(body: str, section_path: str | None) -> str:
    if not section_path:
        return ""
    m = re.search(rf"^##\s+{re.escape(section_path)}\s*$([\s\S]*?)(?=^##\s|\Z)",
                  body, re.MULTILINE)
    return (m.group(1).strip() if m else "")
