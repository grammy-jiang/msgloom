import unittest
from topic02_validation.end_to_end import PredictedTopicSpan,_greedy_match,evaluate_unit_assignment,predict_topic_spans
from topic02_validation.fixtures import canonical_cases
from topic02_validation.models import Span

class EndToEndTests(unittest.TestCase):
    def test_greedy_match_never_reuses_prediction(self):
        gold=(PredictedTopicSpan('g1',Span(0,10),'A','x'),PredictedTopicSpan('g2',Span(0,10),'A','x'))
        pred=(PredictedTopicSpan('p1',Span(0,10),'A','x'),)
        m=_greedy_match(gold,pred,min_iou=.5)
        self.assertEqual(len(m),1);self.assertEqual(len({pi for _,pi,_ in m}),1)
    def test_greedy_match_never_reuses_gold(self):
        gold=(PredictedTopicSpan('g1',Span(0,10),'A','x'),)
        pred=(PredictedTopicSpan('p1',Span(0,10),'A','x'),PredictedTopicSpan('p2',Span(0,10),'A','x'))
        m=_greedy_match(gold,pred,min_iou=.5)
        self.assertEqual(len(m),1);self.assertEqual(len({gi for gi,_,_ in m}),1)
    def test_extra_predicted_units_enter_precision_denominator(self):
        m=evaluate_unit_assignment(canonical_cases(),unit_kind='clause',mode='set_valued')
        self.assertGreater(m['false_positive_predicted_topic_spans'],0)
        self.assertLess(m['membership_span_iou50_precision']['value'],1.0)
    def test_exact_boundary_is_stricter_than_iou_recall(self):
        m=evaluate_unit_assignment(canonical_cases(),unit_kind='clause',mode='set_valued')
        self.assertLess(m['exact_boundary_match_recall']['value'],m['membership_span_iou50_recall']['value'])
    def test_noncontiguous_object_not_falsely_declared_solved(self):
        m=evaluate_unit_assignment(canonical_cases(),unit_kind='clause',mode='set_valued')
        self.assertLess(m['exact_noncontiguous_topic_objects']['value'],1.0)

if __name__=='__main__':unittest.main()
