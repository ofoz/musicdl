import json
import requests

def test_webui():
    base_url = 'http://127.0.0.1:5050'
    
    # 1. Test index page
    r = requests.get(f'{base_url}/')
    assert r.status_code == 200, f'Index error: {r.status_code}'
    print('[Pass] GET / returned 200 OK')

    # 2. Test api/sources
    r = requests.get(f'{base_url}/api/sources')
    assert r.status_code == 200
    data = r.json()
    sources = data.get('sources', [])
    print(f'[Pass] GET /api/sources returned {len(sources)} sources')

    # 3. Test SSE search stream (KuwoMusicClient)
    print('Testing SSE search stream with KuwoMusicClient...')
    r = requests.get(f'{base_url}/api/search/stream?q=稻香&sources=KuwoMusicClient', stream=True, timeout=15)
    got_result = False
    sample_token = None
    for line in r.iter_lines():
        if line:
            decoded = line.decode('utf-8', errors='ignore')
            if decoded.startswith('data:') and 'token' in decoded:
                payload = json.loads(decoded[5:].strip())
                print(f"[Pass] Received stream track: {payload.get('song_name')} - {payload.get('singers')} (Token: {payload.get('token')})")
                sample_token = payload.get('token')
                got_result = True
                break

    assert got_result, 'Failed to get stream search result'

    # 4. Test stream proxy Range request
    if sample_token:
        headers = {'Range': 'bytes=0-1023'}
        stream_r = requests.get(f'{base_url}/api/stream/{sample_token}', headers=headers, timeout=10)
        print(f"[Pass] Audio Range proxy returned: status={stream_r.status_code}, content-type={stream_r.headers.get('Content-Type')}, bytes={len(stream_r.content)}")
        assert stream_r.status_code in (200, 206), f'Audio stream error: {stream_r.status_code}'

    print('\n=============================================')
    print(' ALL WebUI End-to-End Tests Passed Successfully!')
    print('=============================================')

if __name__ == '__main__':
    test_webui()
