import sys  # 導入 sys 模組以設定標準輸出編碼
if hasattr(sys.stdout, "reconfigure"):  # 檢查標準輸出是否支援重新配置編碼
    sys.stdout.reconfigure(encoding="utf-8")  # 重新配置標準輸出為 UTF-8 編碼以相容萬國碼符號
from fastapi.testclient import TestClient  # 從 fastapi.testclient 導入 TestClient 以進行端點測試
from main import app  # 從 main 模組導入核心 FastAPI 應用程式實例
# ---------------------------------------------------------------------------------------------------------------------- # 執行 API 端點整合測試主函式
def run_api_tests() -> None:  # 定義整合端點測試主函式
    client = TestClient(app)  # 初始化 FastAPI 測試客戶端實例
    print("===== 開始測試 FastAPI 伺服器各端點 =====")  # 印出測試開始標題
    r_home = client.get("/")  # 測試前端首頁靜態路由
    assert r_home.status_code == 200, "首頁路由狀態碼應為 200"  # 驗證首頁狀態碼
    assert "<title>日語智慧雲端學習助手" in r_home.text, "首頁應包含標題文字"  # 驗證首頁內容標題
    print("[OK] 前端首頁 HTML 路由測試成功！")  # 印出首頁測試成功日誌
    r_css = client.get("/static/style.css")  # 測試靜態 CSS 路由
    assert r_css.status_code == 200, "CSS 樣式表狀態碼應為 200"  # 驗證 CSS 載入成功
    r_js = client.get("/static/script.js")  # 測試靜態 JS 路由
    assert r_js.status_code == 200, "JavaScript 腳本狀態碼應為 200"  # 驗證 JS 載入成功
    print("[OK] 前端靜態資源 (CSS & JS) 掛載路由正常！")  # 印出靜態資源測試成功日誌
    r_manifest = client.get("/manifest.json")  # 測試 PWA Manifest 端點
    assert r_manifest.status_code == 200, "Manifest 狀態碼應為 200"  # 驗證 Manifest 狀態
    assert "日語雲端智慧學習助手" in r_manifest.text, "Manifest 應包含應用名稱"  # 驗證內容
    print("[OK] PWA Manifest 資訊清單端點正常！")  # 印出 Manifest 正常日誌
    r_sw = client.get("/sw.js")  # 測試 PWA Service Worker 腳本端點
    assert r_sw.status_code == 200, "Service Worker 狀態碼應為 200"  # 驗證 SW 狀態
    assert "CACHE_NAME" in r_sw.text, "SW 腳本應包含快取變數"  # 驗證 SW 內容
    print("[OK] PWA Service Worker 快取腳本端點正常！")  # 印出 SW 正常日誌
    import time  # 導入 time 模組以產生不重複時間戳記
    test_uid = f"api_test_uid_{int(time.time()*1000)}"  # 定義動態唯一測試 UID
    r_login = client.post("/api/user/login", json={  # 測試 Google 登入驗證端點
        "uid": test_uid,  # 測試 UID
        "email": "tester777@gmail.com",  # 測試 Email
        "display_name": "API 試煉員",  # 測試暱稱
        "photo_url": "https://api.dicebear.com/7.x/bottts/svg?seed=777"  # 測試頭像
    })  # 結束登入請求
    assert r_login.status_code == 200, "Google 登入端點狀態碼應為 200"  # 驗證登入狀態碼
    user_prof = r_login.json()  # 解析使用者檔案
    assert user_prof["uid"] == test_uid, "回傳 UID 應吻合"  # 驗證 UID
    assert user_prof["user_level"] == "新手小白", "預設等級應為新手小白"  # 驗證新手階級
    print(f"[OK] Google 登入端點測試成功：{user_prof['display_name']}，等級：{user_prof['user_level']}")  # 印出登入日誌
    r_prof = client.get(f"/api/user/profile?uid={user_prof['uid']}")  # 測試查詢個人檔案端點
    assert r_prof.status_code == 200, "查詢個人檔案狀態碼應為 200"  # 驗證狀態碼
    print("[OK] 個人檔案查詢端點測試成功！")  # 印出個人檔案查詢日誌
    ten_hobbies = ["動漫", "J-Pop音樂", "日本美食", "關東關西旅遊", "日劇影視", "電玩遊戲", "商業金融", "體育運動", "科技前沿", "歷史文化"]  # 定義 10 項興趣標籤清單
    r_pref = client.patch(f"/api/user/preferences?uid={user_prof['uid']}", json={  # 測試更新偏好端點（支援上限 10 個標籤）
        "hobbies": ten_hobbies,  # 傳入 10 個擴充標籤
        "default_sub_ja": True,  # 日文字幕開啟
        "default_sub_zh": True  # 中文字幕開啟
    })  # 結束更新請求
    assert r_pref.status_code == 200, "偏好更新端點狀態碼應為 200"  # 驗證狀態碼
    assert len(r_pref.json()["hobbies"]) == 10, "自選興趣標籤長度應擴充至 10"  # 驗證標籤擴充上限
    print("[OK] 興趣標籤（支援上限 10 項）與雙語字幕偏好端點更新成功！")  # 印出偏好更新日誌
    r_badges = client.get(f"/api/badges?uid={user_prof['uid']}")  # 測試成就徽章館端點
    assert r_badges.status_code == 200, "徽章館端點狀態碼應為 200"  # 驗證徽章狀態碼
    badges_res = r_badges.json()  # 解析徽章陣列 JSON
    assert len(badges_res) == 8, "全站成就徽章總數應為 8 枚"  # 驗證徽章總數
    print(f"[OK] 成就徽章館 API 端點測試成功：共載入 {len(badges_res)} 枚徽章！")  # 印出徽章館日誌
    r_pq = client.get("/api/onboarding/placement-questions?target_tier=外門弟子")  # 測試定級測驗試題端點
    assert r_pq.status_code == 200, "取得分級題目端點狀態碼應為 200"  # 驗證試題狀態碼
    questions = r_pq.json()  # 解析分級試題
    assert len(questions) == 4, "外門弟子挑戰應傳回 4 道 N5 題目"  # 驗證試題數量
    print(f"[OK] 能力定級測驗出題 API 端點測試成功：獲取 {len(questions)} 道試題！")  # 印出試題日誌
    r_submit_novice = client.post(f"/api/onboarding/placement-submit?uid={user_prof['uid']}", json={  # 測試新手小白免試定級
        "target_tier": "新手小白",  # 目標境界為新手小白
        "answers": {}  # 免試作答為空字典
    })  # 結束免試提交請求
    assert r_submit_novice.status_code == 200, "新手小白免試提交狀態碼應為 200"  # 驗證免試狀態碼
    assert r_submit_novice.json()["assigned_tier"] == "新手小白", "新手小白免試應直通新手小白"  # 驗證免試結果
    print(f"[OK] 新手小白免試定級 API 測試成功：{r_submit_novice.json()['message']}")  # 印出免試日誌
    outer_correct_ans = {str(q["id"]): q["correct_answer"] for q in questions}  # 組合 4 題全對作答對照表
    r_submit_outer = client.post(f"/api/onboarding/placement-submit?uid={user_prof['uid']}", json={  # 測試外門弟子全對合格定級
        "target_tier": "外門弟子",  # 目標挑戰外門弟子
        "answers": outer_correct_ans  # 全對作答
    })  # 結束外門提交請求
    assert r_submit_outer.status_code == 200, "外門作答提交狀態碼應為 200"  # 驗證狀態碼
    outer_res = r_submit_outer.json()  # 解析定級結果
    assert outer_res["assigned_tier"] == "外門弟子", "全對應定級為外門弟子"  # 驗證定級境界
    assert outer_res["score"] == 100.0, "滿分得分應為 100.0%"  # 驗證滿分得分
    print(f"[OK] 能力定級考核合格 API 測試成功：定級為【{outer_res['assigned_tier']}】！")  # 印出合格日誌
    outer_array_ans = [{"question_id": q["id"], "selected_option": q["correct_answer"]} for q in questions]  # 組合陣列格式作答清單
    r_body_submit = client.post("/api/onboarding/placement-submit", json={  # 測試純 Body 傳入 UID 與陣列格式作答
        "uid": user_prof["uid"],  # 於 JSON 主體中傳入 UID
        "target_tier": "外門弟子",  # 目標挑戰外門弟子
        "hobbies": ["動漫經典", "J-Pop 音樂"],  # 附帶興趣標籤
        "answers": outer_array_ans  # 陣列格式作答
    })  # 結束純 Body 提交
    assert r_body_submit.status_code == 200, "純 Body 提交狀態碼應為 200"  # 驗證純 Body 提交成功
    assert r_body_submit.json()["assigned_tier"] == "外門弟子", "純 Body 提交應成功定級外門弟子"  # 驗證定級結果
    print("[OK] 純 JSON Body 與作答陣列格式定級 API 測試成功！")  # 印出陣列格式測試成功日誌
    r_missing_uid = client.post("/api/onboarding/placement-submit", json={  # 測試未提供 UID 之防禦機制
        "target_tier": "外門弟子",  # 傳入目標階級
        "answers": []  # 傳入空白作答
    })  # 結束無 UID 提交
    assert r_missing_uid.status_code == 400, "未提供 UID 時應回傳 HTTP 400"  # 驗證防禦機制狀態碼
    print("[OK] 缺少 UID 時防禦驗證 HTTP 400 測試成功！")  # 印出防禦驗證日誌
    r_telemetry = client.post(f"/api/user/behavior?uid={user_prof['uid']}", json={  # 測試動態行為遙測回報端點
        "category": "動漫",  # 互動分類為動漫
        "action_type": "view_media",  # 互動行為為觀看影音
        "duration_seconds": 30.0,  # 互動時長 30 秒
        "word": "写真"  # 關聯日文生詞
    })  # 結束遙測回報請求
    assert r_telemetry.status_code == 200, "行為遙測端點狀態碼應為 200"  # 驗證遙測狀態碼
    assert r_telemetry.json()["status"] == "ok", "行為遙測回傳狀態應為 ok"  # 驗證回傳狀態
    print("[OK] 動態行為偏好遙測追蹤 API 端點測試成功！")  # 印出遙測日誌
    r_telemetry_body = client.post("/api/user/behavior", json={  # 測試純 Body 遙測端點
        "uid": user_prof["uid"],  # 於 Body 傳入 UID
        "dwell_category": "J-Pop",  # 前端實際發送之 dwell_category
        "dwell_seconds": 15.0  # 前端實際發送之 dwell_seconds
    })  # 結束純 Body 遙測
    assert r_telemetry_body.status_code == 200, "純 Body 遙測端點狀態碼應為 200"  # 驗證遙測狀態碼
    print("[OK] 純 JSON Body 動態行為偏好遙測 API 測試成功！")  # 印出遙測測試日誌
    r_eval_tier = client.post(f"/api/user/evaluate-tier?uid={user_prof['uid']}")  # 測試全自動階級與徽章評估端點
    assert r_eval_tier.status_code == 200, "自動階級評估端點狀態碼應為 200"  # 驗證評估狀態碼
    assert "new_level" in r_eval_tier.json(), "評估結果應包含最新階級"  # 驗證最新階級
    print(f"[OK] 全自動階級與成就徽章晉階評審 API 運作成功：【{r_eval_tier.json()['new_level']}】！")  # 印出審核日誌
    r_kana = client.post(f"/api/beginner/kana-complete?uid={user_prof['uid']}")  # 測試標記完成五十音端點
    assert r_kana.status_code == 200, "五十音標記完成狀態碼應為 200"  # 驗證狀態碼
    assert r_kana.json()["kana_completed"] is True, "五十音旗標應為 True"  # 驗證五十音旗標
    print("[OK] 五十音研讀完成端點測試成功！")  # 印出五十音端點日誌
    client.post(f"/api/beginner/game-submit?uid={user_prof['uid']}", json={"game_id": 1, "accuracy": 85.0, "score": 850})  # 提交試煉第一關
    client.post(f"/api/beginner/game-submit?uid={user_prof['uid']}", json={"game_id": 2, "accuracy": 90.0, "score": 900})  # 提交試煉第二關
    r_g3 = client.post(f"/api/beginner/game-submit?uid={user_prof['uid']}", json={"game_id": 3, "accuracy": 88.0, "score": 880})  # 提交試煉第三關
    assert r_g3.status_code == 200, "試煉成績提交狀態碼應為 200"  # 驗證狀態碼
    fb_g3 = r_g3.json()  # 解析回饋 JSON
    assert fb_g3["is_promoted"] is True or fb_g3["new_level"] == "外門弟子", "滿足條件或已定級應為外門弟子"  # 驗證階級
    print(f"[OK] 新手試煉自動晉級閘門端點成功：當前境界為【{fb_g3['new_level']}】！")  # 印出晉級日誌
    r_media = client.get("/api/media")  # 測試官方合法影音查詢端點
    assert r_media.status_code == 200, "取得影音列表狀態碼應為 200"  # 驗證影音端點狀態
    media_list = r_media.json()  # 解析影音清單
    assert len(media_list) >= 2, "影音清單應至少包含 2 部影片"  # 驗證影片數量
    target_media = media_list[0]  # 取得目標影片
    print(f"[OK] 官方合法雙語影音列表 API 測試成功：共 {len(media_list)} 部影片")  # 印出影音查詢日誌
    r_mfb = client.post(f"/api/media/{target_media['id']}/feedback", json={"media_id": target_media["id"], "action": "interested"})  # 測試影音反饋
    assert r_mfb.status_code == 200, "影音評價反饋狀態碼應為 200"  # 驗證評價狀態碼
    print("[OK] 影音推薦評價 API 測試成功！")  # 印出影音評價日誌
    r_fb = client.post("/api/feedback", json={  # 測試直接意見反饋端點
        "user_name": "API測試員",  # 使用者名稱
        "user_email": "api@test.com",  # 使用者信箱
        "category": "功能建議",  # 反饋類別
        "message": "端點測試意見反饋順利執行！",  # 反饋內容
        "target_email": "ytpre.new1@gmail.com"  # 目標官方信箱
    })  # 結束反饋請求
    assert r_fb.status_code == 200, "意見反饋端點狀態碼應為 200"  # 驗證反饋狀態碼
    assert r_fb.json()["target_email"] == "ytpre.new1@gmail.com", "反饋目標信箱應為官方信箱"  # 驗證目標信箱
    print("[OK] 意見反饋路由端點成功直達 ytpre.new1@gmail.com！")  # 印出反饋日誌
    r_words = client.get("/api/words")  # 測試查詢單字庫 API
    assert r_words.status_code == 200, "取得單字庫狀態碼應為 200"  # 驗證單字庫查詢狀態碼
    words_data = r_words.json()  # 解析回傳單字陣列 JSON
    assert len(words_data) >= 20, "單字清單應至少包含 20 筆單字"  # 驗證單字數量
    print(f"[OK] 雲端單字本 API 查詢成功，收錄單字數：{len(words_data)}")  # 印出單字庫查詢日誌
    target_word = words_data[0]  # 取得測試單字
    r_srs = client.patch(f"/api/words/{target_word['id']}/srs", json={"srs_status": "mastered"})  # 測試更新單字 SRS 為已掌握
    assert r_srs.status_code == 200, "更新 SRS 狀態碼應為 200"  # 驗證更新狀態碼
    assert r_srs.json()["srs_status"] == "mastered", "更新後狀態應為 mastered"  # 驗證更新值
    print(f"[OK] SRS 間隔重複狀態更新端點成功，單字「{target_word['word']}」已設為 mastered")  # 印出更新成功日誌
    r_streak = client.get("/api/streak")  # 測試打卡日曆 API
    assert r_streak.status_code == 200, "取得打卡日曆狀態碼應為 200"  # 驗證打卡狀態碼
    streak_res = r_streak.json()  # 解析打卡日曆資料
    assert "current_streak" in streak_res, "回傳資料應包含 current_streak"  # 驗證欄位存在
    assert "month_days" in streak_res, "回傳資料應包含 month_days"  # 驗證月份陣列
    print(f"[OK] 連續打卡日曆 API 運作成功：目前連續 {streak_res['current_streak']} 天")  # 印出打卡 API 日誌
    r_quiz_mc = client.post("/api/quiz/generate", json={"mode": "multiple_choice", "pool": "all", "count": 5})  # 測試四選一測驗生成
    assert r_quiz_mc.status_code == 200, "四選一生成狀態碼應為 200"  # 驗證生成狀態碼
    mc_questions = r_quiz_mc.json()  # 解析測驗題目 JSON
    assert len(mc_questions) == 5, "生成題目數量應為 5"  # 驗證題目數量
    assert len(mc_questions[0]["options"]) == 4, "四選一選項數量應為 4"  # 驗證選項數
    print("[OK] 單字小測驗四選一生成端點測試成功！")  # 印出選擇題端點成功日誌
    q1 = mc_questions[0]  # 取得題目物件
    r_submit = client.post("/api/quiz/submit", json={  # 測試提交作答端點
        "word_id": q1["word_id"],  # 傳入正確單字編號
        "user_answer": str(q1["word_id"]),  # 傳入正確選項編號
        "current_combo": 2,  # 模擬具備 2 連擊
        "mode": "multiple_choice"  # 題型為四選一
    })  # 結束提交作答請求
    assert r_submit.status_code == 200, "提交作答狀態碼應為 200"  # 驗證提交狀態碼
    feedback = r_submit.json()  # 解析回饋 JSON
    assert feedback["is_correct"] is True, "提交正確答案判定應為 True"  # 驗證正誤判定
    assert feedback["updated_combo"] == 3, "連擊數應由 2 晉升為 3"  # 驗證連擊晉升
    assert feedback["earned_score"] > 0, "獲得分數應大於 0"  # 驗證分數計算
    print(f"[OK] 測驗提交結算端點成功：得到 {feedback['earned_score']} 分，Combo 升至 {feedback['updated_combo']}")  # 印出結算成功日誌
    r_stats = client.get("/api/stats")  # 測試學習總體進度統計端點
    assert r_stats.status_code == 200, "取得統計狀態碼應為 200"  # 驗證統計端點狀態碼
    stats = r_stats.json()  # 解析統計資料
    print(f"[OK] 學習統計 API 運作成功：全體準確率 {stats['overall_accuracy']}%")  # 印出統計日誌
    print("====== FastAPI 伺服器所有 API 端點測試全部圓滿通過！======")  # 印出測試完成訊息
# ---------------------------------------------------------------------------------------------------------------------- # 執行測試進入點
if __name__ == "__main__":  # 判斷是否為直接執行腳本
    run_api_tests()  # 呼叫執行端點測試主函式
