// ==============================================================================
// 國高中智慧學習平台 - 前端核心互動邏輯與狀態管理 (static/js/app.js)
// 說明：
// 1. 支援三色動態主題切換 (Dark / Light / System Default)。
// 2. 實作多身分快速切換、首次身分與年齡確認精靈。
// 3. 處理多維度題庫刷題、非強制考程排程、錯題本畢業機制、家長防越權專區與 AI 蘇格拉底導師。
// ==============================================================================

// 全域狀態物件
const state = {
  token: localStorage.getItem("token") || "",
  user: null,
  activeTab: "tab-study",
  currentMistakeFilter: false, // false: 待複習, true: 已畢業
  optionsData: null
};

// 測試用預設模擬使用者名單
const MOCK_USERS = {
  student: { email: "student.ming@example.com", name: "國中學生・小明", role: "student" },
  parent: { email: "parent.chen@example.com", name: "家長・陳爸爸", role: "parent" },
  teacher: { email: "teacher.lin@example.com", name: "教師・林老師", role: "teacher" }
};

// ==============================================================================
// 1. 系統初始化與主題監聽
// ==============================================================================
document.addEventListener("DOMContentLoaded", async () => {
  initTheme();
  setupEventListeners();
  await loadCurriculumOptions();
  
  // 預設以學生身分登入
  const savedRole = localStorage.getItem("simulated_role") || "student";
  document.getElementById("userRoleSwitcher").value = savedRole;
  await performLogin(savedRole);
});

// ------------------------------------------------------------------------------
// 主題設定核心邏輯 (支援 System Default、Dark、Light)
// ------------------------------------------------------------------------------
function initTheme() {
  const themeSelect = document.getElementById("themeSelect");
  const savedTheme = localStorage.getItem("app_theme") || "system";
  themeSelect.value = savedTheme;
  applyTheme(savedTheme);

  themeSelect.addEventListener("change", (e) => {
    const selectedTheme = e.target.value;
    localStorage.setItem("app_theme", selectedTheme);
    applyTheme(selectedTheme);
    if (state.token) {
      updateBackendTheme(selectedTheme);
    }
  });

  // 監聽作業系統深淺色外觀變更
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
    if (localStorage.getItem("app_theme") === "system") {
      applyTheme("system");
    }
  });
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
}

async function updateBackendTheme(theme) {
  try {
    await fetch("/api/auth/theme", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${state.token}`
      },
      body: JSON.stringify({ theme_preference: theme })
    });
  } catch (err) {
    console.warn("同步主題至後端略過：", err);
  }
}

// ==============================================================================
// 2. 身分登入與精靈機制
// ==============================================================================
async function performLogin(roleKey) {
  const mock = MOCK_USERS[roleKey] || MOCK_USERS.student;
  try {
    const res = await fetch("/api/auth/google-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: mock.email,
        name: mock.name,
        avatar: `https://api.dicebear.com/7.x/bottts/svg?seed=${roleKey}`
      })
    });
    const data = await res.json();
    state.token = data.access_token;
    localStorage.setItem("token", state.token);
    localStorage.setItem("simulated_role", roleKey);

    await fetchUserProfile();
  } catch (err) {
    console.error("登入失敗：", err);
  }
}

async function fetchUserProfile() {
  try {
    const res = await fetch("/api/auth/me", {
      headers: { "Authorization": `Bearer ${state.token}` }
    });
    if (!res.ok) throw new Error("取得個人檔案失敗");
    state.user = await res.json();
    renderUserProfile();

    // 檢查是否已完成首次登入身分與年齡精靈
    if (!state.user.is_onboarded) {
      document.getElementById("onboardingModal").classList.add("active");
    } else {
      document.getElementById("onboardingModal").classList.remove("active");
    }

    // 依身分切換介面
    handleRoleSpecificUI();
    // 依目前分頁載入資料
    refreshCurrentTab();
  } catch (err) {
    console.error(err);
  }
}

function renderUserProfile() {
  const u = state.user;
  if (!u) return;

  document.getElementById("userNameDisplay").textContent = `${u.name}`;
  document.getElementById("userAvatar").src = u.avatar || `https://api.dicebear.com/7.x/bottts/svg?seed=${u.role}`;

  // 角色標籤
  const roleNames = { student: "學生", parent: "家長", teacher: "教師" };
  document.getElementById("userRoleBadge").textContent = roleNames[u.role] || u.role;

  // 綁定代碼 (未成年學生專屬)
  const codeBadge = document.getElementById("userBindingCodeBadge");
  if (u.is_minor && u.binding_code) {
    codeBadge.textContent = `家長綁定代碼: ${u.binding_code}`;
    codeBadge.style.display = "inline-block";
  } else {
    codeBadge.style.display = "none";
  }

  // Combo 標籤
  const comboBadge = document.getElementById("userComboBadge");
  if (u.combo > 1) {
    comboBadge.textContent = `Combo x${u.combo} 🔥`;
    comboBadge.style.display = "inline-block";
  } else {
    comboBadge.style.display = "none";
  }

  // 經驗值與等級進度
  document.getElementById("levelTitleDisplay").textContent = u.level_title;
  if (u.level >= 10) {
    document.getElementById("expTextDisplay").textContent = `MAX EXP: ${u.exp}`;
  } else {
    document.getElementById("expTextDisplay").textContent = `EXP: ${u.exp} (距離升級還需 ${u.next_level_exp})`;
  }
  document.getElementById("expBarFill").style.width = `${u.level_progress_percent}%`;
}

function handleRoleSpecificUI() {
  const isParent = state.user && state.user.role === "parent";
  const parentTabBtn = document.getElementById("parentTabBtn");
  
  if (isParent) {
    parentTabBtn.style.display = "inline-flex";
  } else {
    // 學生身分時不展示家長專區
    parentTabBtn.style.display = "none";
    if (state.activeTab === "tab-parent") {
      switchTab("tab-study");
    }
  }
}

// ==============================================================================
// 3. 多維度動態學習選單與題庫刷題
// ==============================================================================
async function loadCurriculumOptions() {
  try {
    const res = await fetch("/api/study/curriculum-options");
    state.optionsData = await res.json();
    bindCurriculumSelects();
  } catch (err) {
    console.error("載入教材選項失敗：", err);
  }
}

function bindCurriculumSelects() {
  const levelSelect = document.getElementById("filterSchoolLevel");
  const gradeSelect = document.getElementById("filterGrade");
  const pubSelect = document.getElementById("filterPublisher");
  const subjSelect = document.getElementById("filterSubject");

  levelSelect.addEventListener("change", () => {
    const lvl = levelSelect.value;
    // 動態更新年級
    gradeSelect.innerHTML = "";
    (state.optionsData.grades_by_level[lvl] || []).forEach(g => {
      gradeSelect.innerHTML += `<option value="${g.id}">${g.name}</option>`;
    });

    // 動態更新出版社
    pubSelect.innerHTML = `<option value="">全部出版社</option>`;
    (state.optionsData.publishers_by_level[lvl] || []).forEach(p => {
      pubSelect.innerHTML += `<option value="${p}">${p}</option>`;
    });

    // 動態更新科目
    subjSelect.innerHTML = `<option value="">全部科目</option>`;
    (state.optionsData.subjects_by_level[lvl] || []).forEach(s => {
      subjSelect.innerHTML += `<option value="${s}">${s}</option>`;
    });
  });
}

async function loadQuestions() {
  const container = document.getElementById("questionsContainer");
  container.innerHTML = `<p style="text-align: center; color: var(--text-muted); padding: 2rem;">載入題目中...</p>`;

  const level = document.getElementById("filterSchoolLevel").value;
  const grade = document.getElementById("filterGrade").value;
  const pub = document.getElementById("filterPublisher").value;
  const subj = document.getElementById("filterSubject").value;
  const tag = document.getElementById("filterTag").value;

  const params = new URLSearchParams();
  if (level) params.append("school_level", level);
  if (grade) params.append("grade", grade);
  if (pub) params.append("publisher", pub);
  if (subj) params.append("subject", subj);
  if (tag) params.append("tag", tag);

  try {
    const res = await fetch(`/api/study/questions?${params.toString()}`);
    const questions = await res.json();

    if (!questions || questions.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 3rem; background: var(--bg-card); border-radius: var(--radius-md); border: 1px dashed var(--border-color);">
          <p style="font-size: 1.1rem; color: var(--text-secondary); margin-bottom: 0.5rem;">此篩選條件下暫無題目</p>
          <span style="font-size: 0.85rem; color: var(--text-muted);">建議切換出版社或清除限定標籤後再次搜尋。</span>
        </div>`;
      return;
    }

    container.innerHTML = "";
    questions.forEach((q, idx) => {
      container.appendChild(createQuestionCard(q, idx + 1));
    });
  } catch (err) {
    container.innerHTML = `<p style="color: var(--danger-color); text-align: center;">載入題目失敗，請稍候再試。</p>`;
  }
}

function createQuestionCard(q, index) {
  const card = document.createElement("div");
  card.className = "question-card";
  card.id = `q-card-${q.id}`;

  const tagsHtml = (q.tags || []).map(t => `<span class="tag-pill">${t}</span>`).join("");
  const optionLetters = ["A", "B", "C", "D"];

  const optionsHtml = (q.options || []).map((opt, i) => {
    const letter = optionLetters[i] || "";
    return `
      <button class="option-btn" data-qid="${q.id}" data-opt="${letter}" onclick="handleOptionSubmit(${q.id}, '${letter}')">
        <strong>${letter}.</strong> <span>${opt}</span>
      </button>
    `;
  }).join("");

  card.innerHTML = `
    <div class="question-header">
      <div style="display: flex; gap: 0.5rem; align-items: center;">
        <span style="font-weight: 700; color: var(--accent-color);">第 ${index} 題</span>
        <span style="font-size: 0.82rem; color: var(--text-secondary);">[${q.publisher}・${q.subject}] ${q.chapter}</span>
      </div>
      <div class="tag-list">${tagsHtml}</div>
    </div>
    <div class="question-text">${q.content}</div>
    <div class="options-grid" id="opt-grid-${q.id}">${optionsHtml}</div>
    <div id="feedback-${q.id}" style="display: none;"></div>
  `;

  return card;
}

async function handleOptionSubmit(questionId, selectedOption) {
  const grid = document.getElementById(`opt-grid-${questionId}`);
  const feedbackBox = document.getElementById(`feedback-${questionId}`);
  const buttons = grid.querySelectorAll(".option-btn");

  buttons.forEach(btn => btn.disabled = true);

  try {
    const res = await fetch("/api/study/submit", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${state.token}`
      },
      body: JSON.stringify({ question_id: questionId, selected_option: selectedOption })
    });

    const result = await res.json();

    // 更新選項視覺標示
    buttons.forEach(btn => {
      const opt = btn.getAttribute("data-opt");
      if (opt === result.correct_answer) {
        btn.classList.add("correct");
      } else if (opt === selectedOption && !result.is_correct) {
        btn.classList.add("incorrect");
      }
    });

    // 呈現即時回饋
    feedbackBox.style.display = "block";
    feedbackBox.className = `feedback-box ${result.is_correct ? "correct" : "incorrect"}`;
    feedbackBox.innerHTML = `
      <strong>${result.message}</strong>
      ${result.explanation ? `<p style="margin-top: 0.5rem;">📖 <strong>詳解：</strong>${result.explanation}</p>` : ""}
    `;

    // 重新載入個人經驗值
    await fetchUserProfile();
  } catch (err) {
    console.error("提交答案失敗：", err);
  }
}

// ==============================================================================
// 4. 【選填功能】智慧考程與每日行程規劃
// ==============================================================================
async function loadExamPlan() {
  try {
    const res = await fetch("/api/planner", {
      headers: { "Authorization": `Bearer ${state.token}` }
    });
    const plan = await res.json();
    renderExamPlan(plan);
  } catch (err) {
    console.error("載入考程規劃失敗：", err);
  }
}

function renderExamPlan(plan) {
  const toggle = document.getElementById("plannerToggle");
  toggle.checked = plan.is_enabled;

  document.getElementById("planExamName").value = plan.exam_name || "第一次段考";
  document.getElementById("planStartDate").value = plan.start_date;
  document.getElementById("planExamDate").value = plan.exam_date;
  document.getElementById("planBufferDays").value = plan.buffer_days;

  document.getElementById("planDaysRemaining").textContent = `${plan.days_remaining} 天`;
  document.getElementById("planProgressPercent").textContent = `${plan.current_progress}%`;

  const aheadStatusEl = document.getElementById("planAheadStatus");
  if (plan.is_ahead_of_schedule) {
    aheadStatusEl.innerHTML = `<span style="color: var(--success-color);">🌟 進度超前 (推薦預習)</span>`;
  } else {
    aheadStatusEl.innerHTML = `<span>按部就班</span>`;
  }

  // 渲染每日行程卡片
  const container = document.getElementById("dailyScheduleContainer");
  container.innerHTML = "";

  if (!plan.daily_schedule || plan.daily_schedule.length === 0) {
    container.innerHTML = `<p style="color: var(--text-muted); grid-column: 1/-1;">目前尚未設定考程範圍或尚未啟用排程。</p>`;
    return;
  }

  plan.daily_schedule.forEach(day => {
    const card = document.createElement("div");
    card.className = `day-card ${day.status}`;

    let statusBadge = "";
    if (day.status === "today") statusBadge = `<span class="tag-pill" style="background: var(--accent-color); color: #fff;">今日核心</span>`;
    if (day.is_buffer_day) statusBadge = `<span class="tag-pill" style="background: var(--warning-color); color: #fff;">考前緩衝</span>`;

    let tasksHtml = (day.tasks || []).map(t => `
      <div style="font-size: 0.85rem; margin-top: 0.4rem; padding-left: 0.5rem; border-left: 2px solid var(--accent-color);">
        <strong>[${t.subject}]</strong> ${t.chapter}
        <div style="font-size: 0.75rem; color: var(--text-muted);">建議練習: ${t.suggested_questions} 題</div>
      </div>
    `).join("");

    if (day.buffer_note) {
      tasksHtml += `<div style="font-size: 0.8rem; color: var(--warning-color); margin-top: 0.5rem;">${day.buffer_note}</div>`;
    }

    card.innerHTML = `
      <div class="day-title">
        <span>第 ${day.day_number} 天 (${day.date})</span>
        ${statusBadge}
      </div>
      <div>${tasksHtml}</div>
    `;

    container.appendChild(card);
  });
}

// 監聽考程開關切換
document.getElementById("plannerToggle").addEventListener("change", async (e) => {
  const isEnabled = e.target.checked;
  try {
    await fetch(`/api/planner/toggle?enabled=${isEnabled}`, {
      method: "PATCH",
      headers: { "Authorization": `Bearer ${state.token}` }
    });
    await loadExamPlan();
  } catch (err) {
    console.error("切換考程開關失敗：", err);
  }
});

// 監聽儲存考程設定
document.getElementById("savePlanConfigBtn").addEventListener("click", async () => {
  const isEnabled = document.getElementById("plannerToggle").checked;
  const examName = document.getElementById("planExamName").value;
  const startDate = document.getElementById("planStartDate").value;
  const examDate = document.getElementById("planExamDate").value;
  const bufferDays = parseInt(document.getElementById("planBufferDays").value, 10);

  const body = {
    is_enabled: isEnabled,
    exam_name: examName,
    start_date: startDate,
    exam_date: examDate,
    buffer_days: bufferDays,
    subjects_scope: [
      { subject: "數學", chapters: ["第一章 乘法公式與多項式", "第二章 一元二次方程式"] },
      { subject: "理化", chapters: ["第一單元 物質的組成", "第二單元 水溶液與反應"] },
      { subject: "英文", chapters: ["Unit 1 Review", "Unit 2 Past Tense"] }
    ]
  };

  try {
    const res = await fetch("/api/planner", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${state.token}`
      },
      body: JSON.stringify(body)
    });
    const updatedPlan = await res.json();
    renderExamPlan(updatedPlan);
    alert("✅ 智慧考程排程更新成功！");
  } catch (err) {
    console.error("儲存考程失敗：", err);
  }
});

// ==============================================================================
// 5. 智慧錯題本與熟練度畢業機制
// ==============================================================================
async function loadMistakes(isGraduated = false) {
  state.currentMistakeFilter = isGraduated;
  const container = document.getElementById("mistakesContainer");
  container.innerHTML = `<p style="text-align: center; color: var(--text-muted); padding: 2rem;">載入錯題中...</p>`;

  try {
    const res = await fetch(`/api/mistakes?graduated=${isGraduated}`, {
      headers: { "Authorization": `Bearer ${state.token}` }
    });
    const mistakes = await res.json();

    if (!mistakes || mistakes.length === 0) {
      container.innerHTML = `
        <div style="text-align: center; padding: 3rem; background: var(--bg-card); border-radius: var(--radius-md); border: 1px dashed var(--border-color);">
          <p style="font-size: 1.1rem; color: var(--text-secondary);">
            ${isGraduated ? "尚無熟練畢業的題目，繼續複習答對即可畢業！" : "🎉 太棒了！目前沒有待複習的錯題！"}
          </p>
        </div>`;
      return;
    }

    container.innerHTML = "";
    mistakes.forEach(m => {
      container.appendChild(createMistakeCard(m));
    });
  } catch (err) {
    container.innerHTML = `<p style="color: var(--danger-color); text-align: center;">載入錯題失敗。</p>`;
  }
}

function createMistakeCard(m) {
  const card = document.createElement("div");
  card.className = "question-card";
  card.id = `m-card-${m.id}`;

  const optionLetters = ["A", "B", "C", "D"];
  const optionsHtml = (m.options || []).map((opt, i) => {
    const letter = optionLetters[i];
    return `
      <button class="option-btn" onclick="handleMistakeReview(${m.id}, '${letter}')">
        <strong>${letter}.</strong> <span>${opt}</span>
      </button>
    `;
  }).join("");

  card.innerHTML = `
    <div class="question-header">
      <div>
        <span style="font-weight: 700; color: var(--accent-color);">[${m.subject}] ${m.chapter}</span>
        <span style="font-size: 0.8rem; color: var(--danger-color); margin-left: 0.5rem;">答錯次數: ${m.wrong_count} 次</span>
      </div>
      <div>
        <span class="tag-pill" style="background: var(--success-soft); color: var(--success-color);">熟練度: ${m.mastery_rate}%</span>
        <span class="tag-pill">連續答對: ${m.consecutive_correct}/2</span>
      </div>
    </div>
    <div class="question-text">${m.content}</div>
    <div class="options-grid" id="m-grid-${m.id}">${optionsHtml}</div>
    <div id="m-feedback-${m.id}" style="display: none;"></div>
  `;

  return card;
}

async function handleMistakeReview(mistakeId, selectedOption) {
  const feedbackBox = document.getElementById(`m-feedback-${mistakeId}`);
  try {
    const res = await fetch("/api/mistakes/review", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${state.token}`
      },
      body: JSON.stringify({ mistake_id: mistakeId, selected_option: selectedOption })
    });
    const result = await res.json();

    feedbackBox.style.display = "block";
    feedbackBox.className = `feedback-box ${result.is_correct ? "correct" : "incorrect"}`;
    feedbackBox.innerHTML = `
      <strong>${result.message}</strong>
      ${result.explanation ? `<p style="margin-top: 0.4rem;">📖 <strong>詳解：</strong>${result.explanation}</p>` : ""}
    `;

    await fetchUserProfile();
    // 延遲刷新錯題本
    setTimeout(() => {
      loadMistakes(state.currentMistakeFilter);
    }, 1200);
  } catch (err) {
    console.error("錯題複習作答失敗：", err);
  }
}

// 錯題本分頁按鈕
document.getElementById("viewPendingMistakesBtn").addEventListener("click", (e) => {
  e.target.classList.add("btn-primary");
  document.getElementById("viewGraduatedMistakesBtn").classList.remove("btn-primary");
  loadMistakes(false);
});

document.getElementById("viewGraduatedMistakesBtn").addEventListener("click", (e) => {
  e.target.classList.add("btn-primary");
  document.getElementById("viewPendingMistakesBtn").classList.remove("btn-primary");
  loadMistakes(true);
});

// ==============================================================================
// 6. 家長專區 (Parent Dashboard & 防越權)
// ==============================================================================
async function loadParentDashboard() {
  const container = document.getElementById("parentChildrenContainer");
  container.innerHTML = `<p style="color: var(--text-muted);">載入子女資訊中...</p>`;

  try {
    const res = await fetch("/api/parent/children", {
      headers: { "Authorization": `Bearer ${state.token}` }
    });
    if (!res.ok) {
      container.innerHTML = `<p style="color: var(--danger-color);">此功能僅限家長帳號存取 (RBAC 資安隔離保護)。</p>`;
      return;
    }
    const children = await res.json();

    if (!children || children.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1/-1; padding: 2.5rem; background: var(--bg-card); border-radius: var(--radius-md); text-align: center; border: 1px dashed var(--border-color);">
          <p style="font-size: 1.05rem; color: var(--text-secondary); margin-bottom: 0.5rem;">尚未綁定任何子女帳號</p>
          <span style="font-size: 0.85rem; color: var(--text-muted);">請點擊右上角「➕ 添加小孩帳號」，輸入小孩的 8 碼綁定代碼完成關聯。</span>
        </div>`;
      return;
    }

    container.innerHTML = "";
    children.forEach(child => {
      container.appendChild(createChildSummaryCard(child));
    });

    await loadParentHomeworks();
  } catch (err) {
    console.error("載入家長面板失敗：", err);
  }
}

function createChildSummaryCard(c) {
  const card = document.createElement("div");
  card.className = "question-card";

  card.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
      <div style="display: flex; align-items: center; gap: 0.75rem;">
        <img src="${c.avatar || 'https://api.dicebear.com/7.x/bottts/svg?seed=child'}" style="width: 44px; height: 44px; border-radius: 50%; border: 2px solid var(--accent-color);">
        <div>
          <h4 style="font-size: 1.05rem;">${c.name}</h4>
          <span style="font-size: 0.75rem; color: var(--text-muted);">${c.email}</span>
        </div>
      </div>
      <button class="action-btn btn-primary" onclick="openAssignModal(${c.child_id}, '${c.name}')">📝 指派作業</button>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; background: var(--bg-primary); padding: 0.85rem; border-radius: var(--radius-sm); font-size: 0.85rem;">
      <div>🏆 等級: <strong>${c.level_title}</strong></div>
      <div>⚡ 今日刷題: <strong>${c.today_practiced_count} 題</strong></div>
      <div>📝 錯題總數: <strong>${c.total_mistakes}</strong> (已畢業 ${c.graduated_mistakes})</div>
      <div>📋 待辦作業: <strong>${c.pending_homeworks_count} 項</strong></div>
    </div>
  `;

  return card;
}

async function loadParentHomeworks() {
  const hwContainer = document.getElementById("parentHomeworksContainer");
  try {
    const res = await fetch("/api/parent/homeworks", {
      headers: { "Authorization": `Bearer ${state.token}` }
    });
    const homeworks = await res.json();

    if (!homeworks || homeworks.length === 0) {
      hwContainer.innerHTML = `<p style="color: var(--text-muted);">目前尚未指派任何自主作業。</p>`;
      return;
    }

    hwContainer.innerHTML = homeworks.map(hw => `
      <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 1rem; margin-bottom: 0.75rem; display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h4 style="font-size: 0.95rem;">${hw.title} <span style="font-size: 0.75rem; color: var(--accent-color);">[${hw.subject}]</span></h4>
          <p style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 0.2rem;">
            對象: <strong>${hw.child_name}</strong> | 目標: ${hw.target_count} 題 | 截止: ${hw.due_date}
          </p>
        </div>
        <span class="badge ${hw.status === 'completed' ? 'badge-role' : 'badge-code'}">
          ${hw.status === 'completed' ? '已完成' : '進行中'}
        </span>
      </div>
    `).join("");
  } catch (err) {
    console.error("載入作業進度失敗：", err);
  }
}

function openAssignModal(childId, childName) {
  document.getElementById("assignTargetChildId").value = childId;
  const dueDateInput = document.getElementById("hwDueDate");
  // 預設一週後
  const d = new Date();
  d.setDate(d.getDate() + 7);
  dueDateInput.value = d.toISOString().split("T")[0];

  document.getElementById("assignHomeworkModal").classList.add("active");
}

// ==============================================================================
// 7. AI 智慧小家教（拍照引導與蘇格拉底教學）
// ==============================================================================
document.getElementById("openTutorBtn").addEventListener("click", () => {
  document.getElementById("tutorModal").classList.add("active");
});

document.getElementById("closeTutorBtn").addEventListener("click", () => {
  document.getElementById("tutorModal").classList.remove("active");
});

// 照片預覽處理
const tutorFileInput = document.getElementById("tutorFileInput");
const imagePreview = document.getElementById("imagePreview");
const imagePreviewContainer = document.getElementById("imagePreviewContainer");
let currentBase64Image = null;

tutorFileInput.addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (file) {
    const reader = new FileReader();
    reader.onload = (event) => {
      currentBase64Image = event.target.result;
      imagePreview.src = currentBase64Image;
      imagePreviewContainer.style.display = "block";
    };
    reader.readAsDataURL(file);
  }
});

// 啟動蘇格拉底引導分析
document.getElementById("askTutorSubmitBtn").addEventListener("click", async () => {
  const subject = document.getElementById("tutorSubjectSelect").value;
  const studentThought = document.getElementById("tutorStudentThought").value;
  const resultBox = document.getElementById("tutorResultBox");

  resultBox.style.display = "block";
  resultBox.innerHTML = `<p style="text-align: center; color: var(--text-muted);">🦉 小老師正在細心分析題目觀念與思考脈絡...</p>`;

  try {
    const res = await fetch("/api/tutor/ask-json", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${state.token}`
      },
      body: JSON.stringify({
        image_base64: currentBase64Image,
        subject: subject,
        student_thought: studentThought
      })
    });

    const data = await res.json();

    const stepsHtml = (data.thought_steps || []).map(s => `<li style="margin-bottom: 0.35rem;">${s}</li>`).join("");

    resultBox.innerHTML = `
      <div style="background: var(--bg-primary); padding: 1.25rem; border-radius: var(--radius-md); border: 1px solid var(--border-color);">
        <h4 style="color: var(--accent-color); margin-bottom: 0.5rem;">📚 題目考察核心觀念：</h4>
        <p style="font-weight: 600; margin-bottom: 1rem;">${data.core_concept}</p>

        <h4 style="margin-bottom: 0.5rem;">🔍 思考拆解三部曲：</h4>
        <ol style="padding-left: 1.25rem; margin-bottom: 1rem;">${stepsHtml}</ol>

        <div style="background: var(--accent-soft); padding: 0.85rem; border-radius: var(--radius-sm); border-left: 4px solid var(--accent-color);">
          <strong>❓ 換你動動腦：</strong>
          <p style="margin-top: 0.3rem;">${data.socratic_question}</p>
        </div>
      </div>
    `;
  } catch (err) {
    resultBox.innerHTML = `<p style="color: var(--danger-color);">引導分析暫時無法連線，請稍候重試。</p>`;
  }
});

// ==============================================================================
// 8. 其他彈窗事件 (Onboarding, Feedback, Add Child, Assign Homework)
// ==============================================================================
function setupEventListeners() {
  // 分頁切換
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const tabId = btn.getAttribute("data-tab");
      switchTab(tabId);
    });
  });

  // 測試身分切換
  document.getElementById("userRoleSwitcher").addEventListener("change", async (e) => {
    await performLogin(e.target.value);
  });

  // 題目篩選按鈕
  document.getElementById("applyFilterBtn").addEventListener("click", () => {
    loadQuestions();
  });

  // 首次登錄精靈提交
  document.getElementById("onboardingForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const role = document.getElementById("onboardRole").value;
    const age = parseInt(document.getElementById("onboardAge").value, 10);
    const schoolLevel = document.getElementById("onboardSchoolLevel").value;
    const grade = document.getElementById("onboardGrade").value;

    try {
      const res = await fetch("/api/auth/onboarding", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${state.token}`
        },
        body: JSON.stringify({
          role: role,
          age: age,
          school_level: schoolLevel,
          grade: grade
        })
      });
      state.user = await res.json();
      document.getElementById("onboardingModal").classList.remove("active");
      renderUserProfile();
      handleRoleSpecificUI();
      refreshCurrentTab();
    } catch (err) {
      console.error("提交精靈確認失敗：", err);
    }
  });

  // 家長添加小孩彈窗
  document.getElementById("openAddChildBtn").addEventListener("click", () => {
    document.getElementById("addChildModal").classList.add("active");
  });
  document.getElementById("closeAddChildBtn").addEventListener("click", () => {
    document.getElementById("addChildModal").classList.remove("active");
  });
  document.getElementById("addChildForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const code = document.getElementById("inputBindingCode").value.trim();
    const email = document.getElementById("inputChildEmail").value.trim();

    try {
      const res = await fetch("/api/parent/bind-child", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${state.token}`
        },
        body: JSON.stringify({ binding_code: code || null, child_email: email || null })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "綁定失敗");
      alert(data.message);
      document.getElementById("addChildModal").classList.remove("active");
      await loadParentDashboard();
    } catch (err) {
      alert(`❌ 綁定失敗：${err.message}`);
    }
  });

  // 指派作業彈窗
  document.getElementById("closeAssignHomeworkBtn").addEventListener("click", () => {
    document.getElementById("assignHomeworkModal").classList.remove("active");
  });
  document.getElementById("assignHomeworkForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const childId = parseInt(document.getElementById("assignTargetChildId").value, 10);
    const title = document.getElementById("hwTitle").value.trim();
    const subject = document.getElementById("hwSubject").value;
    const targetCount = parseInt(document.getElementById("hwTargetCount").value, 10);
    const dueDate = document.getElementById("hwDueDate").value;
    const desc = document.getElementById("hwDescription").value.trim();

    try {
      const res = await fetch("/api/parent/homework", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${state.token}`
        },
        body: JSON.stringify({
          child_id: childId,
          title: title,
          subject: subject,
          target_count: targetCount,
          due_date: dueDate,
          description: desc || null
        })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "指派失敗");
      }
      alert("✅ 作業已成功指派！");
      document.getElementById("assignHomeworkModal").classList.remove("active");
      await loadParentDashboard();
    } catch (err) {
      alert(`❌ 指派失敗：${err.message}`);
    }
  });

  // 意見反饋彈窗
  document.getElementById("openFeedbackBtn").addEventListener("click", () => {
    document.getElementById("feedbackModal").classList.add("active");
  });
  document.getElementById("closeFeedbackBtn").addEventListener("click", () => {
    document.getElementById("feedbackModal").classList.remove("active");
  });
  document.getElementById("feedbackForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const cat = document.getElementById("fbCategory").value;
    const content = document.getElementById("fbContent").value.trim();
    const email = document.getElementById("fbContactEmail").value.trim();

    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${state.token}`
        },
        body: JSON.stringify({ category: cat, content: content, contact_email: email || null })
      });
      const data = await res.json();
      alert(data.message);
      document.getElementById("feedbackModal").classList.remove("active");
      document.getElementById("feedbackForm").reset();
    } catch (err) {
      alert("送出反饋失敗，請稍候重試。");
    }
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
  });
  document.querySelectorAll(".tab-content").forEach(content => {
    content.classList.toggle("active", content.id === tabId);
  });
  refreshCurrentTab();
}

function refreshCurrentTab() {
  if (state.activeTab === "tab-study") {
    loadQuestions();
  } else if (state.activeTab === "tab-planner") {
    loadExamPlan();
  } else if (state.activeTab === "tab-mistakes") {
    loadMistakes(state.currentMistakeFilter);
  } else if (state.activeTab === "tab-parent") {
    loadParentDashboard();
  }
}
