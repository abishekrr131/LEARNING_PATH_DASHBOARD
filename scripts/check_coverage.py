"""Question Bank and Sub-Question Coverage Report Script.

Computes coverage per Career Target and Syllabus Topic:
- Count of main approved questions
- Count of questions with completed sub-question diagnostic sets
- Shortfall against minimum target (default 8 main questions per topic)
"""
from __future__ import annotations

import argparse
import os
import sys
from sqlalchemy import func, select
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.db.session import engine
from backend.app.models.core import CareerTarget, Concept, Question, Skill, SubQuestion, Topic


def generate_coverage_report(target_filter: int | None = None, min_main: int = 8) -> dict:
    with Session(engine) as db:
        query = db.query(CareerTarget)
        if target_filter:
            query = query.filter(CareerTarget.id == target_filter)
        targets = query.order_by(CareerTarget.id).all()

        report_data = []

        for tgt in targets:
            skills = db.query(Skill).filter(Skill.target_id == tgt.id).order_by(Skill.id).all()
            target_summary = {
                "target_id": tgt.id,
                "target_name": tgt.name,
                "category": tgt.category,
                "topics": [],
                "total_main": 0,
                "total_sub_sets": 0,
                "total_shortfall": 0,
            }

            for sk in skills:
                topics = db.query(Topic).filter(Topic.skill_id == sk.id).order_by(Topic.id).all()
                for tp in topics:
                    # Find all concept IDs for this topic
                    concept_ids = [c.id for c in db.query(Concept.id).filter(Concept.topic_id == tp.id).all()]
                    
                    # Count approved main questions
                    main_qs = db.query(Question).filter(
                        Question.concept_id.in_(concept_ids),
                        Question.review_status.in_(["approved", "generated", "curated"]),
                    ).all()
                    main_count = len(main_qs)
                    
                    # Count questions having >= 3 sub-questions
                    sub_set_count = 0
                    for q in main_qs:
                        sq_count = db.query(SubQuestion).filter(SubQuestion.parent_question_id == q.id).count()
                        if sq_count >= 3:
                            sub_set_count += 1

                    shortfall = max(0, min_main - main_count)

                    target_summary["topics"].append({
                        "skill_name": sk.name,
                        "topic_id": tp.id,
                        "topic_name": tp.name,
                        "main_questions": main_count,
                        "sub_question_sets": sub_set_count,
                        "min_required": min_main,
                        "shortfall": shortfall,
                    })

                    target_summary["total_main"] += main_count
                    target_summary["total_sub_sets"] += sub_set_count
                    target_summary["total_shortfall"] += shortfall

            report_data.append(target_summary)

        return report_data


def print_report(reports: list[dict], min_main: int = 8):
    print("=" * 95)
    print(f"QUESTION BANK & SUB-QUESTION COVERAGE AUDIT (Minimum Target: {min_main} Main Qs / Topic)")
    print("=" * 95)

    for tgt in reports:
        print(f"\nTarget #{tgt['target_id']}: {tgt['target_name']} [{tgt['category']}]")
        print("-" * 95)
        print(f"{'Topic ID':<9} | {'Skill':<28} | {'Topic Name':<32} | {'Main Qs':<7} | {'Sub Sets':<8} | {'Shortfall':<9}")
        print("-" * 95)

        for row in tgt["topics"]:
            skill_short = (row["skill_name"][:26] + "..") if len(row["skill_name"]) > 28 else row["skill_name"]
            topic_short = (row["topic_name"][:30] + "..") if len(row["topic_name"]) > 32 else row["topic_name"]
            print(
                f"{row['topic_id']:<9} | {skill_short:<28} | {topic_short:<32} | "
                f"{row['main_questions']:<7} | {row['sub_question_sets']:<8} | {row['shortfall']:<9}"
            )

        print("-" * 95)
        print(
            f"TOTALS for {tgt['target_name']}: "
            f"Topics: {len(tgt['topics'])}, Main Questions: {tgt['total_main']}, "
            f"Sub-Question Sets: {tgt['total_sub_sets']}, Shortfall: {tgt['total_shortfall']}"
        )
        print("=" * 95)


def main():
    parser = argparse.ArgumentParser(description="Check question bank coverage per target and topic.")
    parser.add_argument("--target", type=int, default=None, help="Target ID to filter (e.g. 7 for Banking)")
    parser.add_argument("--min-main", type=int, default=8, help="Minimum required main questions per topic")
    args = parser.parse_args()

    reports = generate_coverage_report(target_filter=args.target, min_main=args.min_main)
    print_report(reports, min_main=args.min_main)


if __name__ == "__main__":
    main()
