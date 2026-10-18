'''
Function:
    Automated verification script for musicdl sources
Author:
    Pair Programming Assistant
Usage:
    python tests/verify_sources.py [--quick] [--keyword KEYWORD] [--sources SOURCE1,SOURCE2]
'''
import os
import sys
import time
import argparse
from typing import Dict, List, Any

# Ensure UTF-8 output on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import requests
from musicdl.modules.sources import MusicClientBuilder, BuildMusicClient
from musicdl.modules.utils import SongInfo


# Core domestic platforms
CORE_DOMESTIC_SOURCES = [
    'NeteaseMusicClient',
    'QQMusicClient',
    'KuwoMusicClient',
    'KugouMusicClient',
    'MiguMusicClient',
    'BilibiliMusicClient',
]

# Extended common platforms
EXTENDED_SOURCES = [
    'BodianMusicClient',
    'SodaMusicClient',
    'GDStudioMusicClient',
    'MyFreeMP3MusicClient',
    'GequbaoMusicClient',
    'JamendoMusicClient',
    'SoundCloudMusicClient',
]


def test_single_source(source_name: str, keyword: str, timeout: int = 15) -> Dict[str, Any]:
    """Test a single music client for search & download url availability."""
    start_time = time.time()
    result = {
        'source': source_name,
        'status': 'UNKNOWN',
        'count': 0,
        'has_download_url': False,
        'sample_song': '',
        'time_cost': 0.0,
        'error': '',
    }
    
    if source_name not in MusicClientBuilder.REGISTERED_MODULES:
        result['status'] = 'NOT_REGISTERED'
        result['error'] = 'Client name not registered in MusicClientBuilder'
        return result

    try:
        client = BuildMusicClient(module_cfg={
            'type': source_name,
            'search_size_per_source': 3,
            'disable_print': True,
            'max_retries': 2,
        })
        
        # Perform search
        search_results: List[SongInfo] = client.search(keyword=keyword)
        time_cost = time.time() - start_time
        result['time_cost'] = round(time_cost, 2)
        
        if not search_results:
            result['status'] = 'EMPTY'
            result['error'] = 'No search results returned'
            return result
            
        result['count'] = len(search_results)
        sample = search_results[0]
        result['sample_song'] = f"{sample.song_name} - {sample.singers}"
        
        # Check download URL
        has_url = bool(sample.download_url and str(sample.download_url).startswith(('http://', 'https://')))
        result['has_download_url'] = has_url
        
        if has_url:
            result['status'] = 'SUCCESS'
        else:
            result['status'] = 'NO_URL'
            result['error'] = 'Search returned songs but download_url is missing or empty'
            
    except Exception as e:
        result['time_cost'] = round(time.time() - start_time, 2)
        result['status'] = 'ERROR'
        result['error'] = f"{type(e).__name__}: {str(e)[:120]}"
        
    return result


def main():
    parser = argparse.ArgumentParser(description="Verify musicdl sources availability.")
    parser.add_argument('--keyword', '-k', default='周杰伦', help="Search keyword for testing")
    parser.add_argument('--sources', '-s', default=None, help="Comma-separated list of sources to test")
    parser.add_argument('--quick', '-q', action='store_true', help="Only test core domestic sources")
    parser.add_argument('--all', '-a', action='store_true', help="Test all registered sources")
    args = parser.parse_args()

    if args.sources:
        test_sources = [s.strip() for s in args.sources.split(',') if s.strip()]
    elif args.all:
        test_sources = list(MusicClientBuilder.REGISTERED_MODULES.keys())
    elif args.quick:
        test_sources = CORE_DOMESTIC_SOURCES
    else:
        test_sources = CORE_DOMESTIC_SOURCES + EXTENDED_SOURCES

    print(f"\n=======================================================")
    print(f"  musicdl Sources Verification")
    print(f"  Keyword: '{args.keyword}' | Total Sources: {len(test_sources)}")
    print(f"=======================================================\n")

    results = []
    for idx, source in enumerate(test_sources, 1):
        print(f"[{idx}/{len(test_sources)}] Testing {source} ... ", end='', flush=True)
        res = test_single_source(source, keyword=args.keyword)
        if res['status'] == 'SUCCESS':
            print(f"OK ({res['count']} songs, sample: {res['sample_song']}, {res['time_cost']}s)")
        elif res['status'] == 'EMPTY':
            print(f"EMPTY (0 songs found, {res['time_cost']}s)")
        elif res['status'] == 'NO_URL':
            print(f"NO_URL ({res['count']} songs found but no download URL, {res['time_cost']}s)")
        else:
            print(f"FAILED ({res['error']}, {res['time_cost']}s)")
        results.append(res)

    print("\n" + "=" * 80)
    print("  Summary Report")
    print("=" * 80)
    print(f"{'Source':<26} | {'Status':<10} | {'Songs':<5} | {'URL?':<5} | {'Cost':<6} | {'Notes / Sample'}")
    print("-" * 80)
    for r in results:
        notes = r['sample_song'] if r['status'] == 'SUCCESS' else r['error']
        has_url_str = 'YES' if r['has_download_url'] else 'NO'
        print(f"{r['source']:<26} | {r['status']:<10} | {r['count']:<5} | {has_url_str:<5} | {r['time_cost']:<5}s | {notes[:40]}")
    print("=" * 80)


if __name__ == '__main__':
    main()
