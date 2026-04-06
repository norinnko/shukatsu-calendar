"""
カレンダー画像生成モジュール
完全版（日本語対応・マス内予定表示）
"""
import calendar
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent
FONT_PATH = BASE_DIR / "fonts" / "NotoSansJP-Regular.ttf"

# 色設定
COLOR_BG = (248, 250, 252)
COLOR_WHITE = (255, 255, 255)
COLOR_HEADER = (66, 133, 244)
COLOR_HEADER_TEXT = (255, 255, 255)
COLOR_WEEK_BG = (243, 246, 250)
COLOR_GRID = (210, 218, 230)
COLOR_TEXT = (40, 50, 65)
COLOR_SUBTEXT = (95, 105, 120)
COLOR_SUN = (220, 70, 70)
COLOR_SAT = (60, 120, 220)
COLOR_TODAY_BG = (227, 239, 255)
COLOR_TODAY_BADGE = (52, 152, 219)

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
    except Exception as e:
        print("FONT LOAD ERROR:", e)
    return ImageFont.load_default()


def get_text_size(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def group_events_by_date(events):
    grouped = {}
    for evt in events:
        date_str = evt.get("date", "")
        grouped.setdefault(date_str, []).append(evt)
    return grouped


def event_short_label(event):
    """
    マス内に表示する短いラベル
    例:
    - Google 面接
    - テスト株… 締切
    - Amazon 説明会
    """
    evt_type = event.get("type", "other")
    company = (event.get("company") or "").strip()
    title = (event.get("title") or "").strip()

    if evt_type == "deadline":
        base = "締切"
    elif evt_type == "interview":
        base = "面接"
    elif evt_type == "seminar":
        base = "説明会"
    elif evt_type == "intern":
        base = "インターン"
    elif evt_type == "test":
        base = "テスト"
    else:
        base = title if title else "予定"

    if company:
        short_company = company
        if len(short_company) > 6:
            short_company = short_company[:6] + "…"
        label = f"{short_company} {base}"
    else:
        label = base

    if len(label) > 12:
        label = label[:12] + "…"

    return label


def generate_calendar_image(year, month, events):
    """
    カレンダー画像を生成して BytesIO を返す
    events: [
        {
            "date": "YYYY-MM-DD",
            "company": "...",
            "title": "...",
            "type": "deadline|intern|interview|seminar|test|other"
        }
    ]
    """
    width = 1400
    height = 1600

    margin_x = 35
    margin_top = 20
    header_h = 110
    weekday_h = 55
    legend_h = 110
    bottom_margin = 25

    grid_top = margin_top + header_h + weekday_h
    grid_bottom = height - legend_h - bottom_margin
    grid_height = grid_bottom - grid_top

    cell_w = (width - margin_x * 2) // 7
    cell_h = grid_height // 6

    image = Image.new("RGB", (width, height), COLOR_BG)
    draw = ImageDraw.Draw(image)

    # フォント
    title_font = load_font(38)
    weekday_font = load_font(24)
    day_font = load_font(24)
    event_font = load_font(18)
    small_font = load_font(16)
    legend_font = load_font(20)

    # ヘッダー
    draw.rounded_rectangle(
        (margin_x, margin_top, width - margin_x, margin_top + header_h),
        radius=18,
        fill=COLOR_HEADER
    )
    title_text = f"{year}年{month}月"
    tw, th = get_text_size(draw, title_text, title_font)
    draw.text(
        ((width - tw) / 2, margin_top + (header_h - th) / 2),
        title_text,
        fill=COLOR_HEADER_TEXT,
        font=title_font
    )

    # 曜日
    weekdays = ["日", "月", "火", "水", "木", "金", "土"]
    week_y1 = margin_top + header_h
    week_y2 = week_y1 + weekday_h

    for i, wd in enumerate(weekdays):
        x1 = margin_x + i * cell_w
        x2 = x1 + cell_w

        draw.rectangle((x1, week_y1, x2, week_y2), fill=COLOR_WEEK_BG, outline=COLOR_GRID)

        color = COLOR_TEXT
        if i == 0:
            color = COLOR_SUN
        elif i == 6:
            color = COLOR_SAT

        ww, wh = get_text_size(draw, wd, weekday_font)
        draw.text(
            (x1 + (cell_w - ww) / 2, week_y1 + (weekday_h - wh) / 2),
            wd,
            fill=color,
            font=weekday_font
        )

    # カレンダー計算
    cal = calendar.Calendar(firstweekday=6)  # 日曜始まり
    month_days = cal.monthdayscalendar(year, month)
    while len(month_days) < 6:
        month_days.append([0] * 7)

    events_by_date = group_events_by_date(events)
    today = datetime.now()

    # 各日セル
    for row_idx, week in enumerate(month_days):
        for col_idx, day in enumerate(week):
            x1 = margin_x + col_idx * cell_w
            y1 = grid_top + row_idx * cell_h
            x2 = x1 + cell_w
            y2 = y1 + cell_h

            is_today = (
                day != 0 and
                today.year == year and
                today.month == month and
                today.day == day
            )

            bg_color = COLOR_TODAY_BG if is_today else COLOR_WHITE
            draw.rectangle((x1, y1, x2, y2), fill=bg_color, outline=COLOR_GRID)

            if day == 0:
                continue

            # 日付
            day_color = COLOR_TEXT
            if col_idx == 0:
                day_color = COLOR_SUN
            elif col_idx == 6:
                day_color = COLOR_SAT

            draw.text((x1 + 10, y1 + 8), str(day), fill=day_color, font=day_font)

            # 今日バッジ
            if is_today:
                badge_r = 16
                cx = x2 - 20
                cy = y1 + 20
                draw.ellipse(
                    (cx - badge_r, cy - badge_r, cx + badge_r, cy + badge_r),
                    fill=COLOR_TODAY_BADGE
                )
                tw2, th2 = get_text_size(draw, "今日", small_font)
                draw.text(
                    (cx - tw2 / 2, cy - th2 / 2),
                    "今日",
                    fill=(255, 255, 255),
                    font=small_font
                )

            # 予定
            date_key = f"{year:04d}-{month:02d}-{day:02d}"
            day_events = events_by_date.get(date_key, [])

            event_start_y = y1 + 42
            line_gap = 28
            max_show = 2

            for idx, evt in enumerate(day_events[:max_show]):
                evt_type = evt.get("type", "other")
                evt_color = TYPE_COLORS.get(evt_type, TYPE_COLORS["other"])
                label = event_short_label(evt)

                line_y = event_start_y + idx * line_gap

                # 色バー
                draw.rounded_rectangle(
                    (x1 + 10, line_y + 3, x1 + 18, line_y + 21),
                    radius=3,
                    fill=evt_color
                )

                # 文字
                draw.text(
                    (x1 + 24, line_y),
                    label,
                    fill=COLOR_TEXT,
                    font=event_font
                )

            # 追加件数
            if len(day_events) > max_show:
                more_text = f"+{len(day_events) - max_show}件"
                draw.text(
                    (x1 + 24, event_start_y + max_show * line_gap),
                    more_text,
                    fill=COLOR_SUBTEXT,
                    font=small_font
                )

    # 凡例
    legend_y = height - legend_h + 10
    legend_items = [
        ("deadline", "締切"),
        ("intern", "インターン"),
        ("interview", "面接"),
        ("seminar", "説明会"),
        ("test", "テスト"),
        ("other", "その他"),
    ]

    start_x = 45
    gap_x = 220

    for idx, (key, label) in enumerate(legend_items):
        lx = start_x + idx * gap_x
        color = TYPE_COLORS[key]

        draw.ellipse((lx, legend_y + 14, lx + 24, legend_y + 38), fill=color)
        draw.text((lx + 34, legend_y + 11), label, fill=COLOR_TEXT, font=legend_font)

    output = BytesIO()
    image.save(output, format="PNG")
    output.seek(0)
    return output