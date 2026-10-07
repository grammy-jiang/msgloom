from dataclasses import replace
import unittest
from topic02_validation.fixtures import canonical_cases
from topic02_validation.representation import from_gold,round_trip

class RepresentationTests(unittest.TestCase):
    def _assert_matches_gold(self,c,r):
        self.assertEqual(r.case_id,c.case_id);self.assertEqual(r.text,c.text);self.assertEqual(r.topics,c.topics);self.assertEqual(r.spans,c.spans);self.assertEqual(r.topic_objects,c.topic_objects)
        self.assertEqual(len(r.assignments),len(c.memberships));self.assertEqual(len({a.assignment_id for a in r.assignments}),len(r.assignments))
        by_span={a.span_id:a for a in r.assignments}
        for m in c.memberships:
            a=by_span[m.span_id];self.assertEqual(a.assignment_id,f'assign:{c.case_id}:{m.span_id}');self.assertEqual(a.abstention_allowed,m.abstention_allowed)
            if m.required_topics:
                self.assertEqual(a.status,'resolved');self.assertEqual(a.topic_ids,tuple(sorted(m.required_topics)));self.assertFalse(a.alternative_topic_sets)
            elif m.alternative_topic_sets:
                self.assertEqual(a.status,'ambiguous');self.assertFalse(a.topic_ids);self.assertEqual(a.alternative_topic_sets,tuple(tuple(sorted(x)) for x in m.alternative_topic_sets))
            else:
                self.assertEqual(a.status,'abstained')
    def test_from_gold_matches_independent_fixture_fields(self):
        for c in canonical_cases():self._assert_matches_gold(c,from_gold(c))
    def test_decoded_round_trip_matches_independent_fixture_fields(self):
        for c in canonical_cases():self._assert_matches_gold(c,round_trip(c))
    def test_all_cases_round_trip_byte_canonically(self):
        for c in canonical_cases():self.assertEqual(from_gold(c).canonical_json(),round_trip(c).canonical_json())
    def test_noncontiguous_and_overlap_survive_round_trip(self):
        c=next(x for x in canonical_cases() if x.case_id=='noncontiguous-with-overlap');r=round_trip(c);atlas=next(o for o in r.topic_objects if o.topic_id=='ATLAS');self.assertEqual(atlas.span_ids,('a1','shared','a2'));a=next(x for x in r.assignments if x.span_id=='shared');self.assertEqual(set(a.topic_ids),{'ATLAS','BETA'})
    def test_ambiguity_survives_without_becoming_joint(self):
        c=next(x for x in canonical_cases() if x.case_id=='ambiguous-reference');r=round_trip(c);a=next(x for x in r.assignments if x.span_id=='amb');self.assertEqual(a.status,'ambiguous');self.assertFalse(a.topic_ids);self.assertEqual(len(a.alternative_topic_sets),2);self.assertTrue(a.abstention_allowed)
    def test_abstention_permission_changes_canonical_representation(self):
        c=next(x for x in canonical_cases() if x.case_id=='ambiguous-reference');m=c.memberships[0];self.assertTrue(m.abstention_allowed)
        changed=replace(c,memberships=(replace(m,abstention_allowed=False),)+c.memberships[1:]);changed.validate()
        a=from_gold(c);b=from_gold(changed)
        self.assertNotEqual(a.canonical_json(),b.canonical_json())
        self.assertTrue(next(x for x in a.assignments if x.span_id==m.span_id).abstention_allowed)
        self.assertFalse(next(x for x in b.assignments if x.span_id==m.span_id).abstention_allowed)
    def test_origin_and_kind_survive(self):
        c=next(x for x in canonical_cases() if x.case_id=='quoted-vs-authored');r=round_trip(c);sp={x.span_id:x for x in r.spans};self.assertEqual(sp['quoted-atlas'].origin,'quoted');self.assertEqual(sp['cfo'].kind,'approval_constraint')

if __name__=='__main__':unittest.main()
