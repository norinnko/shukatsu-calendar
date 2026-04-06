import re
from datetime import datetime
from database import add_event, get_upcoming_events


def normalize_date(date_str: str) -> str:
    date_str = date_str.strip()

    if re.match(r"^\d{1,2}/\d{1,2}$", date_str):
        year = datetime.now().year
        month, day = map(int, date_str.split("/"))
        return f"{year:04d}-{month:02d}-{day:02d}"

    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str

    raise ValueError("日付形式が正しくありません")


def handle_message(user_id, text):
    text = text.strip()

    if text == "ヘルプ":
        return (
            "使い方:\n"
            "・追加 会社名 タイトル 日付\n"
            "  例: 追加 ○○株式会社 ES締切 6/15\n"
            "・一覧\n"
            "・来週の予定\n",
            None
        )

    if text.startswith("追加 "):
        try:
            body = text[3:].strip()
            parts = body.split()

            if len(parts) < 3:
                return (
                    "予定を追加するには:\n\n"
                    "追加 会社名 タイトル 日付\n\n"
                    "例: 追加 ○○株式会社 ES締切 6/15",
                    None
                )

            company = parts[0]
            event_date = parts[-1]
            title = " ".join(parts[1:-1])

            normalized_date = normalize_date(event_date)
            add_event(user_id, company, title, normalized_date)

            return (f"✅ 予定を保存しました\n{company} / {title} / {normalized_date}", None)

        except Exception as e:
            print("add_event error:", e)
            return ("❌ 予定の保存に失敗しました。", None)

    if text in ["一覧", "来週の予定", "今週の予定"]:
        try:
            rows = get_upcoming_events(user_id, limit=10)

            if not rows:
                return ("来週までの予定はありません。", None)

            lines = ["📅 予定一覧"]
            for row in rows:
                lines.append(f"{row['event_date']} | {row['company']} | {row['title']}")

            return ("\n".join(lines), None)

        except Exception as e:
            print("get_events error:", e)
            return ("❌ 予定の取得に失敗しました。", None)

    return ("メッセージありがとうございます！\n「ヘルプ」と送ると使い方を表示します。", None)