"""
Unit Test Suite for Scorer V2 (regex_audit/scorer_v2.py).

Validates:
1. All 8 False Positives from baseline now correctly evaluate to FAIL.
2. All 10 False Negatives from baseline now correctly evaluate to PASS.
3. All 50 baseline True Positives continue to evaluate to PASS with zero regressions.
4. Standalone filter functions (matches_senior_title, requires_3_plus_years,
   matches_out_of_scope_role, is_relevant_jd) handle boundaries and edge cases correctly.
"""

import json
import os
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import regex_audit.scorer_v2 as scorer


DATASET_PATH = PROJECT_ROOT / "regex_audit" / "master_raw_dataset_2026-09-29.jsonl"
FP_PATH = PROJECT_ROOT / "regex_audit" / "evaluation" / "false_positives.jsonl"
FN_PATH = PROJECT_ROOT / "regex_audit" / "evaluation" / "false_negatives.jsonl"
L2_PASS_PATH = PROJECT_ROOT / "regex_audit" / "filter_results" / "layer2_regex_pass.jsonl"
GROUND_TRUTH_PATH = PROJECT_ROOT / "regex_audit" / "evaluation" / "ground_truth.jsonl"


def _load_jsonl(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class TestFalsePositives(unittest.TestCase):
    """Verifies that all 8 jobs that falsely passed in baseline now evaluate to FAIL."""

    @classmethod
    def setUpClass(cls):
        cls.raw_jobs = {j["job_index"]: j for j in _load_jsonl(DATASET_PATH)}
        cls.fps = _load_jsonl(FP_PATH)

    def test_all_8_false_positives_fail(self):
        self.assertEqual(len(self.fps), 8, "Expected exactly 8 false positives in dataset")

        for fp in self.fps:
            idx = fp["job_index"]
            job = self.raw_jobs[idx]
            title = job.get("title", "")
            desc = job.get("description", "")

            sn_title = scorer.matches_senior_title(title, desc)
            exp_req = scorer.requires_3_plus_years(desc)
            oos_role = scorer.matches_out_of_scope_role(title, desc)
            rel_jd = scorer.is_relevant_jd(desc, title)

            passed = (not sn_title) and (not exp_req) and (not oos_role) and rel_jd
            reasons = []
            if sn_title:
                reasons.append("matches_senior_title")
            if exp_req:
                reasons.append("requires_3_plus_years")
            if oos_role:
                reasons.append("matches_out_of_scope_role")
            if not rel_jd:
                reasons.append("not is_relevant_jd")

            self.assertFalse(
                passed,
                f"Job {idx} ('{title}') at '{job.get('company')}' should FAIL but passed Scorer V2!"
            )
            self.assertTrue(len(reasons) > 0, f"Job {idx} failed without attributed reason")

    def test_fp_job_336_albertsons_advanced_engineer(self):
        """Job 336: Advanced Engineer Quality hides senior tier -> rejected by matches_senior_title."""
        job = self.raw_jobs[336]
        self.assertTrue(
            scorer.matches_senior_title(job["title"], job["description"]),
            "Job 336 should be flagged as senior by matches_senior_title due to 'Advanced Engineer'"
        )

    def test_fp_job_456_accenture_career_level_7(self):
        """Job 456: Quality Engineer with Career Level 7 in description header -> rejected by matches_senior_title."""
        job = self.raw_jobs[456]
        self.assertTrue(
            scorer.matches_senior_title(job["title"], job["description"]),
            "Job 456 should be flagged as senior by matches_senior_title due to Career Level 7 / Quality Engineering Manager"
        )

    def test_fp_job_510_wissen_experience_range(self):
        """Job 510: Java Software Engineer with 'Required Experience: 2-5' -> rejected by requires_3_plus_years."""
        job = self.raw_jobs[510]
        self.assertTrue(
            scorer.requires_3_plus_years(job["description"]),
            "Job 510 should be rejected by requires_3_plus_years due to 'Required Experience: 2-5'"
        )

    def test_fp_job_513_infios_word_numeral_experience(self):
        """Job 513: Technical Consultant with 'At least five years' -> rejected by requires_3_plus_years."""
        job = self.raw_jobs[513]
        self.assertTrue(
            scorer.requires_3_plus_years(job["description"]),
            "Job 513 should be rejected by requires_3_plus_years due to 'At least five years'"
        )

    def test_fp_job_563_pwc_multiline_experience(self):
        """Job 563: IN_Associate_Saviynt with multi-line 'Years of Experience required:\n\n 4' -> rejected."""
        job = self.raw_jobs[563]
        self.assertTrue(
            scorer.requires_3_plus_years(job["description"]),
            "Job 563 should be rejected by requires_3_plus_years due to 'Years of Experience required: 4'"
        )

    def test_fp_job_752_amadeus_terminal_digit(self):
        """Job 752: Product Definition Analyst 3 with terminal digit '3' -> rejected by matches_senior_title."""
        job = self.raw_jobs[752]
        self.assertTrue(
            scorer.matches_senior_title(job["title"], job["description"]),
            "Job 752 should be rejected by matches_senior_title due to terminal digit '3'"
        )

    def test_fp_job_796_natwest_avp(self):
        """Job 796: Software Engineer, AVP with executive grade 'AVP' -> rejected by matches_senior_title."""
        job = self.raw_jobs[796]
        self.assertTrue(
            scorer.matches_senior_title(job["title"], job["description"]),
            "Job 796 should be rejected by matches_senior_title due to 'AVP'"
        )

    def test_fp_job_1038_azuga_candidate_skill_experience(self):
        """Job 1038: Fullstack Python Engineer requiring 'At least 3 years... with React' -> rejected."""
        job = self.raw_jobs[1038]
        self.assertTrue(
            scorer.requires_3_plus_years(job["description"]),
            "Job 1038 should be rejected by requires_3_plus_years (skill experience preserved, not stripped)"
        )


class TestFalseNegatives(unittest.TestCase):
    """Verifies that all 10 jobs that falsely failed in baseline now evaluate to PASS."""

    @classmethod
    def setUpClass(cls):
        cls.raw_jobs = {j["job_index"]: j for j in _load_jsonl(DATASET_PATH)}
        cls.fns = _load_jsonl(FN_PATH)

    def test_all_10_false_negatives_pass(self):
        self.assertEqual(len(self.fns), 10, "Expected exactly 10 false negatives in dataset")

        for fn in self.fns:
            idx = fn["job_index"]
            job = self.raw_jobs[idx]
            title = job.get("title", "")
            desc = job.get("description", "")

            sn_title = scorer.matches_senior_title(title, desc)
            exp_req = scorer.requires_3_plus_years(desc)
            oos_role = scorer.matches_out_of_scope_role(title, desc)
            rel_jd = scorer.is_relevant_jd(desc, title)

            passed = (not sn_title) and (not exp_req) and (not oos_role) and rel_jd
            failed_filters = []
            if sn_title:
                failed_filters.append("matches_senior_title")
            if exp_req:
                failed_filters.append("requires_3_plus_years")
            if oos_role:
                failed_filters.append("matches_out_of_scope_role")
            if not rel_jd:
                failed_filters.append("not is_relevant_jd")

            self.assertTrue(
                passed,
                f"Job {idx} ('{title}') at '{job.get('company')}' should PASS but was rejected by: {failed_filters}"
            )

    def test_fn_job_18_and_466_davies_company_growth(self):
        """Jobs 18 & 466: Associate QA Automation - company revenue growth ('ten years') stripped as boilerplate."""
        for idx in [18, 466]:
            job = self.raw_jobs[idx]
            self.assertFalse(
                scorer.requires_3_plus_years(job["description"]),
                f"Job {idx} company history should be stripped and not treated as candidate experience"
            )
            self.assertTrue(scorer.is_relevant_jd(job["description"], job["title"]))

    def test_fn_job_84_capgemini_jvm_kotlin(self):
        """Job 84: Java or Kotlin & React.js Developer - Kotlin as JVM backend language allowed."""
        job = self.raw_jobs[84]
        self.assertFalse(
            scorer.matches_out_of_scope_role(job["title"], job["description"]),
            "Job 84 Kotlin paired with Java should NOT be rejected as out-of-scope"
        )
        self.assertTrue(scorer.is_relevant_jd(job["description"], job["title"]))

    def test_fn_job_119_and_687_domex_age_bracket(self):
        """Jobs 119 & 687: ASP.Net MVC Developer - candidate age bracket '(27 to 40 Yrs)' ignored."""
        for idx in [119, 687]:
            job = self.raw_jobs[idx]
            self.assertFalse(
                scorer.requires_3_plus_years(job["description"]),
                f"Job {idx} candidate age bracket should NOT be matched as 27-40 years experience"
            )
            self.assertTrue(scorer.is_relevant_jd(job["description"], job["title"]))

    def test_fn_job_169_datastraw_fast_track_lead(self):
        """Job 169: Fast-Track to Tech Lead career growth subtitle masked from seniority filter."""
        job = self.raw_jobs[169]
        self.assertFalse(
            scorer.matches_senior_title(job["title"], job["description"]),
            "Job 169 'Fast-Track to Tech Lead' progression subtitle should NOT trigger seniority filter"
        )
        self.assertTrue(scorer.is_relevant_jd(job["description"], job["title"]))

    def test_fn_job_220_poppop_fullstack_flutter(self):
        """Job 220: Full Stack Developer Intern - peripheral Flutter framework in React/Node stack allowed."""
        job = self.raw_jobs[220]
        self.assertFalse(
            scorer.matches_out_of_scope_role(job["title"], job["description"]),
            "Job 220 peripheral Flutter in full-stack internship should NOT be rejected"
        )
        self.assertTrue(scorer.is_relevant_jd(job["description"], job["title"]))

    def test_fn_job_246_commando_mern_markdown(self):
        """Job 246: Full Stack Developer - MERN stack and escaped markdown full\\-stack recognized."""
        job = self.raw_jobs[246]
        self.assertTrue(
            scorer.is_relevant_jd(job["description"], job["title"]),
            "Job 246 MERN stack with escaped full\\-stack should be recognized as relevant"
        )

    def test_fn_job_722_scoutit_qa_salesforce(self):
        """Job 722: QA Engineer testing Salesforce SaaS product allowed."""
        job = self.raw_jobs[722]
        self.assertFalse(
            scorer.matches_out_of_scope_role(job["title"], job["description"]),
            "Job 722 QA role testing Salesforce should NOT be rejected as out-of-scope"
        )
        self.assertTrue(scorer.is_relevant_jd(job["description"], job["title"]))

    def test_fn_job_1027_dymatrix_company_heritage(self):
        """Job 1027: Full Stack (.NET/React) - company heritage ('With over 20 years') stripped."""
        job = self.raw_jobs[1027]
        self.assertFalse(
            scorer.requires_3_plus_years(job["description"]),
            "Job 1027 company heritage of 20 years should NOT be attributed to candidate"
        )
        self.assertTrue(scorer.is_relevant_jd(job["description"], job["title"]))


class TestBaselineTruePositives(unittest.TestCase):
    """Verifies that all 50 baseline True Positives continue to pass with zero regressions."""

    @classmethod
    def setUpClass(cls):
        cls.raw_jobs = {j["job_index"]: j for j in _load_jsonl(DATASET_PATH)}
        l2_pass = _load_jsonl(L2_PASS_PATH)
        gt_map = {r["job_index"]: r["expected_outcome"] for r in _load_jsonl(GROUND_TRUTH_PATH)}
        cls.baseline_tp_indices = [j["job_index"] for j in l2_pass if gt_map.get(j["job_index"]) == "PASS"]

    def test_all_50_baseline_true_positives_pass(self):
        self.assertEqual(len(self.baseline_tp_indices), 50, "Expected exactly 50 baseline True Positives")

        regressions = []
        for idx in self.baseline_tp_indices:
            job = self.raw_jobs[idx]
            title = job.get("title", "")
            desc = job.get("description", "")

            sn_title = scorer.matches_senior_title(title, desc)
            exp_req = scorer.requires_3_plus_years(desc)
            oos_role = scorer.matches_out_of_scope_role(title, desc)
            rel_jd = scorer.is_relevant_jd(desc, title)

            passed = (not sn_title) and (not exp_req) and (not oos_role) and rel_jd
            if not passed:
                failures = []
                if sn_title:
                    failures.append("matches_senior_title")
                if exp_req:
                    failures.append("requires_3_plus_years")
                if oos_role:
                    failures.append("matches_out_of_scope_role")
                if not rel_jd:
                    failures.append("not is_relevant_jd")
                regressions.append((idx, title, failures))

        self.assertEqual(
            len(regressions),
            0,
            f"Detected {len(regressions)} regressions on baseline True Positives: {regressions}"
        )


class TestStandaloneFunctionUnits(unittest.TestCase):
    """Fine-grained boundary and unit tests for individual standalone functions."""

    def test_senior_title_boundaries(self):
        # Senior / Management roles (should return True)
        self.assertTrue(scorer.matches_senior_title("Software Engineer, AVP"))
        self.assertTrue(scorer.matches_senior_title("Associate Vice President of Technology"))
        self.assertTrue(scorer.matches_senior_title("Product Definition Analyst 3"))
        self.assertTrue(scorer.matches_senior_title("Advanced Engineer Quality"))
        self.assertTrue(scorer.matches_senior_title("Lead Software Developer"))
        self.assertTrue(scorer.matches_senior_title("Principal QA Engineer"))
        self.assertTrue(scorer.matches_senior_title("Senior Backend Developer"))
        self.assertTrue(scorer.matches_senior_title("Software Engineer II"))
        self.assertTrue(scorer.matches_senior_title("Software Engineer 2 "))
        self.assertTrue(scorer.matches_senior_title("Software Engineer (4-6 years)"))

        # Entry-level / Progression roles (should return False)
        self.assertFalse(scorer.matches_senior_title("Software Engineer - AI & Product | Fast-Track to Tech Lead"))
        self.assertFalse(scorer.matches_senior_title("Junior Java Developer | Pathway to Lead"))
        self.assertFalse(scorer.matches_senior_title("Associate Software Engineer"))
        self.assertFalse(scorer.matches_senior_title("Graduate Engineer Trainee"))
        self.assertFalse(scorer.matches_senior_title("QA Intern"))
        self.assertFalse(scorer.matches_senior_title("Software Engineer (0-2 years)"))
        self.assertFalse(scorer.matches_senior_title("Backend Developer (1-3 yrs)"))

    def test_requires_3_plus_years_boundaries(self):
        # Requiring 3+ years (should return True)
        self.assertTrue(scorer.requires_3_plus_years("Required Experience: 2-5"))
        self.assertTrue(scorer.requires_3_plus_years("Required Experience: 3 to 6 years"))
        self.assertTrue(scorer.requires_3_plus_years("Years of Experience required:\n\n 4"))
        self.assertTrue(scorer.requires_3_plus_years("At least five years of experience in distributed systems."))
        self.assertTrue(scorer.requires_3_plus_years("At least 3 years of experience working with React."))
        self.assertTrue(scorer.requires_3_plus_years("Candidate must possess 4+ years of hands-on Java."))

        # Entry level / Boilerplate (should return False)
        self.assertFalse(scorer.requires_3_plus_years("Over the past ten years Davies has grown 20-fold."))
        self.assertFalse(scorer.requires_3_plus_years("With over 20 years of experience, DYMATRIX is a leader."))
        self.assertFalse(scorer.requires_3_plus_years("We are a team with 15 years experience in banking."))
        self.assertFalse(scorer.requires_3_plus_years("ASP.Net Developers (27 to 40 Yrs) Freshers welcome 1 to 2 years."))
        self.assertFalse(scorer.requires_3_plus_years("Candidate must have 0-2 years of experience."))
        self.assertFalse(scorer.requires_3_plus_years("Experience: 1-3 years in Python backend development."))
        self.assertFalse(scorer.requires_3_plus_years("Requires 3 years degree in Computer Science."))

    def test_matches_out_of_scope_role_scoping(self):
        # Out-of-scope titles (should return True)
        self.assertTrue(scorer.matches_out_of_scope_role("Salesforce Developer"))
        self.assertTrue(scorer.matches_out_of_scope_role("iOS Swift Engineer"))
        self.assertTrue(scorer.matches_out_of_scope_role("PHP Laravel Backend Developer"))
        self.assertTrue(scorer.matches_out_of_scope_role("Ruby on Rails Specialist"))

        # Context-scoped allowed roles (should return False)
        self.assertFalse(scorer.matches_out_of_scope_role("Java or Kotlin & React.js Developer", "Spring Boot microservices."))
        self.assertFalse(scorer.matches_out_of_scope_role("Quality Assurance Engineer", "Experience testing SaaS products such as Salesforce and Workday."))
        self.assertFalse(scorer.matches_out_of_scope_role("Full Stack Developer Intern", "Build modern apps with React, Node, Express; Flutter experience is a plus."))

    def test_is_relevant_jd_anchors_and_tools(self):
        # MERN Stack with markdown escaping
        mern_desc = "Develop full\\-stack web applications using React.js, Express, Node.js, and MongoDB with REST APIs."
        self.assertTrue(scorer.is_relevant_jd(mern_desc, "Full Stack Developer"))

        # AI / LLM / Agentic domain
        ai_desc = "Building agentic AI workflows, LLM fine-tuning, RAG pipelines with LangChain and Python FastAPI."
        self.assertTrue(scorer.is_relevant_jd(ai_desc, "AI Engineer"))

        # Word boundary protection for short abbreviations (ai vs maintain, ml vs html)
        non_ai_desc = "Must maintain high quality html and css code with git version control and send daily emails."
        self.assertFalse(scorer.is_relevant_jd(non_ai_desc, "Email Coordinator"))

    def test_remediated_type_guards_on_non_string_inputs(self):
        """Verify that all filter functions safely handle np.nan, float('nan'), None, and numeric inputs."""
        non_string_cases = [np.nan, float('nan'), None, 12345, pd.NA, "", "   "]
        for val in non_string_cases:
            self.assertFalse(scorer.matches_out_of_scope_role(val, val))
            self.assertFalse(scorer.is_relevant_jd(val, val))
            self.assertFalse(scorer.matches_senior_title(val, val))
            self.assertFalse(scorer.requires_3_plus_years(val))
        self.assertEqual(scorer.strip_boilerplate(np.nan), "")
        self.assertEqual(scorer.strip_boilerplate(None), "")
        self.assertEqual(scorer.strip_boilerplate(""), "")
        self.assertEqual(scorer.strip_boilerplate("   "), "   ")

    def test_remediated_match_keyword_case_normalization(self):
        """Verify case normalization for uppercase and mixed-case tokens in _match_keyword."""
        self.assertTrue(scorer._match_keyword("AI", "Generative AI solutions"))
        self.assertTrue(scorer._match_keyword("ai", "Generative AI solutions"))
        self.assertTrue(scorer._match_keyword("ML", "Machine Learning (ML)"))
        self.assertTrue(scorer._match_keyword("ml", "Machine Learning (ML)"))
        self.assertFalse(scorer._match_keyword("ai", "maintain customer claims"))
        self.assertFalse(scorer._match_keyword("ml", "write basic html emails"))
        self.assertTrue(scorer._match_keyword("Python", "Senior PYTHON Developer"))
        self.assertTrue(scorer._match_keyword(".net", "Looking for .NET developer"))
        self.assertTrue(scorer._match_keyword("c#", "Looking for C# backend"))
        self.assertFalse(scorer._match_keyword(None, "text"))
        self.assertFalse(scorer._match_keyword("text", None))
        self.assertFalse(scorer._match_keyword(np.nan, "text"))

    def test_remediated_precompiled_third_party_pattern(self):
        """Verify module-level precompiled third-party pattern existence and correct stripping."""
        self.assertTrue(hasattr(scorer, "THIRD_PARTY_PATTERN"))
        self.assertTrue(hasattr(scorer, "THIRD_PARTY_EXPERIENCE_PREFIXES"))
        # Verify third-party company experience is stripped without affecting candidate skill experience
        self.assertFalse(scorer.requires_3_plus_years("Our team has 15 years of experience in Java."))
        self.assertFalse(scorer.requires_3_plus_years("Over the past ten years Davies has grown 20-fold."))
        self.assertFalse(scorer.requires_3_plus_years("With over 20 years of experience, DYMATRIX is a leader."))
        self.assertTrue(scorer.requires_3_plus_years("Candidate must possess 4+ years of hands-on Java experience."))


if __name__ == "__main__":
    unittest.main()

