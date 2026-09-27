import sys  # 導入 sys 模組以設定離開狀態碼與終端機輸出編碼
if hasattr(sys.stdout, "reconfigure"):  # 檢查標準輸出是否支援重新配置編碼
    sys.stdout.reconfigure(encoding="utf-8")  # 重新配置標準輸出為 UTF-8 編碼以相容萬國碼符號
from database import (  # 導入資料庫模組所有核心資料庫操作函式
    init_db,  # 導入資料庫結構與種子初始化函式
    get_all_words,  # 導入查詢單字清單函式
    get_word_by_id,  # 導入主鍵單字查詢函式
    update_word_srs,  # 導入掌握度更新函式
    create_word,  # 導入新增單字寫入函式
    delete_word,  # 導入刪除單字函式
    get_study_statistics,  # 導入學習進度統計函式
    record_study_activity,  # 導入每日學習打卡記錄函式
    get_streak_calendar_data,  # 導入連續打卡天數與月份日曆數據函式
    get_or_create_user,  # 導入使用者帳號讀取與自動建立函式
    update_user_preferences,  # 導入使用者興趣與字幕偏好更新函式
    mark_kana_completed,  # 導入五十音研讀完成標記函式
    record_beginner_game_score,  # 導入記錄新手試煉成績並自動判定晉升函式
    check_and_auto_promote,  # 導入晉級判定核心函式
    get_all_media,  # 導入取得官方影音與字幕清單函式
    record_media_feedback,  # 導入記錄影音評價反饋函式
    save_feedback,  # 導入儲存直接意見反饋函式
    get_user_badges,  # 導入成就徽章館清單查詢函式
    get_placement_questions,  # 導入獲取動態能力定級測驗試題函式
    evaluate_placement_test,  # 導入動態能力定級測試評分與智慧降階判定函式
    record_behavior_telemetry,  # 導入記錄行為遙測與動態微調推薦權重函式
    evaluate_and_update_user_tier_and_badges  # 導入使用者境界與成就徽章自動評審函式
)  # 結束 database 模組函式導入宣告
from quiz_service import generate_quiz_session, evaluate_quiz_answer  # 導入測驗出題與計分服務函式
from models import QuizGenerateRequest, QuizAnswerSubmit  # 導入請求資料模型類別
# ---------------------------------------------------------------------------------------------------------------------- # 執行系統單元與業務邏輯測試主函式
def run_all_tests() -> None:  # 定義測試整合主函式
    print("===== 開始執行日語學習系統後端測試 =====")  # 印出測試開始標題
    init_db()  # 初始化資料庫結構、種子單字與打卡初始記錄
    words = get_all_words()  # 查詢資料庫中所有單字
    assert len(words) >= 20, "單字庫種子數量應大於或等於 20 筆"  # 驗證單字庫初始數量充足
    print(f"[OK] 單字庫讀取成功，目前收錄總筆數：{len(words)}")  # 印出單字讀取成功日誌
    first_word = words[0]  # 取得列表中的第一筆單字
    updated = update_word_srs(first_word["id"], "hard", is_correct=False)  # 測試更新單字 SRS 為困難並累計答錯
    assert updated["srs_status"] == "hard", "SRS 狀態更新應為 hard"  # 斷言驗證狀態變更
    print(f"[OK] SRS 狀態更新測試成功，單字「{first_word['word']}」已標記為 hard")  # 印出更新成功日誌
    record_study_activity(words_count=3, quiz_count=1)  # 測試寫入今日學習打卡活動
    streak_data = get_streak_calendar_data()  # 取得打卡日曆統計
    assert streak_data["current_streak"] >= 1, "連續打卡天數應大於或等於 1 天"  # 驗證連續天數計數正常
    assert streak_data["total_active_days"] >= 1, "累計打卡天數應大於或等於 1 天"  # 驗證累計天數正常
    assert len(streak_data["month_days"]) >= 28, "當月日曆天數應介於 28 至 31 天之間"  # 驗證當月天數結構
    print(f"[OK] 連續打卡日曆演算法測試成功：目前連續 {streak_data['current_streak']} 天，累計 {streak_data['total_active_days']} 天")  # 印出打卡測試日誌
    req_mc = QuizGenerateRequest(mode="multiple_choice", pool="all", count=5)  # 建立四選一測驗生成請求
    quiz_mc = generate_quiz_session(req_mc)  # 生成四選一題目清單
    assert len(quiz_mc) == 5, "生成的四選一題目數量應為 5"  # 驗證題目數量正確
    assert len(quiz_mc[0].options) == 4, "每題四選一應具備 4 個選項"  # 驗證選項數量為四個
    print("[OK] 四選一小測驗題目生成測試成功，干擾項與隨機排序正常")  # 印出選擇題生成成功日誌
    q1 = quiz_mc[0]  # 取得測驗第一題
    submit_correct = QuizAnswerSubmit(word_id=q1.word_id, user_answer=str(q1.word_id), current_combo=0, mode="multiple_choice")  # 模擬送出正確解答
    fb_correct = evaluate_quiz_answer(submit_correct)  # 取得即時判定回饋
    assert fb_correct.is_correct is True, "提交正確答案時判定應為 True"  # 驗證答對判定
    assert fb_correct.updated_combo == 1, "連續答對連擊數應累加為 1"  # 驗證連擊累加
    assert fb_correct.earned_score > 0, "答對時獲得分數應大於 0"  # 驗證得分計算
    print(f"[OK] 測驗正確作答判定成功：連擊數 {fb_correct.updated_combo}，獲得 {fb_correct.earned_score} 分")  # 印出答對回饋日誌
    submit_combo = QuizAnswerSubmit(word_id=q1.word_id, user_answer=str(q1.word_id), current_combo=3, mode="multiple_choice")  # 模擬高連擊送出
    fb_combo = evaluate_quiz_answer(submit_combo)  # 取得高連擊加成判定
    assert fb_combo.updated_combo == 4, "Combo 應累加至 4"  # 驗證連擊延續
    assert fb_combo.earned_score > fb_correct.earned_score, "高連擊得分應享額外倍率加成"  # 驗證連擊獎勵倍率機制
    print(f"[OK] 連擊加成計分測試成功：獲得加成 {fb_combo.earned_score} 分！")  # 印出連擊獎勵日誌
    submit_wrong = QuizAnswerSubmit(word_id=q1.word_id, user_answer="wrong_answer_xyz", current_combo=5, mode="multiple_choice")  # 模擬答錯送出
    fb_wrong = evaluate_quiz_answer(submit_wrong)  # 取得答錯判定
    assert fb_wrong.is_correct is False, "錯誤答案判定應為 False"  # 驗證答錯旗標
    assert fb_wrong.updated_combo == 0, "答錯時 Combo 連擊計數應重置歸零"  # 驗證連擊歸零
    assert fb_wrong.earned_score == 0, "答錯時不得分"  # 驗證不得分
    print("[OK] 答錯重置連擊測試成功，回饋訊息與正確答案揭曉正常")  # 印出答錯回饋日誌
    req_spell = QuizGenerateRequest(mode="spelling", pool="all", count=3)  # 建立拼寫題生成請求
    quiz_spell = generate_quiz_session(req_spell)  # 生成拼寫題目
    q_spell = quiz_spell[0]  # 取得拼寫第一題
    submit_spell = QuizAnswerSubmit(word_id=q_spell.word_id, user_answer=q_spell.target_romaji, current_combo=0, mode="spelling")  # 送出羅馬拼音答案
    fb_spell = evaluate_quiz_answer(submit_spell)  # 評估拼寫作答
    assert fb_spell.is_correct is True, "輸入目標羅馬拼音應判定為答對"  # 驗證拼寫正確性
    print(f"[OK] 拼寫/打字挑戰測試成功：單字「{q_spell.target_word}」羅馬音比對無誤")  # 印出拼寫通過日誌
    import time  # 導入 time 模組以產生不重複時間戳記確保測試冪等性
    test_uid = f"test_user_novice_{int(time.time()*1000)}"  # 定義動態唯一測試使用者 UID
    user = get_or_create_user(test_uid, "novice@example.com", "修真試煉者")  # 測試建立初始使用者帳號
    assert user["user_level"] == "新手小白", "新建立帳號等級應為新手小白"  # 驗證新手境界
    assert user["kana_completed"] is False, "初始五十音完成狀態應為 False"  # 驗證五十音初始狀態
    print(f"[OK] 使用者建立測試成功：{user['display_name']}，階級：{user['user_level']}")  # 印出帳號建立日誌
    ten_hobbies = ["動漫", "J-Pop音樂", "日本美食", "關東關西旅遊", "日劇影視", "電玩遊戲", "商業金融", "體育運動", "科技前沿", "歷史文化"]  # 定義 10 項擴充興趣標籤清單
    pref_res = update_user_preferences(test_uid, ten_hobbies, True, False)  # 測試更新使用者 10 項偏好標籤與字幕開關
    assert len(pref_res["hobbies"]) == 10, "興趣標籤應擴充支援至 10 項"  # 驗證標籤擴充上限至 10 項
    assert pref_res["default_sub_ja"] is True, "日文字幕偏好應為 True"  # 驗證日文字幕設定
    assert pref_res["default_sub_zh"] is False, "中文字幕偏好應為 False"  # 驗證中文字幕設定
    print("[OK] 使用者自選 10 項興趣標籤與雙語字幕偏好更新測試成功！")  # 印出偏好更新日誌
    mark_res = mark_kana_completed(test_uid)  # 測試標記完成五十音
    assert mark_res["kana_completed"] is True, "完成五十音後標記應為 True"  # 驗證五十音標記
    print("[OK] 五十音研讀模組完成標記成功！")  # 印出五十音完成日誌
    fb_g1 = record_beginner_game_score(test_uid, game_id=1, accuracy=90.0, score=900)  # 提交試煉第一關成績（90%）
    assert fb_g1["game1_acc"] == 90.0, "第一關最高分應為 90.0"  # 驗證第一關分數
    assert fb_g1["is_promoted"] is False, "尚未完成所有關卡時不應觸發晉級"  # 驗證未晉升
    fb_g2 = record_beginner_game_score(test_uid, game_id=2, accuracy=85.0, score=850)  # 提交試煉第二關成績（85%）
    assert fb_g2["is_promoted"] is False, "尚未完成第三關時不應觸發晉級"  # 驗證未晉升
    fb_g3 = record_beginner_game_score(test_uid, game_id=3, accuracy=95.0, score=950)  # 提交試煉第三關成績（95%）
    assert fb_g3["is_promoted"] is True, "五十音研讀完成且三關皆達 80% 時應成功自動晉升"  # 驗證觸發自動晉升
    assert fb_g3["new_level"] == "外門弟子", "最新階級應為外門弟子"  # 驗證晉升為外門弟子
    print(f"[OK] 自動晉升外門弟子測試成功：{fb_g3['message']}")  # 印出晉升成功日誌
    badges_list = get_user_badges(test_uid)  # 測試取得使用者成就徽章館清單
    assert len(badges_list) == 8, "全站成就徽章應包含 8 枚"  # 驗證徽章總數
    unlocked_badges = [b for b in badges_list if b["unlocked"]]  # 篩選已解鎖徽章
    assert len(unlocked_badges) >= 1, "晉升外門弟子後應至少已解鎖外門新秀徽章"  # 驗證解鎖境界徽章
    print(f"[OK] 徽章收藏館測試成功：共 8 枚徽章，已解鎖 {len(unlocked_badges)} 枚！")  # 印出徽章館測試日誌
    pq_n5 = get_placement_questions("外門弟子")  # 取得外門弟子挑戰考卷
    assert len(pq_n5) == 4, "外門弟子定級考卷應包含 4 道 N5 試題"  # 驗證定級試題數量
    pq_inner = get_placement_questions("內門弟子")  # 取得內門弟子挑戰考卷
    assert len(pq_inner) == 4, "內門弟子定級考卷應包含 4 道 N4/N3 試題"  # 驗證內門試題數量
    pq_elder = get_placement_questions("長老")  # 取得長老挑戰考卷
    assert len(pq_elder) == 4, "長老定級考卷應包含 4 道 N2/N1 試題"  # 驗證長老試題數量
    print("[OK] 動態能力定級測試出題測試成功：各境界均為 4 題自適應題庫！")  # 印出定級題庫日誌
    place_user_1 = f"place_uid_novice_{int(time.time()*1000)}"  # 定義測試新手小白定級使用者
    res_novice = evaluate_placement_test(place_user_1, "新手小白", {})  # 測試新手小白免試直通
    assert res_novice["assigned_tier"] == "新手小白", "新手小白免試應直通新手小白"  # 驗證免試境界
    assert res_novice["passed"] is True, "新手小白免試判定應為 True"  # 驗證通過
    print(f"[OK] 新手小白免試定級成功：{res_novice['message']}")  # 印出免試日誌
    place_user_2 = f"place_uid_outer_{int(time.time()*1000)}"  # 定義測試外門弟子通過定級使用者
    outer_answers = {str(q["id"]): q["correct_answer"] for q in pq_n5}  # 組裝 4 題全對作答字典
    res_outer = evaluate_placement_test(place_user_2, "外門弟子", outer_answers)  # 提交外門全對作答
    assert res_outer["assigned_tier"] == "外門弟子", "全對時應直接晉級為外門弟子"  # 驗證定級境界
    assert res_outer["score"] == 100.0, "全對得分應為 100.0%"  # 驗證滿分
    assert res_outer["unlocked_badge"] is not None, "通過定級應獲得境界徽章"  # 驗證獲得徽章
    print(f"[OK] 外門弟子定級合格測試成功：得分 {res_outer['score']}%，獲得徽章：{res_outer['unlocked_badge']}")  # 印出通過日誌
    place_user_3 = f"place_uid_fallback_{int(time.time()*1000)}"  # 定義測試智慧降階保護機制使用者
    half_answers = {  # 組裝 2 題正確與 2 題錯誤之作答對照字典（得分率 50%）
        str(pq_inner[0]["id"]): pq_inner[0]["correct_answer"],  # 第一題答對
        str(pq_inner[1]["id"]): pq_inner[1]["correct_answer"],  # 第二題答對
        str(pq_inner[2]["id"]): "wrong_choice_xyz",  # 第三題答錯
        str(pq_inner[3]["id"]): "wrong_choice_abc"  # 第四題答錯
    }  # 結束半數作答字典組裝
    res_fallback = evaluate_placement_test(place_user_3, "內門弟子", half_answers)  # 提交內門挑戰
    assert res_fallback["score"] == 50.0, "半數答對得分應為 50.0%"  # 驗證得分率
    assert res_fallback["assigned_tier"] == "外門弟子", "智慧降階保護應指派為外門弟子"  # 驗證降階保護結果
    print(f"[OK] 智慧降階保護機制測試成功：{res_fallback['message']}")  # 印出智慧降階成功日誌
    tele_res = record_behavior_telemetry(test_uid, category="動漫", action_type="view_media", duration_seconds=45.0)  # 測試寫入行為遙測數據
    assert tele_res["status"] == "ok", "行為遙測記錄狀態應為 ok"  # 驗證遙測成功
    assert "動漫" in tele_res["weights"], "遙測權重中應包含動漫分類加權"  # 驗證分類權重
    print(f"[OK] 行為遙測追蹤與動態權重微調測試成功：最新加權數值 {tele_res['weights']['動漫']}")  # 印出遙測日誌
    eval_res = evaluate_and_update_user_tier_and_badges(test_uid)  # 測試觸發全自動階級與徽章評估引擎
    assert "new_level" in eval_res, "評估結果應包含最新階級"  # 驗證最新階級欄位
    assert "badges" in eval_res, "評估結果應包含徽章清單"  # 驗證徽章清單欄位
    print(f"[OK] 全自動階級與徽章審核引擎測試成功：當前修為【{eval_res['new_level']}】！")  # 印出審核引擎日誌
    media_items = get_all_media()  # 測試取得官方影音列表
    assert len(media_items) >= 2, "影音清單應至少包含 2 部種子影片"  # 驗證影片數量
    m1 = media_items[0]  # 取得第一部影片
    assert len(m1["subtitles"]) > 0, "影片應具備雙語字幕切片資料"  # 驗證字幕資料結構
    print(f"[OK] 官方合法影音庫讀取成功：影片「{m1['title']}」含 {len(m1['subtitles'])} 行字幕")  # 印出影音讀取日誌
    fb_media = record_media_feedback(m1["id"], "interested")  # 測試評價反饋
    assert fb_media["likes_count"] > 0, "喜歡計數應累加"  # 驗證喜歡計數更新
    print(f"[OK] 影音推薦偏好評價成功：累計 {fb_media['likes_count']} 人感興趣")  # 印出評價日誌
    fb_saved = save_feedback("測試使用者", "tester@antigravity.jp", "功能建議", "系統非常好用，希望能增加更多歌曲！")  # 測試直接反饋儲存
    assert fb_saved["status"] == "sent", "反饋狀態應為 sent"  # 驗證反饋送出狀態
    assert fb_saved["target_email"] == "ytpre.new1@gmail.com", "反饋目標信箱應強制為 ytpre.new1@gmail.com"  # 驗證信箱地址
    print(f"[OK] 意見反饋路由測試成功：直達 {fb_saved['target_email']}")  # 印出反饋成功日誌
    stats = get_study_statistics()  # 讀取整體學習統計
    assert stats["total_words"] >= 20, "統計中單字總數應正確"  # 驗證總單字數
    print(f"[OK] 學習統計彙整成功：已掌握 {stats['mastered_count']} / 需練習 {stats['need_practice_count']} / 困難 {stats['hard_count']}")  # 印出統計分佈日誌
    print("====== 所有後端業務邏輯與試煉關卡測試全部圓滿通過！======")  # 印出全數通過訊息
# ---------------------------------------------------------------------------------------------------------------------- # 執行單元測試進入點
if __name__ == "__main__":  # 判斷是否為直接執行測試腳本
    run_all_tests()  # 呼叫執行測試主函式
