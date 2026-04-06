"""
カレンダー画像生成モジュール
Pillowで月間カレンダーを描画し、イベントを色ドットで表示する
"""
import calendar
import io
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont


TYPE_COLORS = {
    "deadline": (231, 76, 60),
    "intern": (52, 152, 219),
    "interview": (46, 204, 113),
    "seminar": (155, 89, 182),
    "test": (230, 126, 34),
    "other": (149, 165, 166),
}

IMG_WIDTH = 1040
IMG_HEIGHT = 1040
BG_COLOR = (255, 255, 255)
TEXT_COLOR = (52, 73, 94)
HEADER_BG = (74, 144, 226)
HEADER_TEXT = (255, 255, 255)
TODAY_CIRCLE = (74, 144, 226)
GRID_COLOR = (236, 240, 241)
SAT_COLOR = (52, 152, 219)
SUN_COLOR = (231, 76, 60)
WEEKDAY_NAMES = ["月", "火", "水", "木", "金", "土", "日"]


def get_font(size):
    """日本語フォントを取得"""
    font_paths = [
        os.path.join(os.path.dirname(__file__), "fonts", "NotoSansJP-Regular.ttf"),
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def generate_calendar_image(year, month, events):
    """月間カレンダー画像を生成しBytesIOで返す"""
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_header = get_font(48)
    font_weekday = get_font(28)
    font_day = get_font(36)
    font_legend = get_font(20)

    # ヘッダー
    header_height = 100
    draw.rectangle([(0, 0), (IMG_WIDTH, header_height)], fill=HEADER_BG)
    header_text = f"{year}年 {month}月"
    bbox = draw.textbbox((0, 0), header_text, font=font_header)
    text_w = bbox[2] - bbox[0]
    draw.text(((IMG_WIDTH - text_w) / 2, 25), header_text, fill=HEADER_TEXT, font=font_header)

    # 曜日行
    weekday_y = header_height + 20
    cell_width = IMG_WIDTH / 7
    for i, name in enumerate(WEEKDAY_NAMES):
        x = i * cell_width + cell_width / 2
        color = SAT_COLOR if i == 5 else SUN_COLOR if i == 6 else TEXT_COLOR
        bbox = draw.textbbox((0, 0), name, font=font_weekday)
        tw = bbox[2] - bbox[0]
        draw.text((x - tw / 2, weekday_y), name, fill=color, font=font_weekday)

    # 日付グリッド
    grid_top = weekday_y + 50
    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(year, month)
    cell_height = (IMG_HEIGHT - grid_top - 80) / len(month_days)

    today = datetime.now()
    is_current_month = today.year == year and today.month == month

    # イベントを日付ごとにグループ化
    events_by_day = {}
    for evt in events:
        try:
            day = int(evt["date"].split("-")[2])
            events_by_day.setdefault(day, []).append(evt)
        except (ValueError, IndexError):
            continue

    for week_idx, week in enumerate(month_days):
        y = grid_top + week_idx * cell_height
        draw.line([(0, y), (IMG_WIDTH, y)], fill=GRID_COLOR, width=1)

        for day_idx, day in enumerate(week):
            if day == 0:
                continue

            x = day_idx * cell_width
            center_x = x + cell_width / 2
            text_y = y + 10

            if is_current_month and day == today.day:
                r = 22
                draw.ellipse(
                    [(center_x - r, text_y - 2), (center_x + r, text_y + r * 2 - 2)],
                    fill=TODAY_CIRCLE,
                )
                day_color = (255, 255, 255)
            else:
                day_color = SAT_COLOR if day_idx == 5 else SUN_COLOR if day_idx == 6 else TEXT_COLOR

            day_text = str(day)
            bbox = draw.textbbox((0, 0), day_text, font=font_day)
            tw = bbox[2] - bbox[0]
            draw.text((center_x - tw / 2, text_y), day_text, fill=day_color, font=font_day)

            if day in events_by_day:
                dot_y = text_y + 48
                dot_types = list({e["type"] for e in events_by_day[day]})
                dot_r = 6
                dot_spacing = 18
                start_x = center_x - (len(dot_types) - 1) * dot_spacing / 2
                for dot_idx, evt_type in enumerate(dot_types):
                    dot_x = start_x + dot_idx * dot_spacing
                    color = TYPE_COLORS.get(evt_type, TYPE_COLORS["other"])
                    draw.ellipse(
                        [(dot_x - dot_r, dot_y - dot_r), (dot_x + dot_r, dot_y + dot_r)],
                        fill=color,
                    )

    # 凡例
    legend_y = IMG_HEIGHT - 60
    draw.line([(20, legend_y - 10), (IMG_WIDTH - 20, legend_y - 10)], fill=GRID_COLOR, width=1)
    legend_items = [
        ("deadline", "締切"), ("intern", "インターン"), ("interview", "面接"),
        ("seminar", "説明会"), ("test", "テスト"), ("other", "その他"),
    ]
    legend_x = 30
    for evt_type, label in legend_items:
        color = TYPE_COLORS[evt_type]
        draw.ellipse([(legend_x, legend_y + 2), (legend_x + 14, legend_y + 16)], fill=color)
        draw.text((legend_x + 20, legend_y), label, fill=TEXT_COLOR, font=font_legend)
        bbox = draw.textbbox((0, 0), label, font=font_legend)
        legend_x += (bbox[2] - bbox[0]) + 45

    output = io.BytesIO()
    img.save(output, format="PNG", quality=95)
    output.seek(0)
    return output
