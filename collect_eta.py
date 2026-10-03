import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

SERVER_CODE = 7  # 하이아칸 7 / 네냐플 16
URL = "https://tales.nexon.com/Community/Ranking/EtaRank"

CHARACTERS = [
    "루시안", "보리스", "막시민", "시벨린", "조슈아",
    "란지에", "이자크", "밀라", "티치엘", "이스핀",
    "나야트레이", "아나이스", "클로에", "벤야", "이솔렛",
    "로아미니", "녹턴", "리체", "예프넨",
]
CHARACTER_CODES = {
    name: code for code, name in enumerate(CHARACTERS)
}


def fetch_character(session, nickname):
    response = session.get(
        URL,
        params={
            "sc": SERVER_CODE,
            "cc": 99,
            "page": 1,
            "search": nickname,
        },
        timeout=30,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    blocked_messages = [
        "Enable JavaScript and cookies",
        "보안 검사를 진행",
    ]

    if any(message in page_text for message in blocked_messages):
        raise RuntimeError(
            "넥슨 보안 검사에 막혔습니다. 기존 JSON은 유지합니다."
        )

    # 정상 랭킹 페이지인지 확인
    if (
        soup.select_one(".col_rank") is None
        and "Last Update" not in page_text
    ):
        raise RuntimeError(
            "정상 랭킹 페이지를 확인할 수 없습니다. "
            "보안 차단 또는 HTML 구조 변경 가능성이 있습니다."
        )

    for row in soup.select("tr"):
        name_element = row.select_one(".nickname")

        if name_element is None:
            continue

        found_name = name_element.get_text(strip=True)

        # 검색 결과 중 닉네임 완전 일치만 사용
        if found_name != nickname:
            continue

        character_element = row.select_one(".charname")
        level_element = row.select_one(".col_level")

        if character_element is None or level_element is None:
            raise RuntimeError("랭킹 HTML 구조가 변경되었습니다.")

        character = character_element.get_text(strip=True)
        level = int(
            level_element.get_text(strip=True).replace(",", "")
        )

        # 캐릭터 코드가 맞는지 확인
        if character not in CHARACTER_CODES:
            raise RuntimeError(
                f"알 수 없는 캐릭터 이름: {character}"
            )

        return {
            "ServerCode": SERVER_CODE,
            "CharacterCode": CHARACTER_CODES[character],
            "Character": character,
            "UserId": found_name,
            "Level": level,
        }

    return None


def main():
    nicknames = list(dict.fromkeys(
        line.strip()
        for line in Path("nicknames.txt")
        .read_text(encoding="utf-8-sig")
        .splitlines()
        if line.strip()
    ))

    if not nicknames:
        raise RuntimeError("nicknames.txt에 닉네임을 입력하세요.")

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/145.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9",
    })

    rankings = []
    not_found = []

    for index, nickname in enumerate(nicknames):
        if index:
            time.sleep(2)

        item = fetch_character(session, nickname)

        if item is None:
            not_found.append(nickname)
            print(f"조회 안 됨: {nickname}")
        else:
            rankings.append(item)
            print(
                f"조회 성공: {nickname} / "
                f"{item['Character']} / 에타 {item['Level']}"
            )

    # 전부 조회 실패했을 때 기존 데이터를 덮어쓰지 않음
    if not rankings:
        raise RuntimeError(
            "조회된 캐릭터가 없습니다. 기존 JSON은 유지합니다."
        )

    payload = {
        "CollectDate": datetime.now(
            ZoneInfo("Asia/Seoul")
        ).strftime("%Y-%m-%d %H:%M:%S"),
        "Rankings": rankings,
        "NotFound": not_found,
    }

    # 모든 요청이 끝난 뒤에만 결과 교체
    output = Path("eta_ranking.json")
    temporary = Path("eta_ranking.json.tmp")

    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)

    print(f"저장 완료: {len(rankings)}명")


if __name__ == "__main__":
    main()
