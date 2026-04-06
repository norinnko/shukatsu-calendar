"""
LINEメッセージ処理モジュール
ユーザーメッセージを解析して適切なアクションを実行する
"""
import re
import uuid
from datetime import datetime, timedelta

from github_api import GitHubEventStore
from calendar_image import generate_calendar_image
from ai_helper import (
    is_openai_available,
    classify_intent,
    parse_event_from_text,
    get_shukatsu_advice,
)

store = GitHubEventStore()

# 削除確認用の一時ストレージ（簡易実装）
pending_deletes = {}


def handle_message(user_id, text):
    """
    ユーザーメッセージを処理し、返信テキストとオプションの画像を返す。

    Returns:
        tuple: (reply_text, image_bytes_or_none)
    """
    text = text.strip()

    # OpenAI APIが利用可能ならAIで意図分類
    if is_openai_available():
        intent = classify_intent(text)
    else:
        intent = classify_intent_rule(text)

    if intent == "add":
        return handle_add(user_id, text)
    elif intent == "list":
        return handle_list(text)
    elif intent == "edit":
        return handle_edit(text)
    elif intent == "delete":
        return handle_delete(user_id, text)
    elif intent == "calendar":
        return handle_calendar(text)
    elif intent == "help":
        return handle_help(), None
    elif intent == "advice" and is_openai_available():
        return handle_advice(text), None
    elif intent == "confirm_yes":
        return handle_confirm_yes(user_id)
    elif intent == "confirm_no":
        return handle_confirm_no(user_id)
    else:
        if is_openai_available():
            # 雑談でも就活関連なら対応
            return handle_advice(text), None
        return handle_help(), None


def handle_add(user_id, text):
    """予定追加"""
    if is_openai_available():
        parsed = parse_event_from_text(text)
        if parsed and parsed.get("date"):
            event = create_event_from_parsed(parsed)
            if store.add_event(event):
                return format_add_success(event), None
            return "❌ 予定の保存に失敗しました。もう一度お試しください。", None
        return "🤔 予定の情報をうまく読み取れませんでした。\n\n例: 「追加 〇〇株式会社 ES締切 6/15」", None
    else:
        return handle_add_rule(text)


def handle_add_rule(text):
    """ルールベースの予定追加（OpenAI APIなし）"""
    # パターン: 追加 会社名 タイトル 日付
    pattern = r"(?:追加|登録|新規)\s+(.+?)\s+(.+?)\s+(\d{1,4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2})"
    match = re.search(pattern, text)
    if not match:
        return "📝 予定を追加するには:\n\n追加 会社名 タイトル 日付\n\n例: 追加 〇〇株式会社 ES締切 6/15", None

    company = match.group(1)
    title = match.group(2)
    date_str = match.group(3)
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

    if store.add_event(event):
        return format_add_success(event), None
    return "❌ 予定の保存に失敗しました。", None


def handle_list(text):
    """予定一覧"""
    # 期間の判定
    if "今週" in text:
        days = 7
        label = "今週"
    elif "来週" in text:
        days = 14
        label = "来週まで"
    else:
        days = 30
        label = "直近30日"

    events = store.get_upcoming_events(days=days)
    if not events:
        return f"📭 {label}の予定はありません。\n\n予定を追加するには「追加」と入力してください。", None

    lines = [f"📅 {label}の予定\n"]
    for evt in events:
        evt_date = datetime.strptime(evt["date"], "%Y-%m-%d")
        remaining = (evt_date - datetime.now()).days
        type_emoji = get_type_emoji(evt["type"])
        remaining_text = f"あと{remaining}日" if remaining > 0 else "今日！🔥" if remaining == 0 else "過ぎました"

        lines.append(
            f"{type_emoji} {evt['company']} - {evt['title']}\n"
            f"   📅 {evt['date']} ({remaining_text})\n"
            f"   🆔 {evt['id']}"
        )

    return "\n\n".join(lines), None


def handle_edit(text):
    """予定編集"""
    # パターン: 編集 ID フィールド 新しい値
    pattern = r"(?:編集|変更|更新)\s+(evt_\S+)\s+(\S+)\s+(.+)"
    match = re.search(pattern, text)
    if not match:
        return "✏️ 編集するには:\n\n編集 イベントID フィールド 新しい値\n\n例: 編集 evt_20260615_001 日付 6/20\n例: 編集 evt_20260615_001 メモ 第一志望！", None

    event_id = match.group(1)
    field = match.group(2)
    value = match.group(3)

    field_map = {
        "会社": "company", "会社名": "company",
        "タイトル": "title", "題名": "title",
        "日付": "date", "日": "date",
        "時刻": "time", "時間": "time",
        "メモ": "memo", "備考": "memo",
        "URL": "url", "リンク": "url",
    }

    actual_field = field_map.get(field, field)
    if actual_field == "date":
        value = parse_date(value) or value

    success, updated = store.update_event(event_id, {actual_field: value})
    if success:
        return f"✅ 予定を更新しました！\n\n📋 {updated['company']} - {updated['title']}\n📅 {updated['date']}", None
    return f"❌ ID「{event_id}」の予定が見つかりません。「一覧」で確認してください。", None


def handle_delete(user_id, text):
    """予定削除（確認あり）"""
    pattern = r"(?:削除|取消|キャンセル)\s+(evt_\S+)"
    match = re.search(pattern, text)
    if not match:
        return "🗑️ 削除するには:\n\n削除 イベントID\n\n例: 削除 evt_20260615_001\n\nIDは「一覧」で確認できます。", None

    event_id = match.group(1)
    events, _ = store.get_events()
    target = next((e for e in events if e["id"] == event_id), None)
    if not target:
        return f"❌ ID「{event_id}」の予定が見つかりません。", None

    pending_deletes[user_id] = event_id
    return (
        f"⚠️ この予定を削除しますか？\n\n"
        f"📋 {target['company']} - {target['title']}\n"
        f"📅 {target['date']}\n\n"
        f"「はい」で削除、「いいえ」でキャンセル"
    ), None


def handle_confirm_yes(user_id):
    """確認への肯定応答"""
    event_id = pending_deletes.pop(user_id, None)
    if not event_id:
        return "🤔 確認待ちの操作がありません。", None

    if store.delete_event(event_id):
        return "✅ 予定を削除しました。", None
    return "❌ 削除に失敗しました。", None


def handle_confirm_no(user_id):
    """確認への否定応答"""
    pending_deletes.pop(user_id, None)
    return "❌ キャンセルしました。", None


def handle_calendar(text):
    """カレンダー画像を生成"""
    now = datetime.now()
    year, month = now.year, now.month

    # 「6月」「7月のカレンダー」等を検出
    month_match = re.search(r"(\d{1,2})月", text)
    if month_match:
        month = int(month_match.group(1))
        if 1 <= month <= 12:
            if month < now.month:
                year = now.year + 1  # 過去の月なら来年とみなす

    events = store.get_events_by_month(year, month)
    image_bytes = generate_calendar_image(year, month, events)

    event_count = len(events)
    reply = f"📅 {year}年{month}月のカレンダー（{event_count}件の予定）"

    return reply, image_bytes


def handle_advice(text):
    """就活アドバイス"""
    advice = get_shukatsu_advice(text)
    if advice:
        return f"💡 就活アドバイス\n\n{advice}"
    return "申し訳ありません、アドバイスの取得に失敗しました。もう一度お試しください。"


def handle_help():
    """ヘルプメッセージ"""
    help_text = """📚 就活カレンダーの使い方

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
    return help_text


# --- ユーティリティ ---

def classify_intent_rule(text):
    """ルールベースの意図分類（OpenAI APIなしの場合）"""
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
    return "chat"


def parse_date(date_str):
    """日付文字列をYYYY-MM-DD形式に変換"""
    date_str = date_str.replace("/", "-")
    parts = date_str.split("-")
    now = datetime.now()

    try:
        if len(parts) == 3 and len(parts[0]) == 4:
            return date_str
        elif len(parts) == 3:
            return f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        elif len(parts) == 2:
            month, day = int(parts[0]), int(parts[1])
            year = now.year
            candidate = datetime(year, month, day)
            if candidate < now - timedelta(days=30):
                year += 1
            return f"{year}-{month:02d}-{day:02d}"
    except ValueError:
        pass
    return None


def guess_type(title):
    """タイトルからイベントタイプを推測"""
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
    """タイプに応じた絵文字"""
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
    """イベントIDを生成"""
    short_uuid = uuid.uuid4().hex[:6]
    date_part = date_str.replace("-", "")
    return f"evt_{date_part}_{short_uuid}"


def create_event_from_parsed(parsed):
    """AIの解析結果からイベントオブジェクトを作成"""
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
    """追加成功メッセージ"""
    type_emoji = get_type_emoji(event["type"])
    msg = (
        f"✅ 予定を追加しました！\n\n"
        f"{type_emoji} {event['company']}\n"
        f"📌 {event['title']}\n"
        f"📅 {event['date']}"
    )
    if event.get("time"):
        msg += f" {event['time']}"
    if event.get("memo"):
        msg += f"\n📝 {event['memo']}"
    msg += f"\n🆔 {event['id']}\n\n編集: 「編集 {event['id']}」\n削除: 「削除 {event['id']}」"
    return msg
