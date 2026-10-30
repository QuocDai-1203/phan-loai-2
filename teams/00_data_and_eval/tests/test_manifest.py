"""Tests for scripts/build_manifest.py and its outputs.

Run (from the repo root):
    .venv\\Scripts\\python.exe -X utf8 teams\\00_data_and_eval\\tests\\test_manifest.py
or with pytest:
    .venv\\Scripts\\python.exe -X utf8 -m pytest teams/00_data_and_eval/tests

Tests that read data/manifest.csv need `scripts/build_manifest.py` to have been run first.
"""
import csv
import hashlib
import sys
import tempfile
import unicodedata
import unittest
from collections import Counter
from pathlib import Path

import fitz

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))
import build_manifest as bm  # noqa: E402

MANIFEST = REPO / "data" / "manifest.csv"
GROUPS = REPO / "data" / "duplicate_groups.csv"
EXPECTED_ROWS = 336


def read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


class DocIdFormula(unittest.TestCase):
    def test_formula_is_stable(self):
        rel = "10. GCN VC HNH/15. GCN VC HNH Dong (12-5-24).pdf"
        self.assertEqual(bm.make_doc_id(rel), hashlib.sha1(rel.encode("utf-8")).hexdigest()[:12])
        self.assertEqual(len(bm.make_doc_id(rel)), 12)
        # frozen value: if this changes, every downstream join on doc_id breaks
        self.assertEqual(bm.make_doc_id("a/b.pdf"), hashlib.sha1(b"a/b.pdf").hexdigest()[:12])
        self.assertEqual(bm.make_doc_id("a/b.pdf"), "55addc42a4ee")

    def test_nfc_and_forward_slashes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sub = root / unicodedata.normalize("NFD", "_Biên bản giao nhận 2026")
            sub.mkdir()
            f = sub / unicodedata.normalize("NFD", "bbgn-ă.pdf")
            f.write_bytes(b"x")
            rel = bm.norm_rel(f, root)
            self.assertEqual(rel, unicodedata.normalize("NFC", "_Biên bản giao nhận 2026/bbgn-ă.pdf"))
            self.assertNotIn("\\", rel)


class SyntheticBuild(unittest.TestCase):
    """End to end on three tiny generated PDFs: two byte-identical copies in different folders."""

    @staticmethod
    def _pdf(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 100), text, fontsize=14)
        doc.save(path, deflate=False, garbage=0)
        doc.close()

    def test_duplicates_and_idempotence(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            samples = d / "samples"
            body = "HOP DONG MUA BAN " + "noi dung dai " * 30
            self._pdf(samples / "A" / "one.pdf", body)
            (samples / "B").mkdir()
            (samples / "B" / "copy.pdf").write_bytes((samples / "A" / "one.pdf").read_bytes())
            self._pdf(samples / "B" / "other.pdf", "BIEN BAN GIAO NHAN khac hoan toan " + "xyz " * 60)
            outs = []
            for k in range(2):
                m, g, s = d / f"m{k}.csv", d / f"g{k}.csv", d / f"s{k}.json"
                rc = bm.main(["--samples-dir", str(samples), "--out", str(m), "--groups-out", str(g),
                              "--stats-out", str(s), "--baseline", str(d / "none.jsonl")])
                self.assertEqual(rc, 0)
                outs.append((m.read_bytes(), g.read_bytes(), s.read_bytes()))
            self.assertEqual(outs[0], outs[1], "output must be deterministic / idempotent")
            self.assertTrue(outs[0][0].startswith(b"\xef\xbb\xbf"), "manifest must be UTF-8 with BOM")
            rows = read(d / "m0.csv")
            self.assertEqual([r["relative_path"] for r in rows], sorted(r["relative_path"] for r in rows))
            dup = [r for r in rows if r["near_dup_group"]]
            self.assertEqual({r["file_name"] for r in dup}, {"one.pdf", "copy.pdf"})
            self.assertTrue(all(r["dup_cross_label"] == "True" and r["dup_group_size"] == "2" for r in dup))
            self.assertEqual(len(read(d / "g0.csv")), 2)


@unittest.skipUnless(MANIFEST.exists(), "run scripts/build_manifest.py first")
class RealManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = read(MANIFEST)

    def test_row_count_and_unique_ids(self):
        self.assertEqual(len(self.rows), EXPECTED_ROWS)
        ids = [r["doc_id"] for r in self.rows]
        self.assertEqual(len(ids), len(set(ids)), "doc_id must be unique")
        self.assertEqual(len({r["relative_path"] for r in self.rows}), EXPECTED_ROWS)

    def test_doc_id_matches_formula_and_paths_are_nfc(self):
        for r in self.rows:
            rel = r["relative_path"]
            self.assertEqual(rel, unicodedata.normalize("NFC", rel))
            self.assertNotIn("\\", rel)
            self.assertEqual(r["doc_id"], hashlib.sha1(rel.encode("utf-8")).hexdigest()[:12])

    def test_sorted_and_bom(self):
        self.assertEqual([r["relative_path"] for r in self.rows], sorted(r["relative_path"] for r in self.rows))
        self.assertTrue(MANIFEST.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_every_group_has_at_least_two_members(self):
        for col in ("exact_dup_group", "near_dup_group", "template_group"):
            counts = Counter(r[col] for r in self.rows if r[col])
            self.assertTrue(counts, col)
            self.assertTrue(all(c >= 2 for c in counts.values()), f"{col}: group with a single member")
        size = Counter(r["near_dup_group"] for r in self.rows if r["near_dup_group"])
        for r in self.rows:
            if r["near_dup_group"]:
                self.assertEqual(int(r["dup_group_size"]), size[r["near_dup_group"]])
            else:
                self.assertEqual(r["dup_group_size"], "1")
                self.assertEqual(r["dup_cross_label"], "False")

    def test_exact_group_implies_same_sha_and_near_group(self):
        by = {}
        for r in self.rows:
            if r["exact_dup_group"]:
                by.setdefault(r["exact_dup_group"], []).append(r)
        for g, ms in by.items():
            self.assertEqual(len({m["sha256"] for m in ms}), 1, g)
            self.assertEqual(len({m["near_dup_group"] for m in ms}), 1, g)
            self.assertTrue(ms[0]["near_dup_group"], g)

    def test_cross_label_flag_matches_labels(self):
        by = {}
        for r in self.rows:
            if r["near_dup_group"]:
                by.setdefault(r["near_dup_group"], set()).add(r["folder_label"])
        for r in self.rows:
            if r["near_dup_group"]:
                self.assertEqual(r["dup_cross_label"] == "True", len(by[r["near_dup_group"]]) >= 2)

    def test_template_group_contains_whole_dup_group(self):
        tg = {}
        for r in self.rows:
            if r["near_dup_group"]:
                tg.setdefault(r["near_dup_group"], set()).add(r["template_group"])
        for g, s in tg.items():
            self.assertEqual(len(s), 1, g)
            self.assertNotIn("", s, g)

    def test_hashes_are_16_hex_and_scan_flag_bool(self):
        for r in self.rows:
            for col in ("page1_dhash", "last_page_dhash"):
                self.assertRegex(r[col], r"^[0-9a-f]{16}$")
            self.assertIn(r["is_scanned"], ("True", "False"))
            self.assertGreaterEqual(int(r["page_count"]), 1)
            self.assertLessEqual(int(r["pages_with_text_layer"]), int(r["page_count"]))

    def test_duplicate_groups_csv_consistent(self):
        g = read(GROUPS)
        n_dup = sum(1 for r in self.rows if r["near_dup_group"])
        self.assertEqual(len(g), n_dup)
        counts = Counter(x["near_dup_group"] for x in g)
        self.assertTrue(all(c >= 2 for c in counts.values()))
        ids = {r["doc_id"] for r in self.rows}
        self.assertTrue(all(x["doc_id"] in ids for x in g))


if __name__ == "__main__":
    unittest.main()
