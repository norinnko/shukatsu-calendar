# 📅 就活カレンダー

LINEボット × Webカレンダーで就活の予定を一元管理するアプリ。

LINEでチャットするだけで予定を追加・編集・削除でき、カレンダー画像も確認可能。1週間前と当日にリマインド通知が届きます。

---

## ✨ 主な機能

| 機能 | 説明 |
|------|------|
| 📱 **LINE予定管理** | チャットで「追加 〇〇 ES締切 6/15」と送るだけで予定登録 |
| 🖼️ **カレンダー画像** | 「カレンダー」と送ると月間カレンダー画像を返信（type別色分け） |
| 🔔 **リマインド通知** | 7日前・当日に自動でLINE通知 |
| 🌐 **Webカレンダー** | GitHub Pagesでスマホ対応のPWAカレンダーを表示 |
| 🤖 **AI解析（任意）** | OpenAI APIで自然文から予定を自動解析＆就活アドバイス |

---

## 🏗️ システム構成

```
LINE App ──Webhook──→ Bot Server (Render/Flask)
                          │
                          ├── メッセージ解析（AI or ルールベース）
                          ├── カレンダー画像生成（Pillow）
                          └── GitHub API ←→ events.json
                                              │
                          GitHub Actions ──→ リマインド通知
                                              │
                          GitHub Pages  ──→ Web PWA カレンダー
```

---

## 📁 プロジェクト構成

```
shukatsu-calendar/
├── server/                        # LINEボットサーバー（Render）
│   ├── app.py                     # Flaskメインアプリ
│   ├── line_handler.py            # メッセージ処理
│   ├── ai_helper.py               # OpenAI API連携（任意）
│   ├── calendar_image.py          # カレンダー画像生成
│   ├── github_api.py              # GitHub API連携
│   ├── reminder.py                # リマインド通知
│   ├── requirements.txt
│   ├── Procfile
│   └── fonts/
│       └── NotoSansJP-Regular.ttf # 日本語フォント
├── docs/                          # GitHub Pages（Web PWA）
│   ├── index.html
│   ├── css/style.css
│   ├── js/
│   │   ├── app.js
│   │   ├── calendar.js
│   │   └── events.js
│   ├── manifest.json
│   └── sw.js
├── data/
│   └── events.json                # 予定データ
├── .github/workflows/
│   └── remind.yml                 # リマインド通知（毎朝6時）
└── README.md
```

---

## 🚀 セットアップ

### 1. リポジトリ作成

```bash
git clone https://github.com/<your-username>/shukatsu-calendar.git
cd shukatsu-calendar
```

### 2. LINE Messaging API 設定

1. [LINE Developers Console](https://developers.line.biz/) にアクセス
2. プロバイダーを作成 → Messaging APIチャネルを作成
3. 以下を控えておく：
   - **チャネルアクセストークン**（長期）
   - **チャネルシークレット**
   - **自分のユーザーID**（リマインド通知用）
4. 応答メッセージを **オフ** に設定
5. Webhookの利用を **オン** に設定

### 3. Render デプロイ

1. [Render](https://render.com/) でアカウント作成
2. New → Web Service → GitHubリポジトリを接続
3. 設定：
   - **Root Directory**: `server`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. 環境変数を設定（下記参照）
5. デプロイ後、WebhookURLをLINE Developers Consoleに登録：
   ```
   https://<your-app>.onrender.com/callback
   ```

### 4. 環境変数

Render Dashboard で以下を設定：

| 変数名 | 説明 |
|--------|------|
| `LINE_CHANNEL_ACCESS_TOKEN` | LINEチャネルアクセストークン |
| `LINE_CHANNEL_SECRET` | LINEチャネルシークレット |
| `GITHUB_TOKEN` | GitHub Personal Access Token（repo権限） |
| `GITHUB_REPO` | `username/shukatsu-calendar` 形式 |
| `BASE_URL` | Renderアプリの公開URL（例: `https://xxx.onrender.com`） |
| `TZ` | `Asia/Tokyo` |
| `OPENAI_API_KEY` | OpenAI APIキー（**任意** — なくても動作します） |

### 5. GitHub Pages 有効化

Settings → Pages → Source: **Deploy from a branch** → Branch: `main`, Folder: `/docs`

### 6. GitHub Secrets 設定（リマインド通知用）

Settings → Secrets and variables → Actions に以下を追加：

| Secret名 | 値 |
|-----------|-----|
| `LINE_CHANNEL_ACCESS_TOKEN` | LINEチャネルアクセストークン |
| `LINE_USER_ID` | 自分のLINEユーザーID |

### 7. 日本語フォントの配置

カレンダー画像の日本語表示用に、Noto Sans JP フォントを配置：

```bash
# Google Fontsからダウンロード
wget -O server/fonts/NotoSansJP-Regular.ttf \
  "https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf"
```

### 8. 動作確認

1. LINEでボットを友だち追加（QRコード）
2. 「ヘルプ」と送信 → 使い方が表示されればOK
3. 「追加 テスト株式会社 ES締切 6/15」→ 予定が登録される
4. 「カレンダー」→ カレンダー画像が返ってくる
5. Web（`https://<username>.github.io/shukatsu-calendar/`）にアクセス

---

## 💬 LINEボットの使い方

### 予定を追加

```
追加 〇〇株式会社 ES締切 6/15
追加 △△商事 面接 2026-07-01 14:00
```

AI有効時は自然文でもOK：
```
来週の水曜に〇〇株式会社の一次面接がある
```

### 予定を確認

```
一覧           → 直近30日の予定
今週の予定      → 今週の予定
来週の予定      → 来週までの予定
```

### カレンダー画像を見る

```
カレンダー      → 今月のカレンダー画像
6月のカレンダー  → 6月のカレンダー画像
```

### 予定を編集・削除

```
編集 evt_xxx 日付 6/20
編集 evt_xxx メモ 第一志望！
削除 evt_xxx
```

### 就活相談（AI有効時）

```
面接対策を教えて
ESの志望動機のコツは？
```

---

## 🎨 予定タイプと色分け

| タイプ | 用途 | 色 |
|--------|------|-----|
| 🔴 `deadline` | ES提出・書類締切 | 赤 |
| 🔵 `intern` | インターンシップ | 青 |
| 🟢 `interview` | 面接・面談 | 緑 |
| 🟣 `seminar` | 説明会・セミナー | 紫 |
| 🟠 `test` | 適性検査・Webテスト | 橙 |
| ⚪ `other` | その他 | グレー |

---

## 🔔 リマインド通知

GitHub Actionsが毎朝6:00（JST）に自動実行されます。

- **7日前**: 「🔔 あと7日です！」
- **当日**: 「🚨 今日が期限です！」

手動実行も可能：Actions → Shukatsu Reminder → Run workflow

---

## 🤖 AI機能（OpenAI API・任意）

環境変数 `OPENAI_API_KEY` を設定すると以下の機能が有効になります：

- **自然文解析**: 「来週の木曜に〇〇の面接」→ 日付・会社名・タイプを自動判定
- **意図分類**: メッセージの意図をAIが判断（精度向上）
- **就活アドバイス**: 面接対策やESの書き方をAIが回答

APIキーがなくてもルールベースで基本機能は全て動作します。

---

## ⚠️ 注意事項

- **Render無料枠**: 15分間アクセスがないとスリープします。初回応答に30秒ほどかかることがあります
- **GitHub API制限**: 認証ありで5,000リクエスト/時間。通常利用なら十分です
- **トークン管理**: APIキーやトークンは絶対にソースコードにハードコードしないでください

---

## 📄 ライセンス

MIT License
