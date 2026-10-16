"""FCM HTTP v1 sender. Credentials come only from a GitHub Actions secret."""
import argparse,datetime,json,os,pathlib,sys,time,urllib.request

def load_live(url):
    with urllib.request.urlopen(url,timeout=25) as r:return json.load(r)
def candidates(current,previous,frequency):
    if frequency=='weekly':
        cutoff=datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=7)
        return [c for c in current['cards'] if datetime.datetime.fromisoformat(c['publishedAt'].replace('Z','+00:00'))>=cutoff]
    previous_ids={c['id'] for c in previous.get('cards',[])}
    return [c for c in current['cards'] if c['id'] not in previous_ids]
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--previous',type=pathlib.Path);p.add_argument('--frequency',choices=['often','weekly'],default='often');p.add_argument('--dry-run',action='store_true');p.add_argument('--live-url',default='https://aj8787.github.io/Quranflect-Content/manifest.json');a=p.parse_args()
    current=json.loads(a.manifest.read_text());previous=json.loads(a.previous.read_text()) if a.previous and a.previous.exists() else {'cards':[]}
    cards=candidates(current,previous,a.frequency)
    if not cards:print('No new cards: no notification sent.');return
    # Do not notify until the exact publication is publicly retrievable.
    for attempt in range(6):
        try:
            live=load_live(a.live_url+'?revision='+current['revision'])
            if live['revision']==current['revision']:break
        except Exception:pass
        if attempt==5:raise RuntimeError('Pages revision is not live; no notification sent')
        time.sleep(5)
    credentials_json=os.environ.get('FIREBASE_SERVICE_ACCOUNT','')
    if not credentials_json:raise RuntimeError('Missing FIREBASE_SERVICE_ACCOUNT secret; content remains published')
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
    info=json.loads(credentials_json)
    credentials=service_account.Credentials.from_service_account_info(info,scopes=['https://www.googleapis.com/auth/firebase.messaging'])
    project=info['project_id']
    event_id=('weekly-'+datetime.date.today().strftime('%G-%V')) if a.frequency=='weekly' else 'publication-'+current['revision']
    payload={'validate_only':a.dry_run,'message':{'topic':'cards_'+a.frequency,'data':{'event_id':event_id,'frequency':a.frequency,'card_id':cards[-1]['id']},'android':{'priority':'high','ttl':'86400s','collapse_key':'quranflect_'+a.frequency}}}
    with AuthorizedSession(credentials) as session:
        response=session.post(f'https://fcm.googleapis.com/v1/projects/{project}/messages:send',json=payload,timeout=30)
        if not response.ok:raise RuntimeError(f'FCM rejected the request (HTTP {response.status_code}); check Firebase project and messaging IAM permission')
    print(('Validated, not sent' if a.dry_run else 'Sent')+f': {a.frequency}, {len(cards)} new cards, event {event_id}')
if __name__=='__main__':main()
