"""Validate uploads and build an atomic GitHub Pages publication."""
import argparse,datetime,hashlib,json,pathlib,re,shutil,subprocess
from PIL import Image

ROOT=pathlib.Path(__file__).resolve().parents[1]
ALLOWED={'id','title','surah','ayah','image','publishedAt','rights','maskColor','referenceMasks','previewMasks','appMasks','order'}
def validate_metadata(data,folder,counts):
    assert isinstance(data,dict) and set(data)<=ALLOWED,'Unknown metadata fields; topics/categories are not supported'
    if 'order' in data:assert type(data['order']) is int and 1<=data['order']<=2_147_483_647,'Order must be a positive whole number'
    card_id=data['id'];assert isinstance(card_id,str) and re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}',card_id) and card_id==folder.name,'ID must match folder'
    assert isinstance(data['title'],str) and 1<=len(data['title'].strip())<=200
    s,a=data['surah'],data['ayah'];assert type(s)==int and type(a)==int and 1<=s<=114 and 1<=a<=counts[s-1],'Invalid Qur’an reference'
    filename=data['image'];assert re.fullmatch(r'[a-zA-Z0-9_.-]+\.(png|jpg|jpeg|webp)',filename) and '..' not in filename
    published=datetime.datetime.fromisoformat(data['publishedAt'].replace('Z','+00:00'));assert published.tzinfo is not None,'Publication date needs a timezone'
    rights=data['rights'];assert rights.get('redistributionAllowed') is True and rights.get('owner') and rights.get('license'),'Explicit artwork redistribution rights are required'
    assert re.fullmatch(r'#[a-fA-F0-9]{6}',data.get('maskColor','#ffffff'))
    for key in ('referenceMasks','previewMasks','appMasks'):
        masks=data.get(key,[]);assert isinstance(masks,list) and len(masks)<=8
        for m in masks:
            assert set(m)=={'left','top','width','height'}
            l,t,w,h=[m[k] for k in ('left','top','width','height')]
            assert all(type(v) in (int,float) and 0<=v<=1 for v in (l,t,w,h)) and w>0 and h>0 and l+w<=1.00001 and t+h<=1.00001,'Mask lies outside the square'
    return published

def image_uploads(root):
    uploads=sorted(p for p in (root/'uploads').glob('*') if p.suffix.lower() in ('.jpg','.jpeg','.png','.webp'))
    if not uploads:return []
    settings=json.loads((root/'publisher.json').read_text())
    rights=settings['rights']
    assert rights.get('redistributionAllowed') is True and rights.get('owner') and rights.get('license'), 'Complete the one-time artwork rights in publisher.json before uploading photos'
    result=[]
    for source in uploads:
        match=re.fullmatch(r'([1-9][0-9]{0,2})-([1-9][0-9]{0,2})-([a-z0-9][a-z0-9-]{0,59})',source.stem)
        assert match, 'Name each upload SURAH-AYAH-ID.jpg, for example 24-30-001.jpg'
        date=subprocess.run(['git','log','-1','--format=%aI','--',str(source.relative_to(root))],cwd=root,capture_output=True,text=True).stdout.strip()
        if not date:date=datetime.datetime.fromtimestamp(source.stat().st_mtime,datetime.timezone.utc).isoformat()
        s,a=int(match[1]),int(match[2]);card_id=source.stem
        data={'id':card_id,'title':f'Qur’an {s}:{a}','surah':s,'ayah':a,'image':source.name,'publishedAt':date,'rights':rights}
        for key in ('maskColor','referenceMasks','previewMasks','appMasks'):
            if key in settings:data[key]=settings[key]
        result.append((data,root/'cards'/card_id,source))
    return result

def assign_order(cards,overrides,previous):
    assert isinstance(overrides,dict),'order.json must contain a card-ID to number object'
    ids={c['id'] for c in cards}
    assert set(overrides)<=ids,'order.json contains an unknown card ID'
    for value in overrides.values():
        assert type(value) is int and 1<=value<=2_147_483_647,'Order must be a positive whole number'
    prior={c['id']:c for c in previous.get('cards',[])}
    used={}
    for card in cards:
        number=overrides.get(card['id'],card.get('order',prior.get(card['id'],{}).get('order')))
        if number is not None:
            assert type(number) is int and 1<=number<=2_147_483_647,'Invalid previous or explicit order'
            assert number not in used,f'Duplicate order number {number}; use a unique number per card'
            used[number]=card['id'];card['order']=number
    next_number=max(used,default=0)
    for card in sorted(cards,key=lambda c:(c['publishedAt'],c['id'])):
        if 'order' not in card:
            next_number+=1;assert next_number<=2_147_483_647
            card['order']=next_number
    cards.sort(key=lambda c:(c['order'],c['publishedAt'],c['id']))

def build(root,output,previous=None):
    counts=json.loads((root/'surah-counts.json').read_text());assert len(counts)==114
    output.mkdir(parents=True,exist_ok=True);cards=[]
    records=[]
    for metadata in sorted((root/'cards').glob('*/card.json')):
        assert not metadata.is_symlink()
        data=json.loads(metadata.read_text(encoding='utf-8'))
        records.append((data,metadata.parent,metadata.parent/data['image']))
    records+=image_uploads(root)
    seen=set()
    for data,folder,source in records:
        published=validate_metadata(data,folder,counts)
        assert data['id'] not in seen,'Duplicate card ID'
        seen.add(data['id'])
        data['publishedAt']=published.astimezone(datetime.timezone.utc).isoformat().replace('+00:00','Z')
        assert source.is_file() and not source.is_symlink() and source.stat().st_size<=20_000_000,'Missing or oversized image'
        with Image.open(source) as image:
            assert image.width==image.height and 256<=image.width<=8192,'Upload a complete square image (256–8192 px)'
            assert getattr(image,'n_frames',1)==1,'Animated image not supported'
            assert image.format=={'.jpg':'JPEG','.jpeg':'JPEG','.png':'PNG','.webp':'WEBP'}[source.suffix.lower()],'Image extension does not match its format'
            image.verify()
        sha=hashlib.sha256(source.read_bytes()).hexdigest();destination=output/'cards'/data['id']/(sha+source.suffix.lower());destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
        data['image']=destination.relative_to(output).as_posix();data['sha256']=sha;cards.append(data)
    # Prevent accidental extra image uploads from silently being published or ignored.
    declared={source.resolve() for _,_,source in records}
    for image in (root/'cards').rglob('*'):
        if image.is_file() and image.suffix.lower() in ('.png','.jpg','.jpeg','.webp'):assert image.resolve() in declared,'An image has no paired card.json'
    orderfile=root/'order.json'
    assign_order(cards,json.loads(orderfile.read_text()) if orderfile.exists() else {},previous or {})
    canonical=json.dumps(cards,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    manifest={'schemaVersion':1,'revision':hashlib.sha256(canonical).hexdigest(),'cards':cards}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'.nojekyll').write_text('')
    if (root/'public').is_dir():shutil.copytree(root/'public',output,dirs_exist_ok=True)
    (output/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Quranflect content</title><body><h1>Quranflect</h1><p>Swipe, Read, Reflect</p><p>Public card feed for the Quranflect Android app.</p><a href="manifest.json">Content manifest</a></body></html>')
    print(f'Validated {len(cards)} cards. Revision {manifest["revision"]}')
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,default=ROOT/'site');p.add_argument('--previous',type=pathlib.Path);a=p.parse_args();build(ROOT,a.output,json.loads(a.previous.read_text()) if a.previous else {})


