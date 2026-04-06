"""
リマインド通知モジュール
7日前・当日のイベントをLINEでプッシュ通知する
GitHub Actionsから実行される
"""
import json
import os
import requests
from datetime import datetime, timedelta


LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")
EVENTS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "events.json")


def load_events():
    path = os.path.abspath(EVENTS_FILE)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_events(events):
    path = os.path.abspath(EVENTS_FILE)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)


def send_line_push(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message}],
    }
    resp = requests.post(url, headers=headers, json=payload)
    return resp.status_code == 200


def get_type_emoji(evt_type):
    return {"deadline": "🔴", "intern": "🔵", "interview": "🟢",
            "seminar": "🟣", "test": "🟠", "other": "⚪"}.get(evt_type, "⚪")


def get_weekday_jp(date_str):
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    return weekdays[datetime.strptime(date_str, "%Y-%m-%d").weekday()]


def check_and_notify():
    events = load_events()
    today = datetime.now().strftime("%Y-%m-%d")
    seven_days_later = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    notifications_7d, notifications_0d = [], []
    updated = False

    for evt in events:
        if evt.get("status") != "upcoming":
            continue
        if evt["date"] == seven_days_later and not evt.get("notified_7d"):
            notifications_7d.append(evt)
            evt["notified_7d"] = True
            updated = True
        if evt["date"] == today and not evt.get("notified_0d"):
            notifications_0d.append(evt)
            evt["notified_0d"] = True
            updated = True

    if notifications_7d:
        lines = ["🔔 就活リマインド【1週間前】\n"]
        for evt in notifications_7d:
            wd = get_weekday_jp(evt["date"])
            lines.append(f"{get_type_emoji(evt['type'])} {evt['company']} - {evt['title']}\n   📅 {evt['date']}（{wd}）" + (f" {evt['time']}" if evt.get("time") else ""))
            if evt.get("memo"):
                lines.append(f"   📝 {evt['memo']}")
        lines.append("\nあと7日です！💪")
        send_line_push("\n".join(lines))

    if notifications_0d:
        lines = ["🚨 今日が期限です！\n"]
        for evt in notifications_0d:
            lines.append(f"{get_type_emoji(evt['type'])} {evt['company']} - {evt['title']}\n   ⏰ 今日" + (f" {evt['time']} まで" if evt.get("time") else ""))
            if evt.get("memo"):
                lines.append(f"   📝 {evt['memo']}")
        lines.append("\n頑張れ！🔥")
        send_line_push("\n".join(lines))

    if updated:
        save_events(events)
    print(f"Sent {len(notifications_7d) + len(notifications_0d)} notifications")


if __name__ == "__main__":
    check_and_notify()
