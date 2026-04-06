"""
カレンダー画像生成モジュール
見やすい改善版
"""
import calendar
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent
FONT_PATH = BASE_DIR / "fonts" / "NotoSansJP-Regular.ttf"


# 色設定
COLOR_BG = (250, 252, 255)
COLOR_HEADER = (70, 130, 220)
COLOR_HEADER_TEXT = (255, 255, 255)
COLOR_GRID = (210, 218, 230)
COLOR_TEXT = (40, 50, 65)
COLOR_SUBTEXT = (90, 100, 120)
COLOR_SUN = (220, 70, 70)
COLOR_SAT = (60, 120, 220)
COLOR_TODAY_BG = (225, 240, 255)
COLOR_EVENT_TEXT = (30, 30, 30)

TYPE_COLORS = {
    "deadline": (231, 76, 60),    # 赤
    "intern": (52, 152, 219),     # 青
    "interview": (46, 204, 113),  # 緑
    "seminar": (155, 89, 182),    # 紫
    "test": (243, 156, 18),       # 橙
    "other": (149, 165, 166),     # 灰
}

TYPE_LABELS = {
    "deadline": "締切",
    "intern": "インターン",
    "interview": "面接",
    "seminar": "説明会",
    "test": "テスト",
    "other": "その他",
}


def load_font(size: int):
    try:
        if FONT_PATH.exists():
            return ImageFont.truetype(str(FONT_PATH), size)
    except Exception:
        pass
    return ImageFont.load_default()


def get_text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def event_short_label(event):
    """
    表示用の短いラベルを返す
    """
    evt_type = event.get("type", "other")
    title = event.get("title", "").strip()

    # タイトルから短縮表示を作る
    if evt_type == "deadline":
        return "締切"
    if evt_type == "interview":
        return "面接"
    if evt_type == "seminar":
        return "説明会"
    if evt_type == "intern":
        return "インターン"
    if evt_type == "test":
        return "テスト"

    # その他はタイトル短縮
    if len(title) > 8:
        return title[:8]
    return title if title else "予定"


def group_events_by_date(events):
    grouped = {}
    for evt in events:
        date_str = evt.get("date", "")
        grouped.setdefault(date_str, []).append(evt)
    return grouped


def generate_calendar_image(year, month, events):
    """
    year, month, events からカレンダー画像を生成して BytesIO を返す
    events: [{"date": "YYYY-MM-DD", "type": "...", "title": "..."}]
    """
    # キャンバスサイズ
    width = 1400
    height = 1600

    margin_x = 40
    top_header_h = 120
    weekday_h = 60
    bottom_legend_h = 110

    grid_top = top_header_h + weekday_h
    grid_bottom = height - bottom_legend_h - 30
    grid_height = grid_bottom - grid_top

    cell_w = (width - margin_x * 2) // 7
    cell_h = grid_height // 6

    # 画像作成
    image = Image.new("RGB", (width, height), COLOR_BG)
    draw = ImageDraw.Draw(image)

    # フォント
    title_font = load_font(36)
    weekday_font = load_font(22)
    day_font = load_font(24)
    event_font = load_font(18)
    small_font = load_font(16)
    legend_font = load_font(18)

    # ヘッダー
    draw.rectangle((0, 0, width, top_header_h), fill=COLOR_HEADER)
    title_text = f"{year}年{month}月"
    tw, th = get_text_size(draw, title_text, title_font)
    draw.text(((width - tw) / 2, (top_header_h - th) / 2), title_text, fill=COLOR_HEADER_TEXT, font=title_font)

    # 曜日ヘッダー
    weekdays = ["日", "月", "火", "水", "木", "金", "土"]
    for i, wd in enumerate(weekdays):
        x1 = margin_x + i * cell_w
        x2 = x1 + cell_w
        y1 = top_header_h
        y2 = top_header_h + weekday_h

        draw.rectangle((x1, y1, x2, y2), fill=(245, 247, 250), outline=COLOR_GRID)

        color = COLOR_TEXT
        if i == 0:
            color = COLOR_SUN
        elif i == 6:
            color = COLOR_SAT

        ww, wh = get_text_size(draw, wd, weekday_font)
        draw.text((x1 + (cell_w - ww) / 2, y1 + (weekday_h - wh) / 2), wd, fill=color, font=weekday_font)

    # 月の日付
    cal = calendar.Calendar(firstweekday=6)  # 日曜始まり
    month_days = cal.monthdayscalendar(year, month)

    while len(month_days) < 6:
        month_days.append([0] * 7)

    events_by_date = group_events_by_date(events)
    today = datetime.now()

    for row_idx, week in enumerate(month_days):
        for col_idx, day in enumerate(week):
            x1 = margin_x + col_idx * cell_w
            y1 = grid_top + row_idx * cell_h
            x2 = x1 + cell_w
            y2 = y1 + cell_h

            # 背景
            bg_color = (255, 255, 255)

            if day != 0 and today.year == year and today.month == month and today.day == day:
                bg_color = COLOR_TODAY_BG

            draw.rectangle((x1, y1, x2, y2), fill=bg_color, outline=COLOR_GRID)

            if day == 0:
                continue

            # 日付文字
            day_color = COLOR_TEXT
            if col_idx == 0:
                day_color = COLOR_SUN
            elif col_idx == 6:
                day_color = COLOR_SAT

            day_text = str(day)
            draw.text((x1 + 10, y1 + 8), day_text, fill=day_color, font=day_font)

            date_key = f"{year:04d}-{month:02d}-{day:02d}"
            day_events = events_by_date.get(date_key, [])

            # 今日マーク
            if today.year == year and today.month == month and today.day == day:
                badge_r = 16
                cx = x2 - 20
                cy = y1 + 20
                draw.ellipse((cx - badge_r, cy - badge_r, cx + badge_r, cy + badge_r), fill=(52, 152, 219))
                tw2, th2 = get_text_size(draw, "今日", small_font)
                draw.text((cx - tw2 / 2, cy - th2 / 2), "今日", fill=(255, 255, 255), font=small_font)

            # 予定表示
            event_start_y = y1 + 42
            max_show = 2

            for idx, evt in enumerate(day_events[:max_show]):
                evt_type = evt.get("type", "other")
                evt_color = TYPE_COLORS.get(evt_type, TYPE_COLORS["other"])
                label = event_short_label(evt)

                line_y = event_start_y + idx * 28

                # 左の色バー
                draw.rounded_rectangle(
                    (x1 + 10, line_y + 3, x1 + 18, line_y + 21),
                    radius=3,
                    fill=evt_color
                )

                # ラベル
                max_label_len = 10
                if len(label) > max_label_len:
                    label = label[:max_label_len] + "…"

                draw.text((x1 + 24, line_y), label, fill=COLOR_EVENT_TEXT, font=event_font)

            if len(day_events) > max_show:
                more_text = f"+{len(day_events) - max_show}件"
                draw.text((x1 + 24, event_start_y + max_show * 28), more_text, fill=COLOR_SUBTEXT, font=small_font)

    # 凡例
    legend_y = height - bottom_legend_h + 10
    legend_items = [
        ("deadline", "締切"),
        ("intern", "インターン"),
        ("interview", "面接"),
        ("seminar", "説明会"),
        ("test", "テスト"),
        ("other", "その他"),
    ]

    start_x = 50
    gap_x = 210

    for idx, (key, label) in enumerate(legend_items):
        lx = start_x + idx * gap_x
        color = TYPE_COLORS[key]

        draw.ellipse((lx, legend_y + 10, lx + 24, legend_y + 34), fill=color)
        draw.text((lx + 34, legend_y + 8), label, fill=COLOR_TEXT, font=legend_font)

    # PNG化
    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return output