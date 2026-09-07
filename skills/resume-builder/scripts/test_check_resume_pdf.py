"""Synthetic PDF checks; contains no applicant data. Requires PyMuPDF."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import fitz


class CheckResumePdfTests(unittest.TestCase):
    def test_visible_clickable_and_production_notes(self):
        url = 'https://example.com/project'
        with tempfile.TemporaryDirectory() as tmp:
            pdf = Path(tmp) / 'fixture.pdf'
            with fitz.open() as doc:
                page = doc.new_page()
                page.insert_text((40, 40), url)
                page.insert_text((40, 70), 'INTERNAL NOTE')
                page.insert_link({'kind': fitz.LINK_URI, 'from': fitz.Rect(40, 25, 240, 45), 'uri': url})
                doc.save(pdf)
            cmd = [sys.executable, str(Path(__file__).with_name('check_resume_pdf.py')), str(pdf)]
            for args, code, field in [
                (['--expect-url', url], 0, None),
                (['--expect-url', 'https://example.com/missing'], 2, 'missing_visible_urls'),
                (['--forbid-text', 'INTERNAL NOTE'], 2, 'forbidden_text_found'),
                (['--expect-pages', '2'], 2, None),
            ]:
                result = subprocess.run(cmd + args, capture_output=True, text=True)
                self.assertEqual(result.returncode, code, result.stderr)
                report = json.loads(result.stdout)
                if field:
                    self.assertTrue(report[field])
            # Clickable label alone is insufficient for a printed URL requirement.
            with fitz.open() as doc:
                page = doc.new_page()
                page.insert_text((40, 40), 'Project repository')
                page.insert_link({'kind': fitz.LINK_URI, 'from': fitz.Rect(40, 25, 240, 45), 'uri': url})
                doc.save(pdf)
            result = subprocess.run(cmd + ['--expect-url', url], capture_output=True, text=True)
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(report['missing_visible_urls'], [url])
            self.assertEqual(report['missing_clickable_urls'], [])


if __name__ == '__main__':
    unittest.main()
