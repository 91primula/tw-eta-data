import csv
import io
import os
from pathlib import Path

import requests

sheet_id = "1Ck1wo1UtZci5AzgEOz9XUEHHL8ofbTVds_arleiOT8s"
sheet_gid = "1271093552"

url = (
    f"https://docs.google.com/spreadsheets/d/{sheet_id}/export"
)

response = requests.get(
    url,
    params={
        "format": "csv",
        "gid": sheet_gid,
        "range": "A2:A",
    },
    timeout=30,
)
response.raise_for_status()

content_type = response.headers.get("Content-Type", "").lower()
text = response.content.decode("utf-8-sig")

# 비공개 시트의 로그인 페이지 등을 명단으로 저장하지 않음
if (
    "text/html" in content_type
    or text.lstrip().lower().startswith(("<!doctype html", "<html"))
):
    raise RuntimeError(
        "시트를 CSV로 읽을 수 없습니다. 공유 설정과 시트 ID를 확인하세요."
    )

nicknames = []
seen = set()

for row in csv.reader(io.StringIO(text)):
    if not row:
        continue

    nickname = row[0].strip()

    if nickname and nickname not in seen:
        seen.add(nickname)
        nicknames.append(nickname)

if not nicknames:
    raise RuntimeError(
        "A2부터 읽은 닉네임이 없습니다. 기존 명단은 유지합니다."
    )

output = Path("nicknames.txt")
temporary = Path("nicknames.txt.tmp")

temporary.write_text(
    "\n".join(nicknames) + "\n",
    encoding="utf-8",
)
temporary.replace(output)

print(f"구글시트에서 닉네임 {len(nicknames)}개 동기화 완료")
