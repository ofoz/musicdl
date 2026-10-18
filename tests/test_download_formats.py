import json
import requests

def test_download_formats():
    base_url = 'http://127.0.0.1:5050'

    print("1. Searching track to obtain token...")
    r = requests.get(f'{base_url}/api/search/stream?q=稻香&sources=KuwoMusicClient', stream=True, timeout=15)
    sample_token = None
    sample_song = None
    for line in r.iter_lines():
        if line:
            decoded = line.decode('utf-8', errors='ignore')
            if decoded.startswith('data:') and 'token' in decoded:
                payload = json.loads(decoded[5:].strip())
                sample_token = payload.get('token')
                sample_song = payload.get('song_name')
                break

    assert sample_token, "Failed to get track token from search"
    print(f"[Pass] Got track: '{sample_song}', Token: {sample_token}")

    # 2. Test original download
    print("\n2. Testing format=original download...")
    orig_res = requests.get(f'{base_url}/api/stream/{sample_token}?download=1&format=original', timeout=15)
    assert orig_res.status_code == 200, f"Original download failed: {orig_res.status_code}"
    cd_orig = orig_res.headers.get('Content-Disposition', '')
    ct_orig = orig_res.headers.get('Content-Type', '')
    print(f"[Pass] Original format response: Content-Disposition={cd_orig}, Content-Type={ct_orig}, Size={len(orig_res.content)} bytes")

    # 3. Test mp3 transcoding download
    print("\n3. Testing format=mp3 transcoding download...")
    mp3_res = requests.get(f'{base_url}/api/stream/{sample_token}?download=1&format=mp3', timeout=20)
    assert mp3_res.status_code == 200, f"MP3 download failed: {mp3_res.status_code}"
    cd_mp3 = mp3_res.headers.get('Content-Disposition', '')
    ct_mp3 = mp3_res.headers.get('Content-Type', '')
    print(f"[Pass] MP3 format response: Content-Disposition={cd_mp3}, Content-Type={ct_mp3}, Size={len(mp3_res.content)} bytes")
    assert '.mp3' in cd_mp3.lower(), f"Expected .mp3 in filename, got: {cd_mp3}"
    assert 'audio/mpeg' in ct_mp3, f"Expected audio/mpeg, got: {ct_mp3}"

    # 4. Test wav transcoding download
    print("\n4. Testing format=wav transcoding download...")
    wav_res = requests.get(f'{base_url}/api/stream/{sample_token}?download=1&format=wav', timeout=20)
    assert wav_res.status_code == 200, f"WAV download failed: {wav_res.status_code}"
    cd_wav = wav_res.headers.get('Content-Disposition', '')
    ct_wav = wav_res.headers.get('Content-Type', '')
    print(f"[Pass] WAV format response: Content-Disposition={cd_wav}, Content-Type={ct_wav}, Size={len(wav_res.content)} bytes")
    assert wav_res.content.startswith(b'RIFF'), "WAV file does not start with RIFF header"
    assert '.wav' in cd_wav.lower(), f"Expected .wav in filename, got: {cd_wav}"

    print("\n=======================================================")
    print(" ALL Format Selection and Transcoding Tests Passed! ")
    print("=======================================================")

if __name__ == '__main__':
    test_download_formats()
