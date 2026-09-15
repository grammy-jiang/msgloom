import unittest

from topic01_validation.detection import reuse_augmented_spans
from topic01_validation.extraction import extract_body
from topic01_validation.fixtures import canonical_cases


class DetectionComparatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {c.case_id: c for c in canonical_cases()}

    def _augmented(self, case_id, message_id):
        case = self.cases[case_id]
        message = case.message(message_id)
        body = extract_body(message.raw_rfc822)
        sources = tuple(m.expected_text for m in case.messages if m.message_id != message_id)
        return body, reuse_augmented_spans(body.text, body.quote_spans, sources)

    def test_reuse_augmented_finds_markerless_copy(self):
        _, spans = self._augmented("markerless-copy", "markerless-reply")
        self.assertTrue(spans)

    def test_reuse_augmented_finds_forwarded_text(self):
        _, spans = self._augmented("forwarded-message-block", "forward-wrapper")
        self.assertTrue(spans)

    def test_reuse_augmented_has_boilerplate_false_positive_negative_control(self):
        _, spans = self._augmented("boilerplate-reuse-not-quotation", "reuse-boiler-new")
        self.assertTrue(spans, "negative control must expose the precision cost of exact reuse detection")


if __name__ == "__main__":
    unittest.main()
