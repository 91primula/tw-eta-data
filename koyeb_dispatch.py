"""Request the existing GitHub workflow daily at 09:10 Asia/Seoul."""
import argparse
import json
import os
import time
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def next_run(now):
    target = now.replace(hour=9, minute=00, second=0, microsecond=0)
    return target if target > now else target + timedelta(days=1)


def dispatch():
    token = os.environ["GITHUB_TOKEN"]
    request = Request(
        "https://api.github.com/repos/91primula/tw-eta-data/"
        "actions/workflows/eta.yml/dispatches",
        data=json.dumps({"ref": "main"}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "tw-eta-koyeb-scheduler",
        },
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        if response.status not in (200, 204):
            raise RuntimeError(f"Unexpected GitHub status: {response.status}")
    print("GitHub Action 실행 요청 성공. 수집 결과는 GitHub Actions에서 확인하세요.", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="실행 요청을 한 번 보내고 종료")
    args = parser.parse_args()
    if not os.environ.get("GITHUB_TOKEN"):
        raise SystemExit("Koyeb 환경변수 GITHUB_TOKEN이 필요합니다.")
    if args.once:
        dispatch()
        return
    while True:
        target = next_run(datetime.now(KST))
        print(f"다음 실행 요청: {target.isoformat()}", flush=True)
        while datetime.now(KST) < target:
            time.sleep(min(30, max(0, (target - datetime.now(KST)).total_seconds())))
        try:
            dispatch()
        except HTTPError as error:
            print(f"GitHub 요청 실패: HTTP {error.code}. 토큰 권한·만료·워크플로를 확인하세요.", flush=True)
        except (URLError, TimeoutError, OSError, RuntimeError) as error:
            # Do not retry ambiguous POST failures: GitHub may have accepted it.
            print(f"실행 요청 확인 실패: {type(error).__name__}. GitHub Actions를 확인하세요.", flush=True)


if __name__ == "__main__":
    main()
