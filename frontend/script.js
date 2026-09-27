// ==========================================================================
// 日語雲端學習助手 - 前端核心互動邏輯腳本 (JavaScript)
// 包含：Google 登入驗證、修真五重境界、新手試煉（五十音圖與三大迷你遊戲）、
//      YouTube 官方合法雙語字典（懸浮暫停與分詞一鍵收藏）、3D 生詞卡、
//      單字測驗遊戲與 Combo、GitHub 綠色貢獻熱力圖、意見反饋與 PWA 支援
// ==========================================================================

// --------------------------------------------------------------------------
// 全域狀態管理中心 (Global State)
// --------------------------------------------------------------------------
const state = {
  currentUser: null,           // 當前登入的使用者個人檔案物件
  activeTab: "novice",         // 當前啟用的主導航分頁：novice | video | flashcard | quiz | streak | vocab
  allWords: [],                // 雲端生詞庫全體單字清單
  filteredCards: [],           // 生詞卡模式依掌握度篩選後卡片清單
  cardIndex: 0,                // 生詞卡當前索引
  isFlipped: false,            // 3D 生詞卡是否已翻面
  cardFilter: "all",           // 生詞卡過濾條件

  // 影音字典專用狀態
  mediaList: [],               // 官方影音清單
  currentMedia: null,          // 當前播放的影音項目
  ytPlayer: null,              // YouTube Iframe Player 實例
  isYtReady: false,            // YouTube API 是否已就緒
  subInterval: null,           // 字幕同步計時器
  userSubJa: true,             // 使用者日文字幕開關
  userSubZh: true,             // 使用者中文字幕開關

  // 新手試煉專用狀態
  noviceSubTab: "kana",        // 新手試煉子分頁：kana | game1 | game2 | game3
  // 試煉一（翻牌）
  g1Cards: [],
  g1FlippedIndices: [],
  g1MatchedCount: 0,
  g1TotalFlips: 0,
  // 試煉二（聽音辨字）
  g2Questions: [],
  g2Index: 0,
  g2Correct: 0,
  // 試煉三（羅馬音打字）
  g3Questions: [],
  g3Index: 0,
  g3Correct: 0,

  // 單字測驗遊戲專用狀態
  quizQuestions: [],
  quizIndex: 0,
  quizScore: 0,
  quizCombo: 0,
  quizMaxCombo: 0,
  quizCorrectCount: 0,
  quizWrongWords: [],
  quizMode: "multiple_choice",
  quizPool: "all",
  quizCount: 10,
  isSubmitting: false,

  // 打卡日曆狀態
  streakData: null,
  calYear: new Date().getFullYear(),
  calMonth: new Date().getMonth() + 1,

  // 徽章與能力定級狀態 (New v3.1)
  userBadges: [],              // 使用者徽章成就清單
  badgeFilter: "all",          // 徽章館篩選分類：all | 境界徽章 | 里程碑成就
  onboardingTargetTier: "新手小白", // 定級挑戰目標境界
  placementQuestions: [],      // 定級考卷題目
  placementAnswers: {}         // 定級作答紀錄
};

// --------------------------------------------------------------------------
// PWA Service Worker 註冊器
// --------------------------------------------------------------------------
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js")
      .then(reg => console.log("[PWA] Service Worker 註冊就緒，範疇:", reg.scope))
      .catch(err => console.warn("[PWA] Service Worker 註冊失敗:", err));
  });
}

// --------------------------------------------------------------------------
// 原生 Web Speech API 語音朗讀合成（零外部付費 API、本機自然發音）
// --------------------------------------------------------------------------
function playJapaneseAudio(text) {
  if (!("speechSynthesis" in window)) {
    console.warn("瀏覽器不支援 Web Speech API");
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "ja-JP";
  utterance.rate = 0.9;
  utterance.pitch = 1.0;
  const voices = window.speechSynthesis.getVoices();
  const jaVoice = voices.find(v => v.lang === "ja-JP" || v.lang === "ja_JP" || v.lang.includes("ja"));
  if (jaVoice) utterance.voice = jaVoice;
  window.speechSynthesis.speak(utterance);
}

// --------------------------------------------------------------------------
// Web Audio API 輕量合成音效
// --------------------------------------------------------------------------
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

function playSuccessChime() {
  if (audioCtx.state === "suspended") audioCtx.resume();
  const now = audioCtx.currentTime;
  [659.25, 987.77].forEach((freq, i) => {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(freq, now + i * 0.1);
    gain.gain.setValueAtTime(0.15, now + i * 0.1);
    gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.1 + 0.35);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start(now + i * 0.1);
    osc.stop(now + i * 0.1 + 0.35);
  });
}

function playWrongBuzzer() {
  if (audioCtx.state === "suspended") audioCtx.resume();
  const now = audioCtx.currentTime;
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.type = "triangle";
  osc.frequency.setValueAtTime(220, now);
  osc.frequency.linearRampToValueAtTime(140, now + 0.25);
  gain.gain.setValueAtTime(0.2, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
  osc.connect(gain);
  gain.connect(audioCtx.destination);
  osc.start(now);
  osc.stop(now + 0.25);
}

// --------------------------------------------------------------------------
// Toast 提示訊息工具函式
// --------------------------------------------------------------------------
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = "toast";
  const icon = type === "success" ? "✅" : type === "error" ? "❌" : "💡";
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(20px)";
    setTimeout(() => toast.remove(), 300);
  }, 3200);
}

// --------------------------------------------------------------------------
// Google 登入驗證與 Mandatory Login Gate
// --------------------------------------------------------------------------
async function handleUserLogin(userData) {
  try {
    const res = await fetch("/api/user/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(userData)
    });
    if (!res.ok) throw new Error("登入請求失敗");
    const user = await res.json();
    state.currentUser = user;
    localStorage.setItem("jp_user_uid", user.uid);
    localStorage.setItem("jp_user_data", JSON.stringify(user));

    // 關閉登入遮罩並更新介面
    document.getElementById("loginGateOverlay").style.display = "none";
    updateUserInterface();
    showToast(`歡迎回來，${user.display_name}！當前境界：【${user.user_level}】`, "success");

    // 載入全站核心資料
    await loadInitialData();

    // v3.1 新手動態定級引導：若尚未完成定級測試，開啟沈浸式動態能力定級視窗
    if (!user.onboarding_completed) {
      openPlacementModal();
    }
  } catch (err) {
    console.error("登入錯誤:", err);
    showToast("登入過程發生錯誤，請稍後再試", "error");
  }
}

function handleLogout() {
  state.currentUser = null;
  localStorage.removeItem("jp_user_uid");
  localStorage.removeItem("jp_user_data");
  document.getElementById("loginGateOverlay").style.display = "flex";
  showToast("已成功登出", "info");
}

function updateUserInterface() {
  const user = state.currentUser;
  if (!user) return;

  // 頂部導航列個人資訊更新
  const avatarEl = document.getElementById("navUserAvatar");
  const nameEl = document.getElementById("navUserName");
  const levelEl = document.getElementById("navUserLevel");

  if (avatarEl) avatarEl.src = user.photo_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${user.uid}`;
  if (nameEl) nameEl.textContent = user.display_name;
  if (levelEl) {
    levelEl.textContent = user.user_level;
    levelEl.className = `level-tag ${getLevelClass(user.user_level)}`;
  }

  // 新手試煉堂看板更新
  const gateLevelBadge = document.getElementById("gateCurrentLevelBadge");
  if (gateLevelBadge) {
    gateLevelBadge.textContent = user.user_level;
    gateLevelBadge.className = `gate-level-badge ${getLevelClass(user.user_level)}`;
  }

  const metricKanaStatus = document.getElementById("metricKanaStatus");
  if (metricKanaStatus) {
    metricKanaStatus.textContent = user.kana_completed ? "已完成 ✅" : "未完成 ❌";
    metricKanaStatus.style.color = user.kana_completed ? "var(--srs-mastered)" : "var(--srs-hard)";
  }

  const g1Acc = document.getElementById("metricGame1Acc");
  if (g1Acc) g1Acc.textContent = `${user.game1_acc}%`;
  const g2Acc = document.getElementById("metricGame2Acc");
  if (g2Acc) g2Acc.textContent = `${user.game2_acc}%`;
  const g3Acc = document.getElementById("metricGame3Acc");
  if (g3Acc) g3Acc.textContent = `${user.game3_acc}%`;

  // 影音字典權限鎖定控制
  const isNovice = user.user_level === "新手小白";
  const videoLock = document.getElementById("videoLockOverlay");
  const lockIndicator = document.getElementById("videoLockIndicator");
  const lockUserLevelText = document.getElementById("lockUserLevelText");
  if (videoLock) videoLock.style.display = isNovice ? "flex" : "none";
  if (lockIndicator) lockIndicator.style.display = isNovice ? "inline" : "none";
  if (lockUserLevelText) lockUserLevelText.textContent = user.user_level;

  // 個人偏好視窗更新
  const prefAvatar = document.getElementById("prefUserAvatar");
  const prefName = document.getElementById("prefUserName");
  const prefEmail = document.getElementById("prefUserEmail");
  const prefLevel = document.getElementById("prefUserLevel");

  if (prefAvatar) prefAvatar.src = user.photo_url || `https://api.dicebear.com/7.x/bottts/svg?seed=${user.uid}`;
  if (prefName) prefName.textContent = user.display_name;
  if (prefEmail) prefEmail.textContent = user.email;
  if (prefLevel) prefLevel.textContent = `修真境界：${user.user_level}`;

  // 勾選既有興趣標籤
  const checkboxes = document.querySelectorAll("#hobbyTagsSelector input[type='checkbox']");
  checkboxes.forEach(cb => {
    cb.checked = (user.hobbies || []).includes(cb.value);
  });
  updateHobbyCountTip();

  // 字幕預設值
  const prefJa = document.getElementById("prefDefaultSubJa");
  const prefZh = document.getElementById("prefDefaultSubZh");
  if (prefJa) prefJa.checked = user.default_sub_ja;
  if (prefZh) prefZh.checked = user.default_sub_zh;

  state.userSubJa = user.default_sub_ja;
  state.userSubZh = user.default_sub_zh;
  const toggleJa = document.getElementById("toggleSubJa");
  const toggleZh = document.getElementById("toggleSubZh");
  if (toggleJa) toggleJa.checked = user.default_sub_ja;
  if (toggleZh) toggleZh.checked = user.default_sub_zh;
}

function getLevelClass(level) {
  switch (level) {
    case "新手小白": return "level-novice";
    case "外門弟子": return "level-outer";
    case "內門弟子": return "level-inner";
    case "長老": return "level-elder";
    default: return "level-guest";
  }
}

// --------------------------------------------------------------------------
// 系統核心資料初始化載入
// --------------------------------------------------------------------------
async function loadInitialData() {
  await Promise.all([
    fetchWordsList(),
    fetchStudyStats(),
    fetchStreakCalendar(),
    fetchMediaList(),
    fetchUserBadges()
  ]);
  renderFiftyOnGrid();
  initBeginnerGames();
}

async function fetchWordsList() {
  try {
    const res = await fetch("/api/words");
    if (!res.ok) throw new Error("讀取單字失敗");
    state.allWords = await res.json();
    applyCardFilter(state.cardFilter);
    renderVocabTable(state.allWords);
  } catch (err) {
    console.error("載入單字本失敗:", err);
  }
}

async function fetchStudyStats() {
  try {
    const res = await fetch("/api/stats");
    if (!res.ok) throw new Error("讀取統計失敗");
    const stats = await res.json();
    document.getElementById("statTotalWords").textContent = stats.total_words;
    document.getElementById("statMastered").textContent = stats.mastered_count;
    document.getElementById("statNeedPractice").textContent = stats.need_practice_count;
    document.getElementById("statHard").textContent = stats.hard_count;
    document.getElementById("statAccuracy").textContent = `${stats.overall_accuracy}%`;
  } catch (err) {
    console.error("載入統計失敗:", err);
  }
}

async function fetchStreakCalendar(year, month) {
  try {
    const y = year || state.calYear;
    const m = month || state.calMonth;
    const res = await fetch(`/api/streak?year=${y}&month=${m}`);
    if (!res.ok) throw new Error("讀取打卡失敗");
    const data = await res.json();
    state.streakData = data;

    // 更新連續天數
    document.getElementById("statNavStreak").textContent = data.current_streak;
    document.getElementById("streakDaysCount").textContent = data.current_streak;
    document.getElementById("streakLongest").textContent = `${data.longest_streak} 天`;
    document.getElementById("streakTotalDays").textContent = `${data.total_active_days} 天`;
    document.getElementById("streakTodayStatus").textContent = data.today_studied ? "今日已打卡 ✅" : "今日未打卡 ⏳";

    renderGitHubHeatmap(data);
    renderMonthCalendar(data);
  } catch (err) {
    console.error("載入打卡日曆失敗:", err);
  }
}

// --------------------------------------------------------------------------
// 新手試煉堂：五十音圖解與三大迷你小遊戲
// --------------------------------------------------------------------------
const FIFTY_ON_DATA = [
  { h: "あ", k: "ア", r: "a" },  { h: "い", k: "イ", r: "i" },  { h: "う", k: "ウ", r: "u" },  { h: "え", k: "エ", r: "e" },  { h: "お", k: "オ", r: "o" },
  { h: "か", k: "カ", r: "ka" }, { h: "き", k: "キ", r: "ki" }, { h: "く", k: "ク", r: "ku" }, { h: "け", k: "ケ", r: "ke" }, { h: "こ", k: "コ", r: "ko" },
  { h: "さ", k: "サ", r: "sa" }, { h: "し", k: "シ", r: "shi"}, { h: "す", k: "ス", r: "su" }, { h: "せ", k: "セ", r: "se" }, { h: "そ", k: "ソ", r: "so" },
  { h: "た", k: "タ", r: "ta" }, { h: "ち", k: "チ", r: "chi"}, { h: "つ", k: "ツ", r: "tsu"}, { h: "て", k: "テ", r: "te" }, { h: "と", k: "ト", r: "to" },
  { h: "な", k: "ナ", r: "na" }, { h: "に", k: "ニ", r: "ni" }, { h: "ぬ", k: "ヌ", r: "nu" }, { h: "ね", k: "ネ", r: "ne" }, { h: "の", k: "ノ", r: "no" },
  { h: "は", k: "ハ", r: "ha" }, { h: "ひ", k: "ヒ", r: "hi" }, { h: "ふ", k: "フ", r: "fu" }, { h: "へ", k: "ヘ", r: "he" }, { h: "ほ", k: "ホ", r: "ho" },
  { h: "ま", k: "マ", r: "ma" }, { h: "み", k: "ミ", r: "mi" }, { h: "む", k: "ム", r: "mu" }, { h: "め", k: "メ", r: "me" }, { h: "も", k: "モ", r: "mo" },
  { h: "や", k: "ヤ", r: "ya" }, { h: "",   k: "",   r: "" },   { h: "ゆ", k: "ユ", r: "yu" }, { h: "",   k: "",   r: "" },   { h: "よ", k: "ヨ", r: "yo" },
  { h: "ら", k: "ラ", r: "ra" }, { h: "り", k: "リ", r: "ri" }, { h: "る", k: "ル", r: "ru" }, { h: "れ", k: "レ", r: "re" }, { h: "ろ", k: "ロ", r: "ro" },
  { h: "わ", k: "ワ", r: "wa" }, { h: "",   k: "",   r: "" },   { h: "",   k: "",   r: "" },   { h: "",   k: "",   r: "" },   { h: "を", k: "ヲ", r: "wo" },
  { h: "ん", k: "ン", r: "n" }
];

function renderFiftyOnGrid() {
  const container = document.getElementById("kanaGridContainer");
  if (!container) return;
  container.innerHTML = "";

  FIFTY_ON_DATA.forEach(item => {
    if (!item.h) {
      const emptyDiv = document.createElement("div");
      emptyDiv.style.visibility = "hidden";
      container.appendChild(emptyDiv);
      return;
    }
    const card = document.createElement("div");
    card.className = "kana-card";
    card.title = `點擊聆聽「${item.h}」標準發音`;
    card.innerHTML = `
      <div class="kana-hira">${item.h}</div>
      <div class="kana-kata">${item.k}</div>
      <div class="kana-romaji">${item.r}</div>
    `;
    card.addEventListener("click", () => playJapaneseAudio(item.h));
    container.appendChild(card);
  });
}

// 標記完成五十音
async function handleMarkKanaCompleted() {
  if (!state.currentUser) return;
  try {
    const res = await fetch(`/api/beginner/kana-complete?uid=${encodeURIComponent(state.currentUser.uid)}`, {
      method: "POST"
    });
    if (!res.ok) throw new Error("標記失敗");
    const updated = await res.json();
    state.currentUser = updated;
    updateUserInterface();
    showToast("🎉 五十音圖解學習已完成標記！", "success");

    // 檢查是否達成自動晉升
    checkPromotionPopup(updated);
  } catch (err) {
    showToast("更新五十音狀態失敗", "error");
  }
}

// --------------------------------------------------------------------------
// 試煉一：假名翻牌記憶配對 (Memory Match - 4x3)
// --------------------------------------------------------------------------
const G1_PAIRS = [
  { kana: "あ", match: "a" },
  { kana: "か", match: "ka" },
  { kana: "さ", match: "sa" },
  { kana: "た", match: "ta" },
  { kana: "な", match: "na" },
  { kana: "は", match: "ha" }
];

function initGame1() {
  state.g1MatchedCount = 0;
  state.g1TotalFlips = 0;
  state.g1FlippedIndices = [];

  const matchedEl = document.getElementById("g1MatchedPairs");
  const flipsEl = document.getElementById("g1TotalFlips");
  const resultBox = document.getElementById("game1ResultBox");
  if (matchedEl) matchedEl.textContent = "0";
  if (flipsEl) flipsEl.textContent = "0";
  if (resultBox) resultBox.style.display = "none";

  // 建立 12 張牌並隨機洗牌
  const cards = [];
  G1_PAIRS.forEach((p, idx) => {
    cards.push({ id: idx, text: p.kana, type: "kana", audio: p.kana });
    cards.push({ id: idx, text: p.match, type: "romaji", audio: p.kana });
  });
  cards.sort(() => Math.random() - 0.5);
  state.g1Cards = cards;

  const grid = document.getElementById("game1MemoryGrid");
  if (!grid) return;
  grid.innerHTML = "";

  cards.forEach((card, index) => {
    const el = document.createElement("div");
    el.className = "memory-card";
    el.dataset.index = index;
    el.textContent = "❓";
    el.addEventListener("click", () => handleFlipCard(index, el));
    grid.appendChild(el);
  });
}

function handleFlipCard(index, cardEl) {
  if (state.g1FlippedIndices.length >= 2) return;
  if (cardEl.classList.contains("is-flipped") || cardEl.classList.contains("is-matched")) return;

  // 翻開卡片
  cardEl.classList.add("is-flipped");
  const cardData = state.g1Cards[index];
  cardEl.textContent = cardData.text;
  playJapaneseAudio(cardData.audio);

  state.g1FlippedIndices.push(index);
  state.g1TotalFlips++;
  document.getElementById("g1TotalFlips").textContent = state.g1TotalFlips;

  if (state.g1FlippedIndices.length === 2) {
    const [idx1, idx2] = state.g1FlippedIndices;
    const c1 = state.g1Cards[idx1];
    const c2 = state.g1Cards[idx2];
    const el1 = document.querySelector(`.memory-card[data-index='${idx1}']`);
    const el2 = document.querySelector(`.memory-card[data-index='${idx2}']`);

    if (c1.id === c2.id) {
      // 配對成功！
      playSuccessChime();
      el1.classList.add("is-matched");
      el2.classList.add("is-matched");
      state.g1MatchedCount++;
      document.getElementById("g1MatchedPairs").textContent = state.g1MatchedCount;
      state.g1FlippedIndices = [];

      if (state.g1MatchedCount === G1_PAIRS.length) {
        finishGame1();
      }
    } else {
      // 配對失敗，翻回
      playWrongBuzzer();
      setTimeout(() => {
        el1.classList.remove("is-flipped");
        el2.classList.remove("is-flipped");
        el1.textContent = "❓";
        el2.textContent = "❓";
        state.g1FlippedIndices = [];
      }, 900);
    }
  }
}

async function finishGame1() {
  const minFlips = 12;
  const extraFlips = Math.max(0, state.g1TotalFlips - minFlips);
  const accuracy = Math.max(50.0, Math.min(100.0, +(100 - extraFlips * 4).toFixed(1)));
  const score = Math.round(accuracy * 10);

  const resultBox = document.getElementById("game1ResultBox");
  if (resultBox) {
    resultBox.style.display = "block";
    resultBox.innerHTML = `
      <h4 style="font-size: 1.15rem; color: #15803d; margin-bottom: 0.4rem;">🎉 試煉一完成！</h4>
      <p>翻牌總次數：<b>${state.g1TotalFlips}</b> 次 · 本輪結算正確率：<b style="color: var(--primary-color);">${accuracy}%</b></p>
    `;
  }

  await submitBeginnerGame(1, accuracy, score);
}

// --------------------------------------------------------------------------
// 試煉二：假名聽音辨字 (Audio-to-Kana - 5 題)
// --------------------------------------------------------------------------
const G2_POOL = [
  { kana: "あ", options: ["あ", "お", "め", "ぬ"] },
  { kana: "か", options: ["か", "が", "き", "力"] },
  { kana: "さ", options: ["さ", "ち", "き", "ざ"] },
  { kana: "た", options: ["た", "な", "に", "だ"] },
  { kana: "な", options: ["な", "ね", "れ", "わ"] },
  { kana: "は", options: ["は", "ほ", "ば", "ま"] },
  { kana: "ま", options: ["ま", "も", "ほ", "み"] },
  { kana: "ら", options: ["ら", "う", "ろ", "る"] }
];

function initGame2() {
  state.g2Index = 0;
  state.g2Correct = 0;
  state.g2Questions = [...G2_POOL].sort(() => Math.random() - 0.5).slice(0, 5);

  document.getElementById("g2CurrentIndex").textContent = "1";
  document.getElementById("g2CorrectCount").textContent = "0";
  document.getElementById("game2ChallengeCard").style.display = "block";
  document.getElementById("game2ResultBox").style.display = "none";

  renderGame2Question();
}

function renderGame2Question() {
  const currentQ = state.g2Questions[state.g2Index];
  if (!currentQ) {
    finishGame2();
    return;
  }

  document.getElementById("g2CurrentIndex").textContent = state.g2Index + 1;
  const grid = document.getElementById("game2OptionsGrid");
  grid.innerHTML = "";

  // 自動播放目標假名發音
  playJapaneseAudio(currentQ.kana);

  const opts = [...currentQ.options].sort(() => Math.random() - 0.5);
  opts.forEach(opt => {
    const btn = document.createElement("button");
    btn.className = "btn-audio-choice";
    btn.textContent = opt;
    btn.addEventListener("click", () => handleGame2Answer(opt, currentQ.kana));
    grid.appendChild(btn);
  });
}

async function handleGame2Answer(selected, correct) {
  if (selected === correct) {
    playSuccessChime();
    state.g2Correct++;
    document.getElementById("g2CorrectCount").textContent = state.g2Correct;
    showToast("答對了！🎯", "success");
  } else {
    playWrongBuzzer();
    showToast(`答錯囉！正確答案是「${correct}」`, "error");
  }

  state.g2Index++;
  setTimeout(renderGame2Question, 600);
}

async function finishGame2() {
  document.getElementById("game2ChallengeCard").style.display = "none";
  const accuracy = Math.round((state.g2Correct / 5) * 100);
  const score = state.g2Correct * 20;

  const resultBox = document.getElementById("game2ResultBox");
  if (resultBox) {
    resultBox.style.display = "block";
    resultBox.innerHTML = `
      <h4 style="font-size: 1.15rem; color: #15803d; margin-bottom: 0.4rem;">🎧 試煉二完成！</h4>
      <p>答對題數：<b>${state.g2Correct} / 5</b> · 正確率：<b style="color: var(--primary-color);">${accuracy}%</b></p>
    `;
  }

  await submitBeginnerGame(2, accuracy, score);
}

// --------------------------------------------------------------------------
// 試煉三：羅馬拼音打字 (Speed Typing - 5 題)
// --------------------------------------------------------------------------
const G3_POOL = [
  { kana: "あ", romaji: "a" },
  { kana: "か", romaji: "ka" },
  { kana: "さ", romaji: "sa" },
  { kana: "た", romaji: "ta" },
  { kana: "な", romaji: "na" },
  { kana: "は", romaji: "ha" },
  { kana: "ま", romaji: "ma" },
  { kana: "や", romaji: "ya" },
  { kana: "ら", romaji: "ra" },
  { kana: "わ", romaji: "wa" }
];

function initGame3() {
  state.g3Index = 0;
  state.g3Correct = 0;
  state.g3Questions = [...G3_POOL].sort(() => Math.random() - 0.5).slice(0, 5);

  document.getElementById("g3CurrentIndex").textContent = "1";
  document.getElementById("g3CorrectCount").textContent = "0";
  document.getElementById("game3ChallengeCard").style.display = "block";
  document.getElementById("game3ResultBox").style.display = "none";
  document.getElementById("g3FeedbackTip").textContent = "";

  renderGame3Question();
}

function renderGame3Question() {
  const currentQ = state.g3Questions[state.g3Index];
  if (!currentQ) {
    finishGame3();
    return;
  }

  document.getElementById("g3CurrentIndex").textContent = state.g3Index + 1;
  document.getElementById("g3TargetKana").textContent = currentQ.kana;
  const input = document.getElementById("inputGame3Romaji");
  input.value = "";
  input.focus();
  document.getElementById("g3FeedbackTip").textContent = "";
}

async function handleGame3Submit(e) {
  e.preventDefault();
  const currentQ = state.g3Questions[state.g3Index];
  if (!currentQ) return;

  const input = document.getElementById("inputGame3Romaji");
  const val = input.value.trim().toLowerCase();

  if (val === currentQ.romaji.toLowerCase()) {
    playSuccessChime();
    state.g3Correct++;
    document.getElementById("g3CorrectCount").textContent = state.g3Correct;
    document.getElementById("g3FeedbackTip").innerHTML = `<span style="color: var(--srs-mastered);">✅ 正確！「${currentQ.kana}」拼寫為 ${currentQ.romaji}</span>`;
  } else {
    playWrongBuzzer();
    document.getElementById("g3FeedbackTip").innerHTML = `<span style="color: var(--srs-hard);">❌ 錯誤！「${currentQ.kana}」標準拼寫是 ${currentQ.romaji}</span>`;
  }

  state.g3Index++;
  setTimeout(renderGame3Question, 800);
}

async function finishGame3() {
  document.getElementById("game3ChallengeCard").style.display = "none";
  const accuracy = Math.round((state.g3Correct / 5) * 100);
  const score = state.g3Correct * 20;

  const resultBox = document.getElementById("game3ResultBox");
  if (resultBox) {
    resultBox.style.display = "block";
    resultBox.innerHTML = `
      <h4 style="font-size: 1.15rem; color: #15803d; margin-bottom: 0.4rem;">⚡ 試煉三完成！</h4>
      <p>答對題數：<b>${state.g3Correct} / 5</b> · 正確率：<b style="color: var(--primary-color);">${accuracy}%</b></p>
    `;
  }

  await submitBeginnerGame(3, accuracy, score);
}

// 提交新手試煉關卡成績並審核自動晉升
async function submitBeginnerGame(gameId, accuracy, score) {
  if (!state.currentUser) return;
  try {
    const res = await fetch(`/api/beginner/game-submit?uid=${encodeURIComponent(state.currentUser.uid)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ game_id: gameId, accuracy: accuracy, score: score })
    });
    if (!res.ok) throw new Error("成績送出失敗");
    const feedback = await res.json();

    // 更新本地狀態
    state.currentUser.game1_acc = feedback.game1_acc;
    state.currentUser.game2_acc = feedback.game2_acc;
    state.currentUser.game3_acc = feedback.game3_acc;
    state.currentUser.user_level = feedback.new_level;
    updateUserInterface();

    // 檢查晉級賀喜
    if (feedback.is_promoted) {
      playSuccessChime();
      openPromotionModal(feedback);
    } else {
      showToast(feedback.message, "info");
    }
    // 重新載入打卡天數與徽章
    fetchStreakCalendar();
    fetchUserBadges();
  } catch (err) {
    console.error("提交試煉成績失敗:", err);
  }
}

function openPromotionModal(feedback) {
  const modal = document.getElementById("promotionModal");
  if (!modal) return;
  const msgEl = document.getElementById("promotionMsgText");
  if (msgEl) msgEl.textContent = feedback.message;
  modal.classList.add("active-modal");
}

function checkPromotionPopup(user) {
  if (user.user_level === "外門弟子") {
    showToast("🎉 您已榮登【外門弟子】，全站功能全面解鎖！", "success");
  }
}

function initBeginnerGames() {
  initGame1();
  initGame2();
  initGame3();
}

// --------------------------------------------------------------------------
// 官方合法 YouTube 雙語互動影音字典
// --------------------------------------------------------------------------
async function fetchMediaList(category = "all") {
  try {
    const url = category && category !== "all" ? `/api/media?category=${encodeURIComponent(category)}` : "/api/media";
    const res = await fetch(url);
    if (!res.ok) throw new Error("取得影音列表失敗");
    state.mediaList = await res.json();
    renderMediaCards();
    if (state.mediaList.length > 0 && !state.currentMedia) {
      loadMediaItem(state.mediaList[0]);
    }
  } catch (err) {
    console.error("載入影音清單失敗:", err);
  }
}

function renderMediaCards() {
  const container = document.getElementById("videoCardsCarousel");
  if (!container) return;
  container.innerHTML = "";

  state.mediaList.forEach(item => {
    const card = document.createElement("div");
    card.className = `video-thumb-card ${state.currentMedia && state.currentMedia.id === item.id ? "active-media" : ""}`;
    card.innerHTML = `
      <div class="video-thumb-title">${item.title}</div>
      <div class="video-thumb-cat">🏷️ ${item.category} · 👍 ${item.likes_count}</div>
    `;
    card.addEventListener("click", () => loadMediaItem(item));
    container.appendChild(card);
  });
}

function loadMediaItem(item) {
  state.currentMedia = item;
  renderMediaCards();

  // 評價計數更新
  document.getElementById("mediaLikesCount").textContent = item.likes_count;
  document.getElementById("mediaDislikesCount").textContent = item.dislikes_count;

  // 渲染字幕清單
  renderSubtitlesList(item.subtitles);

  // 載入 YouTube Player
  mountYouTubePlayer(item.youtube_id);
}

function mountYouTubePlayer(youtubeId) {
  const container = document.getElementById("youtubePlayerPlaceholder");
  if (!container) return;
  container.innerHTML = `<iframe id="ytIframePlayer" src="https://www.youtube.com/embed/${youtubeId}?enablejsapi=1&origin=${encodeURIComponent(window.location.origin)}" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`;
}

// 渲染雙語分詞字幕
function renderSubtitlesList(subtitles) {
  const stream = document.getElementById("subtitlesStreamBox");
  if (!stream) return;
  stream.innerHTML = "";

  if (!subtitles || subtitles.length === 0) {
    stream.innerHTML = "<div style='color: var(--text-muted); text-align: center; padding: 2rem;'>此影片暫無雙語字幕</div>";
    return;
  }

  subtitles.forEach((line, index) => {
    const lineEl = document.createElement("div");
    lineEl.className = "subtitle-line";
    lineEl.dataset.start = line.start_time;
    lineEl.dataset.end = line.end_time;

    // 將日文句子拆分為可懸浮的分詞 Token
    let jaHtml = line.text_ja;
    if (line.words && line.words.length > 0) {
      line.words.forEach(w => {
        const tokenHtml = `<span class="vocab-token" data-word="${w.word}" data-reading="${w.reading}" data-romaji="${w.romaji}" data-meaning="${w.meaning}" data-exja="${w.example_ja || ''}" data-exzh="${w.example_zh || ''}">${w.word}</span>`;
        jaHtml = jaHtml.replace(w.word, tokenHtml);
      });
    }

    lineEl.innerHTML = `
      <div class="sub-ja" style="display: ${state.userSubJa ? 'block' : 'none'};">${jaHtml}</div>
      <div class="sub-zh" style="display: ${state.userSubZh ? 'block' : 'none'};">${line.text_zh}</div>
    `;

    // 為分詞綁定懸浮互動字典
    lineEl.querySelectorAll(".vocab-token").forEach(token => {
      token.addEventListener("mouseenter", (e) => handleWordTokenHover(e, token));
    });

    stream.appendChild(lineEl);
  });
}

// 游標移至日文分詞：暫停 YouTube 影片並彈出詞典懸浮卡
function handleWordTokenHover(e, token) {
  // 發送 postMessage 指令以暫停 YouTube Iframe
  const iframe = document.getElementById("ytIframePlayer");
  if (iframe && iframe.contentWindow) {
    iframe.contentWindow.postMessage(JSON.stringify({ event: 'command', func: 'pauseVideo', args: [] }), '*');
  }

  const tooltip = document.getElementById("dictTooltip");
  if (!tooltip) return;

  const word = token.dataset.word;
  const reading = token.dataset.reading;
  const romaji = token.dataset.romaji;
  const meaning = token.dataset.meaning;
  const exja = token.dataset.exja;

  document.getElementById("tooltipWord").textContent = word;
  document.getElementById("tooltipReading").textContent = `${reading} · ${romaji}`;
  document.getElementById("tooltipMeaning").textContent = meaning;
  document.getElementById("tooltipExample").textContent = exja ? `例句：${exja}` : "";

  // 朗讀按鈕綁定
  const audioBtn = document.getElementById("btnTooltipAudio");
  audioBtn.onclick = () => playJapaneseAudio(word);

  // 一鍵收藏按鈕綁定
  const saveBtn = document.getElementById("btnTooltipSaveWord");
  saveBtn.onclick = () => handleQuickSaveWord({
    word: word,
    reading: reading,
    romaji: romaji,
    meaning: meaning,
    example_ja: exja,
    example_zh: token.dataset.exzh || "",
    level: "N5"
  });

  // 定位懸浮卡至分詞正下方
  const rect = token.getBoundingClientRect();
  const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
  const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

  tooltip.style.left = `${rect.left + scrollLeft}px`;
  tooltip.style.top = `${rect.bottom + scrollTop + 6}px`;
  tooltip.style.display = "block";

  // 背景記錄分詞懸浮遙測，動態微調個人興趣推薦權重
  recordBehaviorTelemetry({
    hovered_word: word,
    dwell_category: state.currentMedia ? state.currentMedia.category : null
  });
}

// 點擊任意處關閉字典懸浮卡
document.addEventListener("click", (e) => {
  const tooltip = document.getElementById("dictTooltip");
  if (tooltip && !tooltip.contains(e.target) && !e.target.classList.contains("vocab-token")) {
    tooltip.style.display = "none";
  }
});

// 一鍵收藏影片單字至個人雲端生詞本
async function handleQuickSaveWord(wordData) {
  try {
    const res = await fetch("/api/words", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(wordData)
    });
    if (!res.ok) throw new Error("收藏失敗");
    const newWord = await res.json();
    playSuccessChime();
    showToast(`已成功將「${newWord.word}」加入個人生詞本！⭐`, "success");
    fetchWordsList();
    fetchStudyStats();
  } catch (err) {
    showToast("收藏單字失敗，請稍後再試", "error");
  }
}

// 影片偏好反饋 (👍 / 👎)
async function handleMediaFeedback(action) {
  if (!state.currentMedia) return;
  try {
    const res = await fetch(`/api/media/${encodeURIComponent(state.currentMedia.id)}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ media_id: state.currentMedia.id, action: action })
    });
    if (!res.ok) throw new Error("評價提交失敗");
    const result = await res.json();
    state.currentMedia.likes_count = result.likes_count;
    state.currentMedia.dislikes_count = result.dislikes_count;
    document.getElementById("mediaLikesCount").textContent = result.likes_count;
    document.getElementById("mediaDislikesCount").textContent = result.dislikes_count;
    showToast(action === "interested" ? "感謝回饋！系統將推薦更多此類影音 👍" : "已記錄反饋 👎", "info");
    renderMediaCards();
  } catch (err) {
    showToast("評價提交失敗", "error");
  }
}

// --------------------------------------------------------------------------
// 優化 3D 生詞卡呈現與複習系統 (Feature 2)
// --------------------------------------------------------------------------
function applyCardFilter(filter) {
  state.cardFilter = filter;
  document.querySelectorAll(".flashcard-toolbar .btn-filter").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.filter === filter);
  });

  if (filter === "all") {
    state.filteredCards = [...state.allWords];
  } else {
    state.filteredCards = state.allWords.filter(w => w.srs_status === filter);
  }
  state.cardIndex = 0;
  state.isFlipped = false;
  renderCurrentCard();
}

function renderCurrentCard() {
  const cardElement = document.getElementById("flashcardElement");
  const counterBadge = document.getElementById("cardCounterBadge");
  if (cardElement) {
    cardElement.classList.remove("is-flipped");
    state.isFlipped = false;
  }

  if (state.filteredCards.length === 0) {
    if (counterBadge) counterBadge.textContent = "0 / 0 張";
    document.getElementById("cardFrontWord").textContent = "無符合單字";
    document.getElementById("cardFrontLevel").textContent = "-";
    document.getElementById("cardFrontStatus").textContent = "-";
    return;
  }

  const currentWord = state.filteredCards[state.cardIndex];
  if (counterBadge) {
    counterBadge.textContent = `第 ${state.cardIndex + 1} / ${state.filteredCards.length} 張`;
  }

  // 正面
  document.getElementById("cardFrontLevel").textContent = currentWord.level || "N5";
  document.getElementById("cardFrontWord").textContent = currentWord.word;
  const srsBadge = document.getElementById("cardFrontStatus");
  srsBadge.textContent = getSrsLabel(currentWord.srs_status);
  srsBadge.style.color = getSrsColor(currentWord.srs_status);

  // 背面
  document.getElementById("cardBackLevel").textContent = currentWord.level || "N5";
  document.getElementById("cardBackReading").textContent = currentWord.reading;
  document.getElementById("cardBackRomaji").textContent = currentWord.romaji;
  document.getElementById("cardBackMeaning").textContent = currentWord.meaning;
  document.getElementById("cardBackExJa").textContent = currentWord.example_ja || "無例句";
  document.getElementById("cardBackExZh").textContent = currentWord.example_zh || "";
}

function getSrsLabel(status) {
  switch (status) {
    case "mastered": return "🟢 已掌握";
    case "hard": return "🔴 困難";
    default: return "🟡 需練習";
  }
}

function getSrsColor(status) {
  switch (status) {
    case "mastered": return "var(--srs-mastered)";
    case "hard": return "var(--srs-hard)";
    default: return "var(--srs-practice)";
  }
}

function flipCard() {
  const cardElement = document.getElementById("flashcardElement");
  if (!cardElement) return;
  state.isFlipped = !state.isFlipped;
  cardElement.classList.toggle("is-flipped", state.isFlipped);
}

async function rateCardSRS(status) {
  if (state.filteredCards.length === 0) return;
  const currentWord = state.filteredCards[state.cardIndex];
  try {
    const res = await fetch(`/api/words/${currentWord.id}/srs`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ srs_status: status })
    });
    if (!res.ok) throw new Error("SRS 更新失敗");
    const updated = await res.json();
    currentWord.srs_status = updated.srs_status;

    // 自動翻下一張
    if (state.cardIndex < state.filteredCards.length - 1) {
      state.cardIndex++;
    } else {
      state.cardIndex = 0;
    }
    renderCurrentCard();
    fetchStudyStats();
    fetchStreakCalendar();
    checkTierProgression();
    showToast(`掌握度已標記為：${getSrsLabel(status)}`, "info");
  } catch (err) {
    showToast("更新掌握度失敗", "error");
  }
}

// --------------------------------------------------------------------------
// 互動單字小測驗遊戲引擎 (Feature 1)
// --------------------------------------------------------------------------
async function startQuizSession() {
  const mode = document.getElementById("quizModeSelect").value;
  const pool = document.getElementById("quizPoolSelect").value;
  const count = parseInt(document.getElementById("quizCountSelect").value, 10);

  state.quizMode = mode;
  state.quizPool = pool;
  state.quizCount = count;
  state.quizIndex = 0;
  state.quizScore = 0;
  state.quizCombo = 0;
  state.quizMaxCombo = 0;
  state.quizCorrectCount = 0;
  state.quizWrongWords = [];

  try {
    const res = await fetch("/api/quiz/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: mode, pool: pool, count: count })
    });
    if (!res.ok) throw new Error("無法生成測驗題目");
    state.quizQuestions = await res.json();

    document.getElementById("quizSetupCard").style.display = "none";
    document.getElementById("quizSummaryCard").style.display = "none";
    document.getElementById("quizGameStage").style.display = "flex";

    renderCurrentQuizQuestion();
  } catch (err) {
    showToast("生成測驗題庫失敗，請確認單字庫有充足詞彙", "error");
  }
}

function renderCurrentQuizQuestion() {
  state.isSubmitting = false;
  const q = state.quizQuestions[state.quizIndex];
  if (!q) {
    finishQuizSession();
    return;
  }

  // 隱藏回饋橫條
  document.getElementById("quizFeedbackBar").style.display = "none";

  // 更新進度條
  const total = state.quizQuestions.length;
  document.getElementById("quizCurrentNum").textContent = state.quizIndex + 1;
  document.getElementById("quizTotalNum").textContent = total;
  document.getElementById("quizProgressBar").style.width = `${((state.quizIndex + 1) / total) * 100}%`;
  document.getElementById("quizScoreVal").textContent = state.quizScore;
  document.getElementById("quizComboBadge").textContent = `🔥 COMBO x${state.quizCombo}`;

  document.getElementById("quizModeLabel").textContent = q.mode === "spelling" ? "拼寫挑戰" : "四選一";
  document.getElementById("quizQuestionPrompt").textContent = q.prompt;

  // 語音朗讀
  const audioBtn = document.getElementById("btnQuizQuestionAudio");
  audioBtn.onclick = () => playJapaneseAudio(q.target_word);

  if (q.mode === "multiple_choice") {
    document.getElementById("quizOptionsContainer").style.display = "grid";
    document.getElementById("quizSpellingContainer").style.display = "none";
    renderQuizOptions(q.options, q.word_id);
  } else {
    document.getElementById("quizOptionsContainer").style.display = "none";
    document.getElementById("quizSpellingContainer").style.display = "block";
    const input = document.getElementById("quizSpellingInput");
    input.value = "";
    input.focus();
  }
}

function renderQuizOptions(options, wordId) {
  const container = document.getElementById("quizOptionsContainer");
  container.innerHTML = "";
  (options || []).forEach(opt => {
    const btn = document.createElement("button");
    btn.className = "quiz-option-btn";
    btn.innerHTML = `<span>${opt.text}</span> ${opt.sub_text ? `<small class="quiz-option-sub">${opt.sub_text}</small>` : ""}`;
    btn.addEventListener("click", () => submitQuizAnswer(wordId, opt.text));
    container.appendChild(btn);
  });
}

async function submitQuizAnswer(wordId, userAnswer) {
  if (state.isSubmitting) return;
  state.isSubmitting = true;

  try {
    const res = await fetch("/api/quiz/submit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        word_id: wordId,
        user_answer: userAnswer,
        current_combo: state.quizCombo,
        mode: state.quizMode
      })
    });
    if (!res.ok) throw new Error("作答判定失敗");
    const feedback = await res.json();

    // 更新連擊與分數
    state.quizCombo = feedback.updated_combo;
    if (state.quizCombo > state.quizMaxCombo) state.quizMaxCombo = state.quizCombo;
    state.quizScore += feedback.earned_score;

    if (feedback.is_correct) {
      playSuccessChime();
      state.quizCorrectCount++;
    } else {
      playWrongBuzzer();
      state.quizWrongWords.push({
        word: feedback.correct_word,
        reading: feedback.correct_reading,
        meaning: feedback.correct_meaning
      });
    }

    // 展現即時回饋橫條
    showQuizFeedbackBar(feedback);
  } catch (err) {
    state.isSubmitting = false;
    showToast("作答送出失敗", "error");
  }
}

function showQuizFeedbackBar(feedback) {
  const bar = document.getElementById("quizFeedbackBar");
  bar.style.display = "flex";
  document.getElementById("feedbackIcon").textContent = feedback.is_correct ? "🎉" : "💡";
  document.getElementById("feedbackTitle").textContent = feedback.is_correct ? "答對了！" : "再接再厲！";
  document.getElementById("feedbackTitle").style.color = feedback.is_correct ? "var(--srs-mastered)" : "var(--srs-hard)";
  document.getElementById("feedbackSub").textContent = `正確：${feedback.correct_word} (${feedback.correct_reading}) - ${feedback.correct_meaning}`;
}

function finishQuizSession() {
  document.getElementById("quizGameStage").style.display = "none";
  document.getElementById("quizSummaryCard").style.display = "block";

  const total = state.quizQuestions.length;
  const accuracy = total > 0 ? Math.round((state.quizCorrectCount / total) * 100) : 0;

  document.getElementById("summaryFinalScore").textContent = state.quizScore;
  document.getElementById("summaryAccuracy").textContent = `${accuracy}%`;
  document.getElementById("summaryMaxCombo").textContent = state.quizMaxCombo;
  document.getElementById("summaryCorrectVsTotal").textContent = `${state.quizCorrectCount} / ${total}`;

  // 錯題清單
  const wrongSection = document.getElementById("quizWrongSection");
  const wrongList = document.getElementById("quizWrongWordsList");
  if (state.quizWrongWords.length > 0) {
    wrongSection.style.display = "block";
    wrongList.innerHTML = "";
    state.quizWrongWords.forEach(w => {
      const li = document.createElement("li");
      li.style.marginBottom = "0.4rem";
      li.innerHTML = `<b>${w.word}</b> (${w.reading}) : ${w.meaning}`;
      wrongList.appendChild(li);
    });
  } else {
    wrongSection.style.display = "none";
  }

  fetchStudyStats();
  fetchStreakCalendar();
  checkTierProgression();
  recordBehaviorTelemetry({ completed_quiz_category: state.quizMode });
}

// --------------------------------------------------------------------------
// 學習打卡日曆與 GitHub 風格熱力圖渲染 (GitHub Contribution Heatmap)
// --------------------------------------------------------------------------
function renderGitHubHeatmap(data) {
  const grid = document.getElementById("githubHeatmapGrid");
  if (!grid) return;
  grid.innerHTML = "";

  // 產生 52 週 x 7 天方格（共 364 天）
  const totalDays = 52 * 7;
  const today = new Date();

  // 建立日期對照字典以快速查找打卡活動
  const activityMap = {};
  if (data && data.month_days) {
    data.month_days.forEach(d => {
      activityMap[d.date_str] = d;
    });
  }

  for (let i = totalDays - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().split("T")[0];

    const box = document.createElement("div");
    box.className = "heat-box";

    const act = activityMap[dateStr];
    if (act && act.is_active) {
      const cnt = (act.words_count || 0) + (act.quizzes_count || 0);
      if (cnt > 12) box.classList.add("level-4");
      else if (cnt > 8) box.classList.add("level-3");
      else if (cnt > 4) box.classList.add("level-2");
      else box.classList.add("level-1");
      box.title = `${dateStr}：已完成學習 (${act.words_count} 個生詞，${act.quizzes_count} 回測驗)`;
    } else {
      box.classList.add("level-0");
      box.title = `${dateStr}：無活動紀錄`;
    }

    grid.appendChild(box);
  }
}

function renderMonthCalendar(data) {
  const title = document.getElementById("calendarMonthTitle");
  if (title) title.textContent = `${state.calYear} 年 ${state.calMonth} 月`;

  const grid = document.getElementById("calendarDaysGrid");
  if (!grid) return;
  grid.innerHTML = "";

  // 計算當月首日星期幾
  const firstDayIndex = new Date(state.calYear, state.calMonth - 1, 1).getDay();
  for (let empty = 0; empty < firstDayIndex; empty++) {
    const emptyCell = document.createElement("div");
    emptyCell.className = "cal-day-cell";
    emptyCell.style.opacity = "0.2";
    grid.appendChild(emptyCell);
  }

  (data.month_days || []).forEach(dayInfo => {
    const cell = document.createElement("div");
    cell.className = `cal-day-cell ${dayInfo.is_active ? 'is-active' : ''} ${dayInfo.is_today ? 'is-today' : ''}`;
    cell.innerHTML = `<span>${dayInfo.day}</span>`;
    if (dayInfo.is_active) {
      cell.title = `${dayInfo.date_str}：已打卡！`;
    }
    grid.appendChild(cell);
  });
}

// --------------------------------------------------------------------------
// 雲端生詞本管理表格渲染
// --------------------------------------------------------------------------
function renderVocabTable(words) {
  const tbody = document.getElementById("vocabTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (words.length === 0) {
    tbody.innerHTML = "<tr><td colspan='6' style='text-align: center; color: var(--text-muted); padding: 2rem;'>單字庫中尚無資料</td></tr>";
    return;
  }

  words.forEach(w => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><b>${w.word}</b> <small style="color: var(--primary-color);">(${w.level})</small></td>
      <td>${w.reading}</td>
      <td>${w.romaji}</td>
      <td>${w.meaning}</td>
      <td><span class="level-tag" style="background:${getSrsColor(w.srs_status)}; color:#fff;">${getSrsLabel(w.srs_status)}</span></td>
      <td><button class="btn-audio-table" title="朗讀發音">🔊</button></td>
    `;
    tr.querySelector(".btn-audio-table").addEventListener("click", () => playJapaneseAudio(w.word));
    tbody.appendChild(tr);
  });
}

// --------------------------------------------------------------------------
// 個人偏好設定與意見反饋 (Direct Feedback -> ytpre.new1@gmail.com)
// --------------------------------------------------------------------------
function updateHobbyCountTip() {
  const checked = document.querySelectorAll("#hobbyTagsSelector input[type='checkbox']:checked");
  const tip = document.getElementById("hobbyCountTip");
  if (tip) tip.textContent = `已選 ${checked.length} / 10 個標籤`;
}

async function handleSavePreferences(e) {
  e.preventDefault();
  if (!state.currentUser) return;

  const checkedBoxes = Array.from(document.querySelectorAll("#hobbyTagsSelector input[type='checkbox']:checked"));
  if (checkedBoxes.length > 10) {
    showToast("興趣標籤最多只能選擇 10 個", "error");
    return;
  }
  const hobbies = checkedBoxes.map(cb => cb.value);
  const subJa = document.getElementById("prefDefaultSubJa").checked;
  const subZh = document.getElementById("prefDefaultSubZh").checked;

  try {
    const res = await fetch(`/api/user/preferences?uid=${encodeURIComponent(state.currentUser.uid)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        hobbies: hobbies,
        default_sub_ja: subJa,
        default_sub_zh: subZh
      })
    });
    if (!res.ok) throw new Error("儲存偏好失敗");
    const updated = await res.json();
    state.currentUser = updated;
    updateUserInterface();
    document.getElementById("preferencesModal").classList.remove("active-modal");
    showToast("個人偏好設定已更新！💾", "success");
    // 依據新偏好重新載入影音推薦清單
    fetchMediaList();
  } catch (err) {
    showToast("儲存偏好失敗", "error");
  }
}

async function handleFeedbackSubmit(e) {
  e.preventDefault();
  const userName = document.getElementById("fbUserName").value.trim();
  const userEmail = document.getElementById("fbUserEmail").value.trim();
  const category = document.getElementById("fbCategory").value;
  const message = document.getElementById("fbMessage").value.trim();

  try {
    const res = await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_name: userName,
        user_email: userEmail,
        category: category,
        message: message,
        target_email: "ytpre.new1@gmail.com"
      })
    });
    if (!res.ok) throw new Error("意見回饋提交失敗");
    const data = await res.json();
    document.getElementById("feedbackModal").classList.remove("active-modal");
    document.getElementById("formFeedbackSubmit").reset();
    showToast("🎉 意見回饋已成功送出至官方信箱！由衷感謝您的支持！", "success");
  } catch (err) {
    showToast("送出反饋失敗，請稍後再試", "error");
  }
}

// --------------------------------------------------------------------------
// 行為遙測追蹤與自動化偏好動態微調 (Behavioral Telemetry Tracking)
// --------------------------------------------------------------------------
async function recordBehaviorTelemetry({ dwell_category = null, dwell_seconds = 0, hovered_word = null, completed_quiz_category = null }) {
  if (!state.currentUser) return;
  try {
    await fetch(`/api/user/behavior?uid=${encodeURIComponent(state.currentUser.uid)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        uid: state.currentUser.uid,
        dwell_category: dwell_category,
        dwell_seconds: dwell_seconds,
        hovered_word: hovered_word,
        completed_quiz_category: completed_quiz_category
      })
    });
  } catch (err) {
    // 背景遙測默默記錄，不干擾使用者操作
  }
}

// --------------------------------------------------------------------------
// 自動審核境界晉升與成就徽章 (Automatic Tier & Badge Progression)
// --------------------------------------------------------------------------
async function checkTierProgression() {
  if (!state.currentUser) return;
  try {
    const res = await fetch(`/api/user/evaluate-tier?uid=${encodeURIComponent(state.currentUser.uid)}`, {
      method: "POST"
    });
    if (res.ok) {
      const data = await res.json();
      if (data.is_promoted) {
        state.currentUser.user_level = data.new_tier;
        updateUserInterface();
        showToast(`🎉 修為大突破！恭喜境界晉升為【${data.new_tier}】！`, "success");
        playSuccessChime();
      }
      await fetchUserBadges();
    }
  } catch (err) {
    console.warn("評估境界晉升失敗:", err);
  }
}

// --------------------------------------------------------------------------
// 成就徽章收藏館 (Feature 2 - Achievement Badge Gallery)
// --------------------------------------------------------------------------
async function fetchUserBadges() {
  if (!state.currentUser) return;
  try {
    const res = await fetch(`/api/badges?uid=${encodeURIComponent(state.currentUser.uid)}`);
    if (!res.ok) throw new Error("讀取徽章資料失敗");
    state.userBadges = await res.json();
    const unlockedCount = state.userBadges.filter(b => b.unlocked).length;
    const totalCount = state.userBadges.length || 8;

    const navBadgeStat = document.getElementById("statBadgeCount");
    if (navBadgeStat) navBadgeStat.textContent = `${unlockedCount} / ${totalCount}`;

    const progEl = document.getElementById("badgeProgressCount");
    if (progEl) progEl.textContent = `${unlockedCount} / ${totalCount}`;

    renderBadgesGallery();
  } catch (err) {
    console.warn("載入徽章清單失敗:", err);
  }
}

function renderBadgesGallery() {
  const container = document.getElementById("badgesGalleryGrid");
  if (!container) return;
  container.innerHTML = "";

  const filtered = state.userBadges.filter(b => {
    if (state.badgeFilter === "all") return true;
    return b.category === state.badgeFilter;
  });

  if (filtered.length === 0) {
    container.innerHTML = "<div style='grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 2.5rem; font-size: 1.05rem;'>目前尚無相符之徽章成就</div>";
    return;
  }

  filtered.forEach(badge => {
    const card = document.createElement("div");
    card.className = `badge-card ${badge.unlocked ? "unlocked" : "locked"}`;
    card.innerHTML = `
      <div class="badge-card-icon">${badge.icon}</div>
      <div class="badge-card-name">${badge.name}</div>
      <div class="badge-card-desc">${badge.description}</div>
      <div class="badge-card-criteria">🎯 達成條件：${badge.criteria}</div>
      <div class="badge-status-tag ${badge.unlocked ? "status-unlocked" : "status-locked"}">
        ${badge.unlocked ? `✅ 已解鎖 (${badge.unlocked_at ? badge.unlocked_at.slice(0, 10) : '已達成'})` : '🔒 未解鎖'}
      </div>
    `;
    container.appendChild(card);
  });
}

// --------------------------------------------------------------------------
// 沈浸式動態能力定級與分級測試 (Feature 3 - Adaptive Level Placement)
// --------------------------------------------------------------------------
function updateOnboardingHobbyCountTip() {
  const checked = document.querySelectorAll("#onboardingHobbySelector input[type='checkbox']:checked");
  const tip = document.getElementById("onboardingHobbyCountTip");
  if (tip) tip.textContent = `已選 ${checked.length} / 10 個標籤`;
}

function openPlacementModal() {
  const modal = document.getElementById("placementModal");
  if (!modal) return;

  state.onboardingTargetTier = "新手小白";
  state.placementQuestions = [];
  state.placementAnswers = {};

  // 重置步驟導航
  document.getElementById("stepIndicator1").className = "p-step active";
  document.getElementById("stepIndicator2").className = "p-step";
  document.getElementById("stepIndicator3").className = "p-step";

  document.getElementById("placementStep1").style.display = "block";
  document.getElementById("placementStep2").style.display = "none";
  document.getElementById("placementStep3").style.display = "none";

  // 預設勾選新手小白
  const firstRadio = document.querySelector('input[name="targetTierSelect"][value="新手小白"]');
  if (firstRadio) firstRadio.checked = true;

  // 勾選現有興趣標籤
  if (state.currentUser && state.currentUser.hobbies) {
    document.querySelectorAll("#onboardingHobbySelector input[type='checkbox']").forEach(cb => {
      cb.checked = state.currentUser.hobbies.includes(cb.value);
    });
  }
  updateOnboardingHobbyCountTip();

  modal.classList.add("active-modal");
}

function closePlacementModal() {
  const modal = document.getElementById("placementModal");
  if (modal) modal.classList.remove("active-modal");
}

async function startPlacementQuiz() {
  const selectedTierRadio = document.querySelector('input[name="targetTierSelect"]:checked');
  const targetTier = selectedTierRadio ? selectedTierRadio.value : "新手小白";
  state.onboardingTargetTier = targetTier;

  const checkedHobbies = Array.from(document.querySelectorAll("#onboardingHobbySelector input[type='checkbox']:checked")).map(cb => cb.value);

  // 若選擇「新手小白」，免試直接註冊道基
  if (targetTier === "新手小白") {
    await submitPlacementTest([], checkedHobbies);
    return;
  }

  // 獲取目標境界試題
  try {
    const res = await fetch(`/api/onboarding/placement-questions?target_tier=${encodeURIComponent(targetTier)}`);
    if (!res.ok) {
      let errMsg = "讀取試題失敗";
      try {
        const errJson = await res.json();
        if (errJson && errJson.detail) errMsg = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      } catch (e) {}
      throw new Error(errMsg);
    }
    state.placementQuestions = await res.json();
    state.placementAnswers = {};

    renderPlacementQuestions();

    // 切換至步驟 2
    document.getElementById("stepIndicator1").className = "p-step";
    document.getElementById("stepIndicator2").className = "p-step active";
    document.getElementById("stepIndicator3").className = "p-step";

    document.getElementById("placementStep1").style.display = "none";
    document.getElementById("placementStep2").style.display = "block";
    document.getElementById("placementStep3").style.display = "none";

    const badgeLabel = document.getElementById("placementTargetBadge");
    if (badgeLabel) {
      badgeLabel.textContent = `${targetTier}挑戰門檻 (4題)`;
      badgeLabel.className = `badge-level ${getLevelClass(targetTier)}`;
    }
  } catch (err) {
    console.error("無法載入定級測試試題：", err);
    showToast(`無法載入定級測試試題：${err.message || "請稍後再試"}`, "error");
  }
}

function renderPlacementQuestions() {
  const container = document.getElementById("placementQuestionsContainer");
  if (!container) return;
  container.innerHTML = "";

  state.placementQuestions.forEach((q, idx) => {
    const card = document.createElement("div");
    card.className = "placement-q-card";
    card.innerHTML = `
      <div class="q-header">
        <span class="q-tag">第 ${idx + 1} 題 · ${q.target_tier}</span>
        <span style="font-size: 0.88rem; color: var(--text-muted);">${q.jlpt_level || ''}</span>
      </div>
      <div class="q-prompt">${q.prompt}</div>
      <div class="q-options" id="pq_options_${q.id}">
        ${q.options.map(opt => `
          <label class="q-option-label">
            <input type="radio" name="pq_${q.id}" value="${opt}">
            <span>${opt}</span>
          </label>
        `).join("")}
      </div>
    `;
    container.appendChild(card);
  });
}

async function submitPlacementAnswers() {
  if (!state.placementQuestions || state.placementQuestions.length === 0) return;

  const answers = [];
  for (let i = 0; i < state.placementQuestions.length; i++) {
    const q = state.placementQuestions[i];
    const checked = document.querySelector(`input[name="pq_${q.id}"]:checked`);
    if (!checked) {
      showToast(`第 ${i + 1} 題尚未作答，請完成所有題目後再送出！`, "info");
      return;
    }
    answers.push({
      question_id: q.id,
      selected_option: checked.value
    });
  }

  const checkedHobbies = Array.from(document.querySelectorAll("#onboardingHobbySelector input[type='checkbox']:checked")).map(cb => cb.value);
  await submitPlacementTest(answers, checkedHobbies);
}

async function submitPlacementTest(answers, hobbies) {
  if (!state.currentUser) return;
  try {
    const res = await fetch(`/api/onboarding/placement-submit?uid=${encodeURIComponent(state.currentUser.uid)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        uid: state.currentUser.uid,
        target_tier: state.onboardingTargetTier,
        hobbies: hobbies,
        answers: answers
      })
    });
    if (!res.ok) {
      let errMsg = "定級提交失敗";
      try {
        const errJson = await res.json();
        if (errJson && errJson.detail) {
          errMsg = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
        }
      } catch (e) {}
      throw new Error(errMsg);
    }
    const result = await res.json();

    // 更新使用者狀態
    state.currentUser.user_level = result.assigned_tier;
    state.currentUser.onboarding_completed = true;
    state.currentUser.hobbies = hobbies;
    localStorage.setItem("jp_user_data", JSON.stringify(state.currentUser));
    updateUserInterface();

    // 展現步驟 3
    document.getElementById("stepIndicator1").className = "p-step";
    document.getElementById("stepIndicator2").className = "p-step";
    document.getElementById("stepIndicator3").className = "p-step active";

    document.getElementById("placementStep1").style.display = "none";
    document.getElementById("placementStep2").style.display = "none";
    document.getElementById("placementStep3").style.display = "block";

    const assignedTag = document.getElementById("placementAssignedTier");
    if (assignedTag) {
      assignedTag.textContent = result.assigned_tier;
      assignedTag.className = `promoted-tier-tag ${getLevelClass(result.assigned_tier)}`;
    }

    const titleEl = document.getElementById("placementResultTitle");
    const iconEl = document.getElementById("placementResultIcon");
    const msgEl = document.getElementById("placementResultMsg");

    if (result.passed) {
      if (iconEl) iconEl.textContent = "🎉";
      if (titleEl) titleEl.textContent = "定級成功！道基確立！";
      playSuccessChime();
    } else if (result.fallback_triggered) {
      if (iconEl) iconEl.textContent = "🛡️";
      if (titleEl) titleEl.textContent = "智慧降階保護機制啟動！";
      playSuccessChime();
    } else {
      if (iconEl) iconEl.textContent = "🌱";
      if (titleEl) titleEl.textContent = "基礎奠定完成！";
    }

    if (msgEl) msgEl.textContent = result.message;

    const badgeBox = document.getElementById("placementBadgeAwardedBox");
    const badgePill = document.getElementById("placementBadgePill");
    if (badgeBox && badgePill) {
      const awarded = (result.badges_awarded && result.badges_awarded.length > 0) ? result.badges_awarded : (result.unlocked_badge ? [result.unlocked_badge] : []);
      if (awarded.length > 0) {
        badgeBox.style.display = "block";
        badgePill.textContent = `🏆 解鎖徽章：${awarded.join("、")}`;
      } else {
        badgeBox.style.display = "none";
      }
    }

    await fetchUserBadges();
    await fetchStudyStats();
  } catch (err) {
    console.error("定級結算失敗：", err);
    showToast(`定級結算失敗：${err.message || "請稍後再試"}`, "error");
  }
}

// --------------------------------------------------------------------------
// DOM 載入完畢：全域事件監聽註冊與頁面就緒
// --------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  // 檢查既有登入紀錄
  const savedUid = localStorage.getItem("jp_user_uid");
  if (savedUid) {
    fetch(`/api/user/profile?uid=${encodeURIComponent(savedUid)}`)
      .then(res => res.json())
      .then(async user => {
        state.currentUser = user;
        document.getElementById("loginGateOverlay").style.display = "none";
        updateUserInterface();
        await loadInitialData();
        if (!user.onboarding_completed) {
          openPlacementModal();
        }
      })
      .catch(() => {
        document.getElementById("loginGateOverlay").style.display = "flex";
      });
  } else {
    document.getElementById("loginGateOverlay").style.display = "flex";
  }

  // 登入按鈕事件
  document.getElementById("btnGoogleSignIn").addEventListener("click", () => {
    // 官方 Google 登入模擬入口
    handleUserLogin({
      uid: "google_user_" + Math.random().toString(36).substring(2, 9),
      email: "user@gmail.com",
      display_name: "Google 學習者",
      photo_url: "https://api.dicebear.com/7.x/bottts/svg?seed=ninja"
    });
  });

  document.getElementById("btnDemoLogin").addEventListener("click", () => {
    // 快速體驗帳號
    handleUserLogin({
      uid: "demo_guest_101",
      email: "demo@antigravity.jp",
      display_name: "日語修行者",
      photo_url: "https://api.dicebear.com/7.x/bottts/svg?seed=samurai"
    });
  });

  document.getElementById("btnLogout").addEventListener("click", handleLogout);

  // 主導航切換
  document.querySelectorAll(".nav-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      const targetId = tab.dataset.target;
      document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
      tab.classList.add("active");

      document.querySelectorAll(".view-section").forEach(view => {
        view.classList.remove("active-view");
      });
      const targetView = document.getElementById(targetId);
      if (targetView) targetView.classList.add("active-view");

      state.activeTab = tab.dataset.tab;
    });
  });

  // 新手試煉堂子分頁切換
  document.querySelectorAll(".novice-tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const sub = btn.dataset.noviceSub;
      document.querySelectorAll(".novice-tab-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");

      document.querySelectorAll(".novice-sub-panel").forEach(p => p.classList.remove("active-sub"));
      if (sub === "kana") document.getElementById("noviceSubKana").classList.add("active-sub");
      else if (sub === "game1") document.getElementById("noviceSubGame1").classList.add("active-sub");
      else if (sub === "game2") document.getElementById("noviceSubGame2").classList.add("active-sub");
      else if (sub === "game3") document.getElementById("noviceSubGame3").classList.add("active-sub");
    });
  });

  // 標記完成五十音
  document.getElementById("btnMarkKanaComplete").addEventListener("click", handleMarkKanaCompleted);

  // 試煉遊戲重置按鈕
  document.getElementById("btnRestartGame1").addEventListener("click", initGame1);
  document.getElementById("btnRestartGame2").addEventListener("click", initGame2);
  document.getElementById("btnRestartGame3").addEventListener("click", initGame3);

  // 試煉二重播語音
  document.getElementById("btnPlayGame2Audio").addEventListener("click", () => {
    const currentQ = state.g2Questions[state.g2Index];
    if (currentQ) playJapaneseAudio(currentQ.kana);
  });

  // 試煉三打字提交
  document.getElementById("formGame3Submit").addEventListener("submit", handleGame3Submit);

  // 影音字典分類切換
  document.querySelectorAll(".category-filter-group .cat-pill").forEach(pill => {
    pill.addEventListener("click", () => {
      document.querySelectorAll(".category-filter-group .cat-pill").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      fetchMediaList(pill.dataset.cat);
    });
  });

  // 影音推薦評價按鈕
  document.getElementById("btnLikeMedia").addEventListener("click", () => handleMediaFeedback("interested"));
  document.getElementById("btnDislikeMedia").addEventListener("click", () => handleMediaFeedback("not_interested"));

  // 影片雙語字幕手動開關
  document.getElementById("toggleSubJa").addEventListener("change", (e) => {
    state.userSubJa = e.target.checked;
    document.querySelectorAll(".subtitle-line .sub-ja").forEach(el => {
      el.style.display = state.userSubJa ? "block" : "none";
    });
  });

  document.getElementById("toggleSubZh").addEventListener("change", (e) => {
    state.userSubZh = e.target.checked;
    document.querySelectorAll(".subtitle-line .sub-zh").forEach(el => {
      el.style.display = state.userSubZh ? "block" : "none";
    });
  });

  // 前往試煉堂導引按鈕
  document.getElementById("btnGoToNoviceTrial").addEventListener("click", () => {
    document.querySelector(".nav-tab[data-tab='novice']").click();
  });

  // 3D 生詞卡翻轉與導航
  document.getElementById("flashcardScene").addEventListener("click", flipCard);
  document.getElementById("btnPrevCard").addEventListener("click", () => {
    if (state.cardIndex > 0) {
      state.cardIndex--;
      renderCurrentCard();
    }
  });
  document.getElementById("btnNextCard").addEventListener("click", () => {
    if (state.cardIndex < state.filteredCards.length - 1) {
      state.cardIndex++;
      renderCurrentCard();
    }
  });

  // 生詞卡語音按鈕 (阻止卡片翻轉冒泡)
  document.getElementById("btnAudioFront").addEventListener("click", (e) => {
    e.stopPropagation();
    const current = state.filteredCards[state.cardIndex];
    if (current) playJapaneseAudio(current.word);
  });
  document.getElementById("btnAudioBack").addEventListener("click", (e) => {
    e.stopPropagation();
    const current = state.filteredCards[state.cardIndex];
    if (current) playJapaneseAudio(current.word);
  });

  // SRS 評級按鈕
  document.querySelectorAll(".btn-srs-rate").forEach(btn => {
    btn.addEventListener("click", () => rateCardSRS(btn.dataset.srs));
  });

  // 單字測驗啟動
  document.getElementById("btnStartQuiz").addEventListener("click", startQuizSession);
  document.getElementById("btnRestartQuiz").addEventListener("click", startQuizSession);
  document.getElementById("btnReturnSetup").addEventListener("click", () => {
    document.getElementById("quizSummaryCard").style.display = "none";
    document.getElementById("quizSetupCard").style.display = "block";
  });

  // 拼寫測驗提交
  document.getElementById("quizSpellingForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const q = state.quizQuestions[state.quizIndex];
    if (!q) return;
    const input = document.getElementById("quizSpellingInput");
    submitQuizAnswer(q.word_id, input.value.trim());
  });

  // 下一題按鈕
  document.getElementById("btnNextQuestion").addEventListener("click", () => {
    state.quizIndex++;
    renderCurrentQuizQuestion();
  });

  // 打卡月份切換
  document.getElementById("btnPrevMonth").addEventListener("click", () => {
    if (state.calMonth === 1) {
      state.calMonth = 12;
      state.calYear--;
    } else {
      state.calMonth--;
    }
    fetchStreakCalendar(state.calYear, state.calMonth);
  });

  document.getElementById("btnNextMonth").addEventListener("click", () => {
    if (state.calMonth === 12) {
      state.calMonth = 1;
      state.calYear++;
    } else {
      state.calMonth++;
    }
    fetchStreakCalendar(state.calYear, state.calMonth);
  });

  // 偏好設定 Modal
  document.getElementById("btnOpenPreferences").addEventListener("click", () => {
    document.getElementById("preferencesModal").classList.add("active-modal");
  });
  document.getElementById("btnClosePreferences").addEventListener("click", () => {
    document.getElementById("preferencesModal").classList.remove("active-modal");
  });
  document.getElementById("formPreferences").addEventListener("submit", handleSavePreferences);

  // 偏好設定中興趣標籤勾選上限監控 (最多 10 項)
  document.querySelectorAll("#hobbyTagsSelector input[type='checkbox']").forEach(cb => {
    cb.addEventListener("change", () => {
      const checked = document.querySelectorAll("#hobbyTagsSelector input[type='checkbox']:checked");
      if (checked.length > 10) {
        cb.checked = false;
        showToast("最多僅能選擇 10 項興趣標籤", "info");
      }
      updateHobbyCountTip();
    });
  });

  // 意見反饋 Modal
  document.getElementById("btnOpenFeedback").addEventListener("click", () => {
    document.getElementById("feedbackModal").classList.add("active-modal");
  });
  document.getElementById("btnCloseFeedback").addEventListener("click", () => {
    document.getElementById("feedbackModal").classList.remove("active-modal");
  });
  document.getElementById("formFeedbackSubmit").addEventListener("submit", handleFeedbackSubmit);

  // 晉級慶祝 Modal 點擊解鎖影音字典
  document.getElementById("btnExploreUnlockedFeatures").addEventListener("click", () => {
    document.getElementById("promotionModal").classList.remove("active-modal");
    document.querySelector(".nav-tab[data-tab='video']").click();
  });

  // 搜尋生詞
  document.getElementById("vocabSearchInput").addEventListener("input", (e) => {
    const q = e.target.value.trim().toLowerCase();
    const filtered = state.allWords.filter(w =>
      w.word.toLowerCase().includes(q) ||
      w.reading.toLowerCase().includes(q) ||
      w.romaji.toLowerCase().includes(q) ||
      w.meaning.toLowerCase().includes(q)
    );
    renderVocabTable(filtered);
  });

  // 新增自訂單字 Modal
  document.getElementById("btnOpenAddWord").addEventListener("click", () => {
    document.getElementById("addWordModal").classList.add("active-modal");
  });
  document.getElementById("btnCloseAddWord").addEventListener("click", () => {
    document.getElementById("addWordModal").classList.remove("active-modal");
  });

  document.getElementById("addWordForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const kanji = document.getElementById("newWordKanji").value.trim();
    const reading = document.getElementById("newWordReading").value.trim();
    const romaji = document.getElementById("newWordRomaji").value.trim();
    const meaning = document.getElementById("newWordMeaning").value.trim();
    const exJa = document.getElementById("newWordExJa").value.trim();
    const exZh = document.getElementById("newWordExZh").value.trim();
    const level = document.getElementById("newWordLevel").value;

    try {
      const res = await fetch("/api/words", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          word: kanji,
          reading: reading,
          romaji: romaji,
          meaning: meaning,
          example_ja: exJa,
          example_zh: exZh,
          level: level
        })
      });
      if (!res.ok) throw new Error("新增單字失敗");
      document.getElementById("addWordModal").classList.remove("active-modal");
      document.getElementById("addWordForm").reset();
      showToast(`單字「${kanji}」已成功新增！🎉`, "success");
      fetchWordsList();
      fetchStudyStats();
    } catch (err) {
      showToast("新增單字失敗", "error");
    }
  });

  // ------------------------------------------------------------------------
  // v3.1 新增功能互動事件綁定
  // ------------------------------------------------------------------------
  // 定級引導興趣標籤勾選上限監控 (最多 10 項)
  document.querySelectorAll("#onboardingHobbySelector input[type='checkbox']").forEach(cb => {
    cb.addEventListener("change", () => {
      const checked = document.querySelectorAll("#onboardingHobbySelector input[type='checkbox']:checked");
      if (checked.length > 10) {
        cb.checked = false;
        showToast("最多只能選擇 10 項興趣標籤", "info");
      }
      updateOnboardingHobbyCountTip();
    });
  });

  // 成就徽章館分類切換
  document.querySelectorAll(".badge-filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".badge-filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.badgeFilter = btn.dataset.badgeFilter;
      renderBadgesGallery();
    });
  });

  // 動態能力定級測試操作按鈕
  document.getElementById("btnStartPlacementQuiz").addEventListener("click", startPlacementQuiz);
  document.getElementById("btnPlacementBack").addEventListener("click", () => {
    document.getElementById("stepIndicator1").className = "p-step active";
    document.getElementById("stepIndicator2").className = "p-step";
    document.getElementById("placementStep1").style.display = "block";
    document.getElementById("placementStep2").style.display = "none";
  });
  document.getElementById("btnSubmitPlacementAnswers").addEventListener("click", submitPlacementAnswers);
  document.getElementById("btnFinishPlacement").addEventListener("click", () => {
    closePlacementModal();
    showToast(`恭喜完成能力定級！當前境界：【${state.currentUser.user_level}】`, "success");
    loadInitialData();
  });

  // 影音鎖定畫面中的「參與動態能力定級測試」按鈕
  const btnOpenPlacement = document.getElementById("btnOpenPlacementTest");
  if (btnOpenPlacement) {
    btnOpenPlacement.addEventListener("click", openPlacementModal);
  }

  // 頁尾顯目意見反饋按鈕
  const btnFooterFb = document.getElementById("btnFooterFeedback");
  if (btnFooterFb) {
    btnFooterFb.addEventListener("click", () => {
      document.getElementById("feedbackModal").classList.add("active-modal");
    });
  }

  // 背景每 15 秒追蹤一次影音觀看駐留時長遙測
  setInterval(() => {
    if (state.currentUser && state.activeTab === "video" && state.currentMedia) {
      recordBehaviorTelemetry({
        dwell_category: state.currentMedia.category,
        dwell_seconds: 15
      });
    }
  }, 15000);
});
