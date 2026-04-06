/**
 * calendar.js - カレンダーグリッド描画
 */
const Calendar = (() => {
  const TYPE_COLORS = {
    deadline: '#E74C3C',
    intern: '#3498DB',
    interview: '#2ECC71',
    seminar: '#9B59B6',
    test: '#E67E22',
    other: '#95A5A6',
  };

  const TYPE_LABELS = {
    deadline: '締切',
    intern: 'インターン',
    interview: '面接',
    seminar: '説明会',
    test: 'テスト',
    other: 'その他',
  };

  let currentYear, currentMonth;
  let onDayClick = null;

  function init(year, month, dayClickCallback) {
    currentYear = year;
    currentMonth = month;
    onDayClick = dayClickCallback;
  }

  function render(year, month, events) {
    currentYear = year;
    currentMonth = month;

    const grid = document.getElementById('calendar-grid');
    const label = document.getElementById('month-label');
    label.textContent = `${year}年${month}月`;

    // イベントを日付ごとにマップ
    const eventMap = {};
    events.forEach(evt => {
      const day = parseInt(evt.date.split('-')[2], 10);
      if (!eventMap[day]) eventMap[day] = [];
      eventMap[day].push(evt.type || 'other');
    });

    // 月のカレンダーを計算（月曜始まり）
    const firstDay = new Date(year, month - 1, 1);
    const lastDate = new Date(year, month, 0).getDate();
    let startDow = firstDay.getDay(); // 0=日
    startDow = startDow === 0 ? 6 : startDow - 1; // 月曜=0

    const today = new Date();
    const isCurrentMonth = today.getFullYear() === year && today.getMonth() + 1 === month;
    const todayDate = today.getDate();

    let html = '';

    // 前月の空白
    for (let i = 0; i < startDow; i++) {
      html += '<div class="cal-day empty"></div>';
    }

    // 日付
    for (let d = 1; d <= lastDate; d++) {
      const dow = (startDow + d - 1) % 7;
      const isToday = isCurrentMonth && d === todayDate;
      const isSat = dow === 5;
      const isSun = dow === 6;

      let cls = 'cal-day';
      if (isToday) cls += ' today';
      if (isSat) cls += ' sat';
      if (isSun) cls += ' sun';

      const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`;

      let dots = '';
      if (eventMap[d]) {
        const unique = [...new Set(eventMap[d])].slice(0, 4);
        dots = '<div class="cal-day__dots">';
        unique.forEach(t => {
          dots += `<div class="cal-day__dot" style="background:${TYPE_COLORS[t] || TYPE_COLORS.other}"></div>`;
        });
        dots += '</div>';
      }

      html += `<div class="${cls}" data-date="${dateStr}">
        <span class="cal-day__num">${d}</span>
        ${dots}
      </div>`;
    }

    grid.innerHTML = html;

    // クリックイベント
    grid.querySelectorAll('.cal-day:not(.empty)').forEach(el => {
      el.addEventListener('click', () => {
        if (onDayClick) onDayClick(el.dataset.date);
      });
    });
  }

  function showDayDetail(dateStr, events) {
    const detail = document.getElementById('day-detail');
    const dayEvents = events.filter(e => e.date === dateStr);

    if (dayEvents.length === 0) {
      detail.classList.add('hidden');
      return;
    }

    const d = new Date(dateStr);
    const weekdays = ['日', '月', '火', '水', '木', '金', '土'];
    const dateLabel = `${d.getMonth() + 1}/${d.getDate()}（${weekdays[d.getDay()]}）`;

    let html = `<h3 class="day-detail__title">📅 ${dateLabel}の予定</h3>`;

    dayEvents.forEach(evt => {
      const color = TYPE_COLORS[evt.type] || TYPE_COLORS.other;
      const label = TYPE_LABELS[evt.type] || 'その他';
      const time = evt.time ? ` ${evt.time}` : '';
      const memo = evt.memo ? `<div style="font-size:12px;color:#7F8C8D;margin-top:4px;">📝 ${evt.memo}</div>` : '';

      html += `
        <div class="day-detail__item">
          <span class="day-detail__type-badge" style="background:${color}">${label}</span>
          <div>
            <div style="font-weight:600;font-size:14px;">${evt.company || ''}</div>
            <div style="font-size:13px;color:#7F8C8D;">${evt.title}${time}</div>
            ${memo}
          </div>
        </div>`;
    });

    detail.innerHTML = html;
    detail.classList.remove('hidden');
  }

  return { init, render, showDayDetail, TYPE_COLORS, TYPE_LABELS };
})();
