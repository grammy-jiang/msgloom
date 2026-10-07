import unittest

from topic01_validation.extraction import extract_body
from topic01_validation.fixtures import canonical_cases


class ExtractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {c.case_id: c for c in canonical_cases()}

    def test_reextracts_fixture_expected_text(self):
        for case in self.cases.values():
            for message in case.messages:
                with self.subTest(case=case.case_id, message=message.message_id):
                    self.assertEqual(extract_body(message.raw_rfc822).text, message.expected_text)

    def test_plain_gt_quote_detected(self):
        msg = self.cases["late-parent-arrival"].message("late-reply")
        body = extract_body(msg.raw_rfc822)
        self.assertEqual(len(body.quote_spans), 1)
        self.assertIn("Condition: Legal must sign off.", body.quote_spans[0].extract(body.text))

    def test_markerless_copy_is_not_detected_by_structural_baseline(self):
        msg = self.cases["markerless-copy"].message("markerless-reply")
        body = extract_body(msg.raw_rfc822)
        self.assertEqual(body.quote_spans, ())

    def test_html_blockquote_detected_and_table_value_preserved(self):
        msg = self.cases["html-table-nested"].message("html-reply")
        body = extract_body(msg.raw_rfc822)
        self.assertTrue(body.quote_spans)
        self.assertIn("AUD 50,000", body.text)
        self.assertTrue(any("AUD 50,000" in s.extract(body.text) for s in body.quote_spans))

    def test_multipart_alternative_prefers_plain_and_preserves_condition(self):
        msg = self.cases["mime-alternative-preservation"].messages[0]
        body = extract_body(msg.raw_rfc822)
        self.assertEqual(body.content_type, "text/plain")
        self.assertIn("Condition: CFO approval required.", body.text)

    def test_format_flowed_joins_same_depth(self):
        msg = self.cases["format-flowed"].messages[0]
        body = extract_body(msg.raw_rfc822)
        self.assertIn("> quoted line onecontinues here", body.text)
        self.assertEqual(len(body.quote_spans), 1)

    def test_forwarded_block_is_not_detected_by_simple_quote_baseline(self):
        msg = self.cases["forwarded-message-block"].message("forward-wrapper")
        body = extract_body(msg.raw_rfc822)
        self.assertEqual(body.quote_spans, ())
        self.assertIn("Decision: approve Gamma rollout.", body.text)

    def test_interleaved_reply_has_two_separate_quote_occurrences(self):
        msg = self.cases["interleaved-inline-reply"].message("inline-reply")
        body = extract_body(msg.raw_rfc822)
        self.assertEqual(len(body.quote_spans), 2)
        self.assertIn("Yes for Alpha.", body.text)
        self.assertIn("No for Beta.", body.text)


if __name__ == "__main__":
    unittest.main()
