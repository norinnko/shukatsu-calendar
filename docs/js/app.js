/**
 * app.js - メインアプリケーション
 */
(async () => {
  const loading = document.getElementById('loading');
  const calendarView = document.getElementById('calendar-view');
  const listView = document.getElementById('list-view');
  const navBtns = document.querySelectorAll('.nav-btn');
  const typeFilter = document.getElementById('type-filter');

  let currentYear, currentMonth;
  let allEvents = [];

  // === 初期化 ===
  async function init() {
    loading.classList.add('active');

    const now = new Date();
    currentYear = now.getFullYear();
    currentMonth = now.getMonth() + 1;

    // ビュー切り替え
    navBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        navBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const view = btn.dataset.view;
        calendarView.classList.toggle('active', view === 'calendar');
        listView.classList.toggle('active', view === 'list');
        if (view === 'list') renderList();
      });
    });

    // 月移動
    document.getElementById('prev-month').addEventListener('click', () => {
      currentMonth--;
      if (currentMonth < 1) { currentMonth = 12; currentYear--; }
      renderCalendar();
    });

    document.getElementById('next-month').addEventListener('click', () => {
      currentMonth++;
      if (currentMonth > 12) { currentMonth = 1; currentYear++; }
      renderCalendar();
    });

    // フィルタ
    typeFilter.addEventListener('change', renderList);

    // スワイプ対応
    let touchStartX = 0;
    calendarView.addEventListener('touchstart', e => {
      touchStartX = e.touches[0].clientX;
    }, { passive: true });

    calendarView.addEventListener('touchend', e => {
      const diff = e.changedTouches[0].clientX - touchStartX;
      if (Math.abs(diff) > 80) {
        if (diff > 0) {
          // 右スワイプ → 前月
          currentMonth--;
          if (currentMonth < 1) { currentMonth = 12; currentYear--; }
        } else {
          // 左スワイプ → 次月
          currentMonth++;
          if (currentMonth > 12) { currentMonth = 1; currentYear++; }
        }
        renderCalendar();
      }
    }, { passive: true });

    // データ取得
    allEvents = await EventStore.fetchEvents();

    Calendar.init(currentYear, currentMonth, (dateStr) => {
      Calendar.showDayDetail(dateStr, allEvents);
    });

    renderCalendar();
    loading.classList.remove('active');
  }

  // === カレンダー描画 ===
  function renderCalendar() {
    const monthEvents = EventStore.getEventsByMonth(currentYear, currentMonth);
    Calendar.render(currentYear, currentMonth, monthEvents);
    document.getElementById('day-detail').classList.add('hidden');
  }

  // === リスト描画 ===
  function renderList() {
    const container = document.getElementById('event-list');
    const filterType = typeFilter.value;
    let upcoming = EventStore.getUpcomingEvents(90);

    if (filterType !== 'all') {
      upcoming = upcoming.filter(e => e.type === filterType);
    }

    if (upcoming.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state__icon">📋</div>
          <p class="empty-state__text">
            表示する予定がありません。<br>
            LINEボットから予定を追加しましょう！
          </p>
        </div>`;
      return;
    }

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    container.innerHTML = upcoming.map(evt => {
      const evtDate = new Date(evt.date);
      const daysLeft = Math.ceil((evtDate - today) / (1000 * 60 * 60 * 24));

      let countdown, countdownClass;
      if (daysLeft === 0) {
        countdown = '今日！';
        countdownClass = 'urgent';
      } else if (daysLeft <= 7) {
        countdown = `あと${daysLeft}日`;
        countdownClass = 'urgent';
      } else if (daysLeft <= 14) {
        countdown = `あと${daysLeft}日`;
        countdownClass = 'warning';
      } else {
        countdown = `あと${daysLeft}日`;
        countdownClass = 'normal';
      }

      const weekdays = ['日', '月', '火', '水', '木', '金', '土'];
      const dateLabel = `${evtDate.getMonth() + 1}/${evtDate.getDate()}（${weekdays[evtDate.getDay()]}）`;
      const time = evt.time ? ` ${evt.time}` : '';
      const memo = evt.memo ? `<div class="event-card__memo">📝 ${evt.memo}</div>` : '';

      return `
        <div class="event-card" data-type="${evt.type || 'other'}">
          <div class="event-card__header">
            <span class="event-card__company">${evt.company || '未設定'}</span>
            <span class="event-card__countdown ${countdownClass}">${countdown}</span>
          </div>
          <div class="event-card__title">${evt.title || '予定'}</div>
          <div class="event-card__date">📅 ${dateLabel}${time}</div>
          ${memo}
        </div>`;
    }).join('');
  }

  init();
})();
