"""Weekly Adaptation Service.

Implements Phase 5:
- Rolling 7-day analysis window of eligible test attempts and diagnostic responses.
- Idempotent calculation of weekly adaptation snapshots.
- WoW (Week-over-Week) mastery delta and cognitive root-cause evolution.
- Remediation priority recalculation.
- Scheduled background task runner and authorized manual refresh.
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.core import (
    Concept,
    ConceptDependency,
    LearnerProfile,
    Question,
    Skill,
    StudentMastery,
    StudentResponse,
    Topic,
    User,
    WeeklyAnalysisSnapshot,
)
from backend.app.services.root_cause import (
    get_ancestors_within_hops,
    rank_root_cause_candidates,
)
from ml.graph.dag_validator import SimpleDiGraph

logger = logging.getLogger(__name__)


def compute_weekly_adaptation(
    db: Session,
    user_id: int,
    force: bool = False,
    now: dt.datetime | None = None,
) -> WeeklyAnalysisSnapshot:
    """Computes and stores a rolling 7-day adaptation snapshot for the specified user.

    Ensures idempotency: if a snapshot was calculated within the last 6 hours and not forced,
    the existing snapshot is returned.
    """
    current_time = now or dt.datetime.now(dt.timezone.utc)
    window_end = current_time
    window_start = current_time - dt.timedelta(days=7)

    # Idempotency check: don't create duplicate snapshots within 6 hours unless forced
    latest_existing = db.execute(
        select(WeeklyAnalysisSnapshot)
        .where(WeeklyAnalysisSnapshot.user_id == user_id)
        .order_by(WeeklyAnalysisSnapshot.calculated_at.desc())
    ).scalars().first()

    if not force and latest_existing:
        diff_seconds = (current_time - latest_existing.calculated_at.replace(tzinfo=dt.timezone.utc if latest_existing.calculated_at.tzinfo is None else latest_existing.calculated_at.tzinfo)).total_seconds()
        if diff_seconds < 6 * 3600:
            return latest_existing

    # Query responses in the rolling 7-day window
    window_responses = db.execute(
        select(StudentResponse)
        .where(
            StudentResponse.user_id == user_id,
            StudentResponse.answered_at >= window_start,
            StudentResponse.answered_at <= window_end,
        )
    ).scalars().all()

    total_attempts = len(window_responses)
    correct_count = sum(1 for r in window_responses if r.is_correct)
    accuracy_pct = round((correct_count / total_attempts * 100), 2) if total_attempts > 0 else 0.0

    # Query current student mastery estimates
    masteries = db.execute(
        select(StudentMastery).where(StudentMastery.user_id == user_id)
    ).scalars().all()
    mastery_estimates = {m.concept_id: round(m.mastery_score, 4) for m in masteries}

    # Fetch concept names
    all_concepts = db.execute(select(Concept)).scalars().all()
    concept_names = {c.id: c.name for c in all_concepts}

    # Calculate WoW mastery delta comparing with latest previous snapshot
    prev_snapshot = latest_existing
    curr_avg = (sum(mastery_estimates.values()) / len(mastery_estimates)) if mastery_estimates else 0.0
    if prev_snapshot and prev_snapshot.mastery_estimates_json:
        prev_estimates = prev_snapshot.mastery_estimates_json
        prev_avg = sum(prev_estimates.values()) / len(prev_estimates) if prev_estimates else 0.0
        wow_delta = round(curr_avg - prev_avg, 4)
    else:
        wow_delta = 0.0

    # Recompute ranked root causes across weak concepts
    deps = db.execute(select(ConceptDependency)).scalars().all()
    g = SimpleDiGraph([(d.prerequisite_id, d.concept_id) for d in deps])

    ranked_root_causes = []
    remediation_priorities = []

    # Identify concepts with weakness (<0.70) or failures in window
    failed_concept_ids = set()
    for resp in window_responses:
        if not resp.is_correct and resp.question_id:
            q = db.get(Question, resp.question_id)
            if q and q.concept_id:
                failed_concept_ids.add(q.concept_id)

    weak_concept_ids = {cid for cid, m in mastery_estimates.items() if m < 0.70}.union(failed_concept_ids)

    for cid in weak_concept_ids:
        ancestors = get_ancestors_within_hops(g, cid, max_hops=2)
        if ancestors:
            candidates = rank_root_cause_candidates(
                surface_concept_id=cid,
                ancestors_with_hops=ancestors,
                concept_mastery=mastery_estimates,
                concept_names=concept_names,
            )
            if candidates:
                top_cand = candidates[0]
                ranked_root_causes.append({
                    "surface_concept_id": cid,
                    "surface_concept_name": concept_names.get(cid, f"Concept {cid}"),
                    "primary_bottleneck_id": top_cand["candidate_concept_id"],
                    "primary_bottleneck_name": top_cand["candidate_name"],
                    "root_score": top_cand["root_score"],
                    "attention_alpha": top_cand["attention_alpha"],
                    "error_evidence": top_cand["error_evidence"],
                    "hop_distance": ancestors.get(top_cand["candidate_concept_id"], 1),
                })

    # Sort root causes descending by root_score
    ranked_root_causes.sort(key=lambda x: x["root_score"], reverse=True)

    # Derive remediation priorities from top root causes
    seen_prereqs = set()
    for rc in ranked_root_causes:
        prereq_id = rc["primary_bottleneck_id"]
        if prereq_id not in seen_prereqs:
            seen_prereqs.add(prereq_id)
            remediation_priorities.append({
                "concept_id": prereq_id,
                "concept_name": rc["primary_bottleneck_name"],
                "reason": f"Bottleneck prerequisite for {rc['surface_concept_name']} (Root Score: {rc['root_score']:.2f})",
                "urgency": "high" if rc["root_score"] > 0.60 else "medium",
                "recommended_action": f"Master foundational skills in {rc['primary_bottleneck_name']} to unblock {rc['surface_concept_name']}.",
            })

    # Create snapshot record
    snapshot = WeeklyAnalysisSnapshot(
        user_id=user_id,
        window_start=window_start,
        window_end=window_end,
        calculated_at=current_time,
        total_attempts=total_attempts,
        accuracy_pct=accuracy_pct,
        mastery_estimates_json=mastery_estimates,
        ranked_root_causes_json=ranked_root_causes,
        remediation_priorities_json=remediation_priorities,
        wow_mastery_delta=wow_delta,
        model_version="weekly_adaptation_v1",
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_weekly_adaptation_summary(db: Session, user_id: int) -> dict[str, Any]:
    """Retrieves the latest weekly adaptation snapshot and compares it with the previous snapshot."""
    snapshots = db.execute(
        select(WeeklyAnalysisSnapshot)
        .where(WeeklyAnalysisSnapshot.user_id == user_id)
        .order_by(WeeklyAnalysisSnapshot.calculated_at.desc())
        .limit(2)
    ).scalars().all()

    if not snapshots:
        # If no snapshot exists yet, generate one on-demand
        latest = compute_weekly_adaptation(db, user_id, force=True)
        prev = None
    else:
        latest = snapshots[0]
        prev = snapshots[1] if len(snapshots) > 1 else None

    # Calculate comparative progression metrics
    latest_rc_names = {rc["primary_bottleneck_name"] for rc in (latest.ranked_root_causes_json or [])}
    prev_rc_names = {rc["primary_bottleneck_name"] for rc in (prev.ranked_root_causes_json or [])} if prev else set()

    resolved_root_causes = list(prev_rc_names - latest_rc_names)
    new_root_causes = list(latest_rc_names - prev_rc_names)

    attempts_delta = latest.total_attempts - (prev.total_attempts if prev else 0)
    acc_delta = round(latest.accuracy_pct - (prev.accuracy_pct if prev else 0.0), 2)

    return {
        "latest": {
            "id": latest.id,
            "window_start": latest.window_start.isoformat() if latest.window_start else None,
            "window_end": latest.window_end.isoformat() if latest.window_end else None,
            "calculated_at": latest.calculated_at.isoformat() if latest.calculated_at else None,
            "total_attempts": latest.total_attempts,
            "accuracy_pct": latest.accuracy_pct,
            "mastery_estimates": latest.mastery_estimates_json or {},
            "ranked_root_causes": latest.ranked_root_causes_json or [],
            "remediation_priorities": latest.remediation_priorities_json or [],
            "wow_mastery_delta": latest.wow_mastery_delta,
            "model_version": latest.model_version,
        },
        "previous": {
            "id": prev.id,
            "window_start": prev.window_start.isoformat() if prev.window_start else None,
            "window_end": prev.window_end.isoformat() if prev.window_end else None,
            "calculated_at": prev.calculated_at.isoformat() if prev.calculated_at else None,
            "total_attempts": prev.total_attempts,
            "accuracy_pct": prev.accuracy_pct,
            "wow_mastery_delta": prev.wow_mastery_delta,
        } if prev else None,
        "comparison": {
            "wow_mastery_delta": latest.wow_mastery_delta,
            "attempts_delta": attempts_delta,
            "accuracy_delta": acc_delta,
            "resolved_root_causes": resolved_root_causes,
            "newly_identified_root_causes": new_root_causes,
            "remediation_progress_note": (
                f"Resolved {len(resolved_root_causes)} prerequisite bottleneck(s); identified {len(new_root_causes)} new priority area(s)."
                if prev else "Initial baseline weekly adaptation established."
            ),
        },
    }


def run_scheduled_weekly_adaptation_job(db: Session) -> int:
    """Executes weekly adaptation calculation for all users who have response or mastery activity.

    Idempotent and safe to run on recurring schedules.
    """
    user_ids = db.execute(
        select(User.id).order_by(User.id)
    ).scalars().all()

    processed_count = 0
    for uid in user_ids:
        try:
            compute_weekly_adaptation(db, uid, force=False)
            processed_count += 1
        except Exception as exc:
            logger.error("Failed weekly adaptation for user %d: %s", uid, exc, exc_info=True)
            db.rollback()

    return processed_count
