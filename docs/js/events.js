/**
 * events.js - GitHub APIからイベントデータを取得・管理
 */
const EventStore = (() => {
  // ★ ここを自分のリポジトリに変更
  const GITHUB_REPO = 'username/shukatsu-calendar';
  const FILE_PATH = 'data/events.json';
  const API_URL = `https://api.github.com/repos/${GITHUB_REPO}/contents/${FILE_PATH}`;
  const CACHE_KEY = 'shukatsu_events_cache';
  const CACHE_TTL = 5 * 60 * 1000; // 5分キャッシュ

  let _events = [];
  let _lastFetch = 0;

  async function fetchEvents(force = false) {
    const now = Date.now();
    // キャッシュが有効ならそれを返す
    if (!force && _events.length > 0 && now - _lastFetch < CACHE_TTL) {
      return _events;
    }

    try {
      const resp = await fetch(API_URL, {
        headers: { 'Accept': 'application/vnd.github.v3+json' }
      });

      if (!resp.ok) throw new Error(`GitHub API error: ${resp.status}`);

      const data = await resp.json();
      const content = atob(data.content);
      _events = JSON.parse(content);
      _lastFetch = now;

      // ローカルキャッシュにも保存（オフライン用）
      try {
        localStorage.setItem(CACHE_KEY, JSON.stringify({
          events: _events,
          timestamp: now
        }));
      } catch (e) { /* ignore */ }

      return _events;
    } catch (err) {
      console.error('Failed to fetch events:', err);
      // オフラインフォールバック
      try {
        const cached = JSON.parse(localStorage.getItem(CACHE_KEY));
        if (cached && cached.events) {
          _events = cached.events;
          return _events;
        }
      } catch (e) { /* ignore */ }
      return [];
    }
  }

  function getEventsByMonth(year, month) {
    const prefix = `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}`;
    return _events.filter(e => e.date && e.date.startsWith(prefix));
  }

  function getUpcomingEvents(days = 60) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const end = new Date(today);
    end.setDate(end.getDate() + days);

    return _events
      .filter(e => {
        if (e.status !== 'upcoming') return false;
        const d = new Date(e.date);
        return d >= today && d <= end;
      })
      .sort((a, b) => a.date.localeCompare(b.date));
  }

  function getEventsByDate(dateStr) {
    return _events.filter(e => e.date === dateStr);
  }

  return { fetchEvents, getEventsByMonth, getUpcomingEvents, getEventsByDate };
})();
