"""
就活カレンダー - メインアプリケーション
LINE Messaging API Webhook + カレンダー画像配信
"""
import os
import uuid
import hashlib
import hmac
import base64
from flask import Flask, request, abort, send_file, jsonify
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    ImageMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError

from line_handler import handle_message

app = Flask(__name__)

# LINE設定
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# カレンダー画像の一時保存
CALENDAR_IMAGES = {}  # {filename: bytes}


@app.route("/callback", methods=["POST"])
def callback():
    """LINE Webhook受付エンドポイント"""
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    """テキストメッセージのハンドラー"""
    user_id = event.source.user_id
    text = event.message.text

    reply_text, image_bytes = handle_message(user_id, text)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        messages = []

        if image_bytes:
            # カレンダー画像を一時保存して配信
            filename = f"{uuid.uuid4().hex}.png"
            CALENDAR_IMAGES[filename] = image_bytes.getvalue()

            # 古い画像を削除（50件以上）
            if len(CALENDAR_IMAGES) > 50:
                oldest = list(CALENDAR_IMAGES.keys())[0]
                del CALENDAR_IMAGES[oldest]

            base_url = os.environ.get("BASE_URL", request.url_root.rstrip("/"))
            image_url = f"{base_url}/calendar_image/{filename}"

            messages.append(ImageMessage(
                original_content_url=image_url,
                preview_image_url=image_url,
            ))

        if reply_text:
            messages.append(TextMessage(text=reply_text))

        if messages:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=messages,
                )
            )


@app.route("/calendar_image/<filename>")
def serve_calendar_image(filename):
    """カレンダー画像を配信"""
    if filename not in CALENDAR_IMAGES:
        abort(404)

    from io import BytesIO
    return send_file(
        BytesIO(CALENDAR_IMAGES[filename]),
        mimetype="image/png",
        download_name=filename,
    )


@app.route("/health")
def health():
    """ヘルスチェック"""
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    """トップページ"""
    return "🎓 就活カレンダーBot is running!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
