import importlib.util,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('publish',ROOT/'scripts/publish.py');p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
def cards():return [{'id':i,'publishedAt':'2026-10-27T10:00:00Z'} for i in ['a','b','c']]
class OrderTest(unittest.TestCase):
 def test_explicit_order_controls_one_batch(self):
  c=cards();p.assign_order(c,{'a':30,'b':10,'c':20},{})
  self.assertEqual(['b','c','a'],[x['id'] for x in c])
  self.assertEqual(['a','c','b'],[x['id'] for x in reversed(c)])
 def test_existing_numbers_survive_and_new_cards_append(self):
  old=cards();p.assign_order(old,{},{});c=cards()+[{'id':'0-new','publishedAt':'2026-10-27T10:00:00Z'}]
  p.assign_order(c,{}, {'cards':old})
  self.assertEqual([1,2,3,4],[x['order'] for x in c]);self.assertEqual('0-new',c[-1]['id'])
 def test_bad_numbers_rejected(self):
  for overrides in ({'a':True},{'a':0},{'a':1.5},{'a':1,'b':1},{'missing':5}):
   with self.subTest(overrides=overrides),self.assertRaises(AssertionError):p.assign_order(cards(),overrides,{})
if __name__=='__main__':unittest.main()
