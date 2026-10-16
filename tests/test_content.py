import copy,importlib.util,json,pathlib,tempfile,unittest,hashlib
from PIL import Image
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('publish',ROOT/'scripts/publish.py');publish=importlib.util.module_from_spec(spec);spec.loader.exec_module(publish)
class ContentTest(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'card.example.json').read_text());self.folder=pathlib.Path(self.data['id']);self.counts=json.loads((ROOT/'surah-counts.json').read_text())
    def test_valid_metadata(self):publish.validate_metadata(self.data,self.folder,self.counts)
    def test_reference_past_last_ayah_is_rejected(self):
        self.data.update(surah=114,ayah=7)
        with self.assertRaises(AssertionError):publish.validate_metadata(self.data,self.folder,self.counts)
    def test_unlicensed_art_is_rejected(self):
        self.data['rights']['redistributionAllowed']=False
        with self.assertRaises(AssertionError):publish.validate_metadata(self.data,self.folder,self.counts)
    def test_path_traversal_is_rejected(self):
        self.data['image']='../other.png'
        with self.assertRaises(AssertionError):publish.validate_metadata(self.data,self.folder,self.counts)
    def test_overflow_mask_is_rejected(self):
        self.data['referenceMasks'][0]['width']=.9
        with self.assertRaises(AssertionError):publish.validate_metadata(self.data,self.folder,self.counts)
    def test_topics_are_rejected(self):
        self.data['topic']='example'
        with self.assertRaises(AssertionError):publish.validate_metadata(self.data,self.folder,self.counts)
    def test_empty_feed_can_be_published(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);(root/'cards').mkdir();(root/'surah-counts.json').write_text(json.dumps(self.counts));feed=publish.build(root,root/'site');self.assertEqual([],feed['cards']);self.assertEqual(1,feed['schemaVersion'])
    def test_photo_only_upload_preserves_original_bytes_and_reference(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);(root/'uploads').mkdir();(root/'cards').mkdir()
            (root/'surah-counts.json').write_text(json.dumps(self.counts))
            (root/'publisher.json').write_text(json.dumps({'rights':self.data['rights']}))
            source=root/'uploads/24-30-001.png';Image.new('RGB',(256,256),'white').save(source)
            original=source.read_bytes();feed=publish.build(root,root/'site');card=feed['cards'][0]
            self.assertEqual((24,30),(card['surah'],card['ayah']))
            self.assertEqual(original,(root/'site'/card['image']).read_bytes())
            self.assertEqual(hashlib.sha256(original).hexdigest(),card['sha256'])
    def test_photo_only_upload_requires_rights_confirmation(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);(root/'uploads').mkdir()
            Image.new('RGB',(256,256),'white').save(root/'uploads/24-30-001.png')
            (root/'publisher.json').write_text(json.dumps({'rights':{'redistributionAllowed':False}}))
            with self.assertRaises(AssertionError):publish.image_uploads(root)
if __name__=='__main__':unittest.main()
