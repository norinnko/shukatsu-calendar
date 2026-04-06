import os
import json
import re
from datetime import datetime
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()


def is_openai_available():
    return bool(OPENAI_API_KEY)


def get_client():
    return OpenAI(api_key=OPENAI_API_KEY)


def classify_intent(text: str) -> str:
    """
    多少の誤字やくだけた表現込みで意図分類
    """
    client = get_client()

    prompt = f"""
あなたはLINE就活カレンダーBotの意図分類器です。
ユーザー文を次のどれか1つに分類してください。

- add
- list
- edit
- delete
- calendar
- help
- advice
- confirm_yes
- confirm_no
- chat

ルール:
- 誤字や口語も考慮する
- 「今週のよてい」「らいしゅう」「かれんだー」も推定する
- 予定追加っぽい自然文も add
- 就活相談っぽい質問は advice
- 出力はラベル1語だけ

ユーザー文:
{text}
""".strip()

    response = client.responses.create(
        model="gpt-5.4-mini",
        input=prompt
    )

    intent = response.output_text.strip().lower()
    allowed = {
        "add", "list", "edit", "delete", "calendar",
        "help", "advice", "confirm_yes", "confirm_no", "chat"
    }
    return intent if intent in allowed else "chat"


def parse_event_from_text(text: str):
    """
    自然文や多少の誤字から予定を抽出
    JSONだけ返させる
    """
    client = get_client()
    today = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""
あなたは就活予定抽出器です。
ユーザー文から予定情報をJSONで抽出してください。

今日の日付: {today}

返すJSON形式:
{{
  "company": "会社名",
  "title": "予定タイトル",
  "date": "YYYY-MM-DD",
  "time": "",
  "type": "deadline|intern|interview|seminar|test|other",
  "memo": "",
  "tags": []
}}

ルール:
- 誤字をある程度補正して意味で解釈
- date は必ず YYYY-MM-DD
- 分からない項目は空文字
- JSON以外は出力しない
- 予定として解釈できないなら {{}}

ユーザー文:
{text}
""".strip()

    response = client.responses.create(
        model="gpt-5.4-mini",
        input=prompt
    )

    raw = response.output_text.strip()

    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        if not data.get("date"):
            return None
        return data
    except Exception:
        return None


def get_shukatsu_advice(text: str) -> str:
    client = get_client()

    prompt = f"""
あなたはやさしく実用的な就活アドバイザーです。
日本語で、短すぎず長すぎず、LINEで読みやすい形で答えてください。
必要なら箇条書き風にして構いません。
ユーザーの相談:
{text}
""".strip()

    response = client.responses.create(
        model="gpt-5.4-mini",
        input=prompt
    )

    return response.output_text.strip()