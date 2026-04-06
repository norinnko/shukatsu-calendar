"""
LINEメッセージ処理モジュール
SQLite + OpenAI対応 完成版
"""
import re
import uuid
from datetime import datetime, timedelta

from database import (
    init_db,
    add_event,
    get_events,
    get_upcoming_events,
    get_events_by_month,
    get_event_by_id,
    update_event,
    delete_event,
)
from calendar_image import generate_calendar_image
from ai_helper import (
    is_openai_available,
    classify_intent,
    parse_event_from_text,
    get_shukatsu_advice,
)

init_db()

pending_deletes = {}


def handle_message(user_id, text):
    text = text.strip()

    if is_openai_available():
        try:
            intent = classify_intent(text)
        except Exception as e:
            print("classify_intent error:", e)
            intent = classify_intent_rule(text)
    else:
        intent = classify_intent_rule(text)

    if intent == "add":
        return handle_add(user_id, text)
    elif intent == "list":
        return handle_list(user_id, text)
    elif intent == "edit":
        return handle_edit(user_id, text)
    elif intent == "delete":
        return handle_delete(user_id, text)
    elif intent == "calendar":
        return handle_calendar(user_id, text)
    elif intent == "help":
        return handle_help(), None
    elif intent == "advice":
        return handle_advice(text), None
    elif intent == "confirm_yes":
        return handle_confirm_yes(user_id)
    elif intent == "confirm_no":
        return handle_confirm_no(user_id)
    else:
        if is_openai_available():
            return handle_advice(text), None
        return handle_help(), None


def handle_add(user_id, text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    add_lines = [line for line in lines if re.match(r"^(追加|登録|新規)", line)]

    if len(add_lines) >= 2:
        return handle_add_multiple_rule(user_id, add_lines)

    if is_openai_available():
        try:
            parsed = parse_event_from_text(text)
            if parsed and parsed.get("date"):
                event = create_event_from_parsed(parsed)
                add_event(user_id, event)
                return format_add_success(event), None
        except Exception as e:
            print("handle_add ai error:", e)

    return handle_add_rule(user_id, text)


def handle_add_multiple_rule(user_id, lines):
    results = []

    for line in lines:
        reply, _ = handle_add_rule(user_id, line)
        results.append(reply)

    return "\n\n".join(results), None


def handle_add_rule(user_id, text):
    pattern = r"(?:追加|登録|新規)\s+(.+?)\s+(.+?)\s+(\d{1,4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2})"
    match = re.search(pattern, text)

    if not match:
        return (
            "📝 予定を追加するには:\n\n"
            "追加 会社名 タイトル 日付\n\n"
            "例: 追加 〇〇株式会社 ES締切 6/15",
            None
        )

    company = match.group(1).strip()
    title = match.group(2).strip()
    date_str = match.group(3).strip()

    date = parse_date(date_str)
    if not date:
        return "❌ 日付の形式が認識できません。YYYY-MM-DD または M/D の形式で入力してください。", None

    evt_type = guess_type(title)
    event = {
        "id": generate_event_id(date),
        "company": company,
        "type": evt_type,
        "title": title,
        "date": date,
        "time": "",
        "url": "",
        "memo": "",
        "status": "upcoming",
        "notified_7d": False,
        "notified_0d": False,
        "tags": [],
        "created_at": datetime.now().isoformat(),
    }

    try:
        add_event(user_id, event)
        return format_add_success(event), None
    except Exception as e:
        print("handle_add_rule error:", e)
        return "❌ 予定の保存に失敗しました。", None


def handle_list(user_id, text):
    if "今週" in text:
        days = 7
        label = "今週"
    elif "来週" in text:
        days = 14
        label = "来週まで"
    else:
        days = 30
        label = "直近30日"

    try:
        events = get_upcoming_events(user_id, days=days)
    except Exception as e:
        print("handle_list error:", e)
        return "❌ 予定の取得に失敗しました。", None

    if not events:
        return f"📭 {label}の予定はありません。\n\n予定を追加するには「追加」と入力してください。", None

    lines = [f"📅 {label}の予定\n"]
    now_date = datetime.now().date()

    for evt in events:
        evt_date = datetime.strptime(evt["date"], "%Y-%m-%d").date()
        remaining = (evt_date - now_date).days
        type_emoji = get_type_emoji(evt["type"])

        if remaining > 0:
            remaining_text = f"あと{remaining}日"
        elif remaining == 0:
            remaining_text = "今日！🔥"
        else:
            remaining_text = "過ぎました"

        lines.append(
            f"{type_emoji} {evt['company']} - {evt['title']}\n"
            f"   📅 {evt['date']} ({remaining_text})\n"
            f"   🆔 {evt['id']}"
        )

    return "\n\n".join(lines), None


def handle_edit(user_id, text):
    pattern = r"(?:編集|変更|更新)\s+(evt_\S+)\s+(\S+)\s+(.+)"
    match = re.search(pattern, text)

    if not match:
        return (
            "✏️ 編集するには:\n\n"
            "編集 イベントID フィールド 新しい値\n\n"
            "例: 編集 evt_20260615_001 日付 6/20\n"
            "例: 編集 evt_20260615_001 メモ 第一志望！",
            None
        )

    event_id = match.group(1).strip()
    field = match.group(2).strip()
    value = match.group(3).strip()

    field_map = {
        "会社": "company", "会社名": "company",
        "タイトル": "title", "題名": "title",
        "日付": "date", "日": "date",
        "時刻": "time", "時間": "time",
        "メモ": "memo", "備考": "memo",
        "URL": "url", "リンク": "url",
        "種類": "type", "タイプ": "type",
    }

    actual_field = field_map.get(field, field)

    if actual_field == "date":
        converted = parse_date(value)
        if not converted:
            return "❌ 日付形式が正しくありません。例: 6/20 または 2026-06-20", None
        value = converted

    try:
        success, updated = update_event(user_id, event_id, {actual_field: value})
        if success:
            return (
                f"✅ 予定を更新しました！\n\n"
                f"📋 {updated['company']} - {updated['title']}\n"
                f"📅 {updated['date']}",
                None
            )
        return f"❌ ID「{event_id}」の予定が見つかりません。「一覧」で確認してください。", None
    except Exception as e:
        print("handle_edit error:", e)
        return "❌ 予定の更新に失敗しました。", None


def handle_delete(user_id, text):
    pattern = r"(?:削除|取消|キャンセル)\s+(evt_\S+)"
    match = re.search(pattern, text)

    if not match:
        return (
            "🗑️ 削除するには:\n\n"
            "削除 イベントID\n\n"
            "例: 削除 evt_20260615_001\n\n"
            "IDは「一覧」で確認できます。",
            None
        )

    event_id = match.group(1).strip()
    target = get_event_by_id(user_id, event_id)

    if not target:
        return f"❌ ID「{event_id}」の予定が見つかりません。", None

    pending_deletes[user_id] = event_id
    return (
        f"⚠️ この予定を削除しますか？\n\n"
        f"📋 {target['company']} - {target['title']}\n"
        f"📅 {target['date']}\n\n"
        f"「はい」で削除、「いいえ」でキャンセル",
        None
    )


def handle_confirm_yes(user_id):
    event_id = pending_deletes.pop(user_id, None)
    if not event_id:
        return "🤔 確認待ちの操作がありません。", None

    try:
        if delete_event(user_id, event_id):
            return "✅ 予定を削除しました。", None
        return "❌ 削除に失敗しました。", None
    except Exception as e:
        print("handle_confirm_yes error:", e)
        return "❌ 削除に失敗しました。", None


def handle_confirm_no(user_id):
    pending_deletes.pop(user_id, None)
    return "❌ キャンセルしました。", None


def handle_calendar(user_id, text):
    now = datetime.now()
    year, month = now.year, now.month

    month_match = re.search(r"(\d{1,2})月", text)
    if month_match:
        month = int(month_match.group(1))
        if 1 <= month <= 12 and month < now.month:
            year = now.year + 1

    try:
        events = get_events_by_month(user_id, year, month)
        image_bytes = generate_calendar_image(year, month, events)
        reply = f"📅 {year}年{month}月のカレンダー（{len(events)}件の予定）"
        return reply, image_bytes
    except Exception as e:
        print("handle_calendar error:", e)
        return "❌ カレンダー画像の生成に失敗しました。", None


def handle_advice(text):
    if is_openai_available():
        try:
            advice = get_shukatsu_advice(text)
            if advice:
                return f"💡 就活アドバイス\n\n{advice}"
        except Exception as e:
            print("handle_advice error:", e)

    return "就活相談機能は現在うまく応答できませんでした。もう少し具体的に送ってみてください。"


def handle_help():
    return """📚 就活カレンダーの使い方

【予定追加】
「追加 〇〇株式会社 ES締切 6/15」
「来週水曜に△△の面接」

【予定一覧】
「一覧」「今週の予定」「来週の予定」

【カレンダー表示】
「カレンダー」「6月のカレンダー」

【予定編集】
「編集 evt_xxx 日付 6/20」
「編集 evt_xxx メモ 第一志望」

【予定削除】
「削除 evt_xxx」

【就活相談】💡
「面接対策を教えて」
「ESの書き方のコツは？」

🔔 1週間前と当日にリマインド通知が届きます！"""


def classify_intent_rule(text):
    text_lower = text.lower().strip()

    if text_lower in ("はい", "うん", "ok", "おk", "お願い", "yes"):
        return "confirm_yes"
    if text_lower in ("いいえ", "やめる", "やめて", "no", "キャンセル"):
        return "confirm_no"
    if re.match(r"(追加|登録|新規)", text_lower):
        return "add"
    if re.match(r"(一覧|予定|今週|来週)", text_lower):
        return "list"
    if re.match(r"(編集|変更|更新)", text_lower):
        return "edit"
    if re.match(r"(削除|取消)", text_lower):
        return "delete"
    if re.match(r"(カレンダー|今月|\d{1,2}月)", text_lower):
        return "calendar"
    if re.match(r"(ヘルプ|使い方|何ができ)", text_lower):
        return "help"
    if re.search(r"(面接|es|就活|志望動機|自己pr|ガクチカ|対策)", text_lower):
        return "advice"
    return "chat"


def parse_date(date_str):
    date_str = date_str.strip().replace("/", "-")
    parts = date_str.split("-")
    now = datetime.now()

    try:
        if len(parts) == 3 and len(parts[0]) == 4:
            return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        elif len(parts) == 3:
            return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        elif len(parts) == 2:
            month, day = int(parts[0]), int(parts[1])
            year = now.year
            candidate = datetime(year, month, day)
            if candidate < now - timedelta(days=30):
                year += 1
            return f"{year:04d}-{month:02d}-{day:02d}"
    except ValueError:
        pass

    return None


def guess_type(title):
    title_lower = title.lower()
    if any(w in title_lower for w in ["es", "エントリー", "締切", "締め切り", "提出", "応募"]):
        return "deadline"
    if any(w in title_lower for w in ["インターン", "intern"]):
        return "intern"
    if any(w in title_lower for w in ["面接", "面談", "リクルーター"]):
        return "interview"
    if any(w in title_lower for w in ["説明会", "セミナー", "座談会", "ob"]):
        return "seminar"
    if any(w in title_lower for w in ["テスト", "spi", "適性検査", "玉手箱", "webテスト"]):
        return "test"
    return "other"


def get_type_emoji(evt_type):
    emojis = {
        "deadline": "🔴",
        "intern": "🔵",
        "interview": "🟢",
        "seminar": "🟣",
        "test": "🟠",
        "other": "⚪",
    }
    return emojis.get(evt_type, "⚪")


def generate_event_id(date_str):
    short_uuid = uuid.uuid4().hex[:6]
    date_part = date_str.replace("-", "")
    return f"evt_{date_part}_{short_uuid}"


def create_event_from_parsed(parsed):
    return {
        "id": generate_event_id(parsed["date"]),
        "company": parsed.get("company", ""),
        "type": parsed.get("type", "other"),
        "title": parsed.get("title", ""),
        "date": parsed["date"],
        "time": parsed.get("time", ""),
        "url": "",
        "memo": parsed.get("memo", ""),
        "status": "upcoming",
        "notified_7d": False,
        "notified_0d": False,
        "tags": parsed.get("tags", []),
        "created_at": datetime.now().isoformat(),
    }


def format_add_success(event):
    return (
        f"✅ 予定を保存しました\n"
        f"{event['company']} / {event['title']} / {event['date']}"
    )