"""
GitHub API連携モジュール
events.jsonの読み書きをGitHub REST API経由で行う
"""
import requests
import json
import base64
import os
from datetime import datetime, timedelta


class GitHubEventStore:
    def __init__(self):
        self.token = os.environ.get("GITHUB_TOKEN")
        self.repo = os.environ.get("GITHUB_REPO")
        self.api_base = f"https://api.github.com/repos/{self.repo}"
        self.file_path = "data/events.json"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def get_events(self):
        """events.jsonを取得し、イベントリストとSHAを返す"""
        resp = requests.get(
            f"{self.api_base}/contents/{self.file_path}",
            headers=self.headers,
        )
        if resp.status_code == 404:
            self._create_initial_file()
            return [], None

        data = resp.json()
        content = base64.b64decode(data["content"]).decode("utf-8")
        events = json.loads(content)
        return events, data["sha"]

    def save_events(self, events, sha=None):
        """events.jsonを更新"""
        content = base64.b64encode(
            json.dumps(events, ensure_ascii=False, indent=2).encode("utf-8")
        ).decode("utf-8")

        payload = {
            "message": f"Update events ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
            "content": content,
        }
        if sha:
            payload["sha"] = sha

        resp = requests.put(
            f"{self.api_base}/contents/{self.file_path}",
            headers=self.headers,
            json=payload,
        )
        return resp.status_code in (200, 201)

    def add_event(self, event):
        """イベントを追加"""
        events, sha = self.get_events()
        events.append(event)
        return self.save_events(events, sha)

    def update_event(self, event_id, updates):
        """イベントを更新"""
        events, sha = self.get_events()
        for evt in events:
            if evt["id"] == event_id:
                evt.update(updates)
                return self.save_events(events, sha), evt
        return False, None

    def delete_event(self, event_id):
        """イベントを削除"""
        events, sha = self.get_events()
        original_len = len(events)
        events = [e for e in events if e["id"] != event_id]
        if len(events) < original_len:
            return self.save_events(events, sha)
        return False

    def get_events_by_month(self, year, month):
        """特定月のイベントを取得"""
        events, _ = self.get_events()
        month_str = f"{year}-{month:02d}"
        return [e for e in events if e["date"].startswith(month_str)]

    def get_upcoming_events(self, days=14):
        """直近N日間のイベントを取得"""
        events, _ = self.get_events()
        today = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        upcoming = [
            e for e in events
            if today <= e["date"] <= end_date and e.get("status") == "upcoming"
        ]
        return sorted(upcoming, key=lambda x: x["date"])

    def _create_initial_file(self):
        """events.jsonの初期ファイルを作成"""
        content = base64.b64encode(b"[]").decode("utf-8")
        requests.put(
            f"{self.api_base}/contents/{self.file_path}",
            headers=self.headers,
            json={"message": "Initialize events.json", "content": content},
        )
