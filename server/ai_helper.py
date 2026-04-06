"""
OpenAI API連携モジュール
自然文からイベント情報を抽出し、就活アドバイスも提供する
"""
import os
import json
import requests
from datetime import datetime


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def call_openai(system_prompt, user_message, response_format=None):
    """OpenAI APIを呼び出す共通関数"""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.3,
        "max_tokens": 1000,
    }
    if response_format:
        payload["response_format"] = response_format

    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
    )
    if resp.status_code != 200:
        return None
    return resp.json()["choices"][0]["message"]["content"]


def parse_event_from_text(user_text):
    """
    自然文からイベント情報を抽出する。
    例: 「来週の水曜に〇〇株式会社の面接がある」
    → {"company": "〇〇株式会社", "type": "interview", "title": "面接", "date": "2026-04-15", ...}
    """
    today = datetime.now().strftime("%Y-%m-%d")
    weekday = ["月", "火", "水", "木", "金", "土", "日"][datetime.now().weekday()]

    system_prompt = f"""あなたは就活予定の解析アシスタントです。
ユーザーのメッセージから就活イベント情報を抽出し、JSON形式で返してください。

今日の日付: {today}（{weekday}曜日）

以下のJSON形式で返してください（他のテキストは含めないでください）:
{{
  "company": "会社名（わからない場合は空文字）",
  "type": "イベントタイプ（deadline/intern/interview/seminar/test/other）",
  "title": "イベントのタイトル（例: ES提出締切、一次面接）",
  "date": "YYYY-MM-DD形式の日付",
  "time": "HH:MM形式の時刻（わからない場合は空文字）",
  "memo": "その他のメモ情報（あれば）",
  "tags": ["タグのリスト"],
  "confidence": 0.0から1.0の解析信頼度
}}

タイプの判定基準:
- deadline: ES提出、書類提出、エントリー、応募締切
- intern: インターン、インターンシップ
- interview: 面接、面談、リクルーター面談
- seminar: 説明会、セミナー、座談会、OB訪問
- test: Webテスト、適性検査、SPI、玉手箱
- other: 上記に当てはまらないもの

「来週」「今週の金曜」「明日」「3日後」等の相対日付を正しく計算してください。
"""

    result = call_openai(system_prompt, user_text)
    if not result:
        return None

    try:
        # JSON部分を抽出（コードブロックで囲まれている場合も対応）
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]
        return json.loads(cleaned)
    except (json.JSONDecodeError, IndexError):
        return None


def classify_intent(user_text):
    """
    ユーザーメッセージの意図を分類する。
    戻り値: "add", "list", "edit", "delete", "calendar", "help", "advice", "chat"
    """
    system_prompt = """あなたは就活カレンダーボットのメッセージ分類器です。
ユーザーのメッセージの意図を以下の1つに分類し、その単語だけを返してください:

- add: 予定の追加・登録（「追加」「登録」「新規」や、予定を伝えるメッセージ）
- list: 予定一覧の表示（「一覧」「今週」「来週」「予定」）
- edit: 予定の編集（「編集」「変更」「更新」）
- delete: 予定の削除（「削除」「取消」「キャンセル」）
- calendar: カレンダー画像の表示（「カレンダー」「今月」「◯月」）
- help: 使い方の案内（「ヘルプ」「使い方」「何ができる」）
- advice: 就活アドバイス（「面接対策」「ES添削」「アドバイス」「教えて」「コツ」）
- confirm_yes: 確認に対する肯定（「はい」「うん」「OK」「お願い」）
- confirm_no: 確認に対する否定（「いいえ」「やめる」「キャンセル」）
- chat: 上記に当てはまらない雑談

1単語だけ返してください。"""

    result = call_openai(system_prompt, user_text)
    if result:
        return result.strip().lower()
    return "chat"


def get_shukatsu_advice(user_text):
    """就活に関するアドバイスを返す"""
    system_prompt = """あなたは日本の就職活動に詳しいキャリアアドバイザーです。
就活生からの質問に、簡潔で実践的なアドバイスを返してください。

ルール:
- LINEメッセージなので、500文字以内で簡潔に
- 箇条書きや絵文字を使って読みやすく
- 具体的なアクションを提案
- 励ましの言葉を添える
"""
    return call_openai(system_prompt, user_text)


def is_openai_available():
    """OpenAI APIが利用可能かチェック"""
    return bool(OPENAI_API_KEY)
