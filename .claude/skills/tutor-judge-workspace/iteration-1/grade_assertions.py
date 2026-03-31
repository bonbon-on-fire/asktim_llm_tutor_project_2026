"""Grade each run against the eval assertions and write grading.json files."""
import json, os, sys

VALID_SUB_IDS = {
    "1.1.A.a", "1.1.B.a", "1.1.C.a", "1.1.C.b",
    "1.2.A.a", "1.2.B.a",
    "1.3.A.a", "1.3.B.a", "1.3.B.b", "1.3.D.a",
    "2.1.A.a", "2.2.A.a", "2.2.B.a",
    "3.1.A.a", "3.1.B.a", "3.2.A.a", "3.2.B.a", "3.2.B.b",
}
REQUIRED_CRITERIA = {"1.1", "1.2", "1.3", "2.1", "2.2", "3.1", "3.2"}
CRITERIA_MAX = {"1.1": 12, "1.2": 6, "1.3": 6, "2.1": 4, "2.2": 8, "3.1": 6, "3.2": 4}
SECTION_MAP = {"pedagogy": ["1.1","1.2","1.3"], "dialogue": ["2.1","2.2"], "communication": ["3.1","3.2"]}

BASE = sys.argv[1]  # iteration directory

def grade_run(grade_path, assertions, eval_name, run_type):
    """Evaluate one grade JSON against assertion definitions for a single run."""

    results = {"eval_name": eval_name, "run_type": run_type, "expectations": []}
    try:
        with open(grade_path, encoding="utf-8") as f:
            g = json.load(f)
    except Exception as e:
        for a in assertions:
            results["expectations"].append({"text": a["name"], "passed": False, "evidence": f"Failed to load JSON: {e}"})
        return results

    for a in assertions:
        name = a["name"]
        passed = False
        evidence = ""

        if name == "valid_json_structure":
            needed = {"sections","total_base_score","max_base_score","max_score","overview","total_score","judge_llm_calls"}
            present = set(g.keys()) & needed
            missing = needed - present
            passed = len(missing) == 0
            evidence = f"Present: {sorted(present)}. Missing: {sorted(missing)}" if missing else "All required keys present"

        elif name == "all_criteria_present":
            found = set()
            sections = g.get("sections", {})
            for sec_data in sections.values():
                criteria = sec_data.get("criteria", {})
                for cid, cdata in criteria.items():
                    if all(k in cdata for k in ["score","max","deductions"]):
                        found.add(cid)
            missing = REQUIRED_CRITERIA - found
            passed = len(missing) == 0
            evidence = f"Found: {sorted(found)}. Missing: {sorted(missing)}" if missing else "All 7 criteria present with required fields"

        elif name == "score_consistency":
            issues = []
            sections = g.get("sections", {})
            computed_total = 0
            for sec_name, sec_data in sections.items():
                criteria = sec_data.get("criteria", {})
                sec_sum = sum(c.get("score", 0) for c in criteria.values())
                sec_base = sec_data.get("base", {}).get("score", sec_sum)
                if sec_sum != sec_base:
                    issues.append(f"{sec_name}: criteria sum {sec_sum} != base {sec_base}")
                computed_total += sec_sum
            tbs = g.get("total_base_score", g.get("total_score", -1))
            ts = g.get("total_score", -1)
            if tbs != ts:
                issues.append(f"total_base_score {tbs} != total_score {ts}")
            if computed_total != ts:
                issues.append(f"computed total {computed_total} != total_score {ts}")
            passed = len(issues) == 0
            evidence = "; ".join(issues) if issues else "All scores internally consistent"

        elif name == "valid_sub_criterion_ids":
            invalid = []
            sections = g.get("sections", {})
            for sec_data in sections.values():
                for cdata in sec_data.get("criteria", {}).values():
                    for d in cdata.get("deductions", []):
                        sid = d.get("sub_criterion_id", "")
                        if sid and sid not in VALID_SUB_IDS:
                            invalid.append(sid)
                        elif not sid:
                            invalid.append("(missing sub_criterion_id)")
            has_deductions = any(
                d for sec_data in sections.values()
                for cdata in sec_data.get("criteria", {}).values()
                for d in cdata.get("deductions", [])
            )
            if not has_deductions:
                passed = True
                evidence = "No deductions to validate"
            else:
                passed = len(invalid) == 0
                evidence = f"Invalid IDs: {invalid}" if invalid else "All sub_criterion_ids match rubric"

        elif name == "evidence_turns_cited":
            total_d = 0
            with_turns = 0
            sections = g.get("sections", {})
            for sec_data in sections.values():
                for cdata in sec_data.get("criteria", {}).values():
                    for d in cdata.get("deductions", []):
                        total_d += 1
                        et = d.get("evidence_turns", [])
                        if et and all(1 <= t <= 10 for t in et):
                            with_turns += 1
            if total_d == 0:
                passed = True
                evidence = "No deductions to check"
            else:
                pct = with_turns / total_d * 100
                passed = pct >= 80
                evidence = f"{with_turns}/{total_d} deductions ({pct:.0f}%) cite valid turns"

        elif name == "score_in_range":
            ts = g.get("total_score", -1)
            passed = 0 <= ts <= 46
            evidence = f"total_score = {ts}"

        elif name == "overview_present":
            ov = g.get("overview", [])
            passed = isinstance(ov, list) and len(ov) > 0 and any(len(str(s)) > 0 for s in ov)
            evidence = f"overview has {len(ov)} items" if passed else "overview missing or empty"

        elif name == "deductions_have_evidence_turns":
            total_d = 0
            with_turns = 0
            sections = g.get("sections", {})
            for sec_data in sections.values():
                for cdata in sec_data.get("criteria", {}).values():
                    for d in cdata.get("deductions", []):
                        total_d += 1
                        et = d.get("evidence_turns", [])
                        if et and all(1 <= t <= 10 for t in et):
                            with_turns += 1
            if total_d == 0:
                passed = True
                evidence = "No deductions to check"
            else:
                passed = with_turns == total_d
                evidence = f"{with_turns}/{total_d} deductions have valid evidence_turns"

        elif name == "socratic_method_high_score":
            s = g.get("sections", {}).get("pedagogy", {}).get("criteria", {}).get("1.1", {}).get("score", -1)
            passed = s >= 10
            evidence = f"1.1 score = {s}"

        elif name == "assignment_anchoring_high":
            s = g.get("sections", {}).get("dialogue", {}).get("criteria", {}).get("2.2", {}).get("score", -1)
            passed = s >= 6
            evidence = f"2.2 score = {s}"

        elif name == "scaffolding_assessed":
            s = g.get("sections", {}).get("pedagogy", {}).get("criteria", {}).get("1.2", {}).get("score", -1)
            passed = s >= 0
            evidence = f"1.2 score = {s}"

        else:
            evidence = f"Unknown assertion: {name}"

        results["expectations"].append({"text": name, "passed": passed, "evidence": evidence})

    return results


evals = ["chaotic-boundary-testing", "chitchat-off-topic", "clueless-scaffolding"]

for ev in evals:
    meta_path = os.path.join(BASE, ev, "eval_metadata.json")
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)
    assertions = meta["assertions"]

    for run_type in ["with_skill", "without_skill"]:
        grade_path = os.path.join(BASE, ev, run_type, "outputs", "grade.json")
        if not os.path.exists(grade_path):
            print(f"SKIP: {ev}/{run_type} (no grade.json)")
            continue
        result = grade_run(grade_path, assertions, ev, run_type)
        out_path = os.path.join(BASE, ev, run_type, "grading.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        passed = sum(1 for e in result["expectations"] if e["passed"])
        total = len(result["expectations"])
        print(f"{ev}/{run_type}: {passed}/{total} assertions passed")
