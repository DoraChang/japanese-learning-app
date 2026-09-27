import random  # 導入亂數產生模組以實現隨機抽題與選項洗牌打亂
import unicodedata  # 導入 Unicode 正規化模組以處理日文假名全形半形比對
from typing import List, Dict, Any, Tuple  # 導入型別提示工具以定義嚴格的輸入與回傳型態
from database import get_all_words, get_word_by_id, get_random_distractors, update_word_srs  # 從資料庫模組導入操作函式
from models import QuizGenerateRequest, QuizQuestion, QuizOption, QuizAnswerSubmit, QuizAnswerFeedback  # 導入資料模型類別
# ---------------------------------------------------------------------------------------------------------------------- # 單字文字正規化輔助函式（去除空格、轉小寫、Unicode NFKC 正規化）
def normalize_text(text: str) -> str:  # 定義字串正規化處理函式
    if not text:  # 檢查輸入文字是否為空或 None
        return ""  # 若為空則直接回傳空字串
    cleaned = text.strip().lower()  # 去除首尾空白字元並轉為小寫字母以利不分大小寫比對
    return unicodedata.normalize("NFKC", cleaned)  # 套用 Unicode NFKC 標準化轉換全形半形字元
# ---------------------------------------------------------------------------------------------------------------------- # 測驗題目集動態生成服務函式
def generate_quiz_session(request: QuizGenerateRequest) -> List[QuizQuestion]:  # 宣告測驗出題邏輯主函式
    pool_filter = request.pool if request.pool in ["hard", "need_practice", "mastered"] else None  # 判定單字庫篩選條件
    words = get_all_words(srs_status=pool_filter)  # 依掌握度篩選自雲端單字本讀取題目候選單字
    if len(words) < 4:  # 判斷若篩選出的單字數量不足以構成多選題干擾項（少於 4 個）
        words = get_all_words()  # 自動回退為從全體單字庫中選取，以確保測驗順利進行
    if not words:  # 若單字庫為完全空白無任何單字
        return []  # 回傳空陣列通知前端無題目
    quiz_count = min(request.count, len(words))  # 計算本次測驗實際出題數量（取請求數與庫存數最小值）
    selected_words = random.sample(words, quiz_count)  # 從單字陣列中不重複隨機抽取目標單字
    questions: List[QuizQuestion] = []  # 初始化測驗題目結果列表
    for idx, target in enumerate(selected_words, start=1):  # 依序走訪被抽中的各個目標單字
        current_mode = request.mode  # 取得使用者請求的遊戲模式
        if current_mode == "mixed":  # 若為混合挑戰模式
            current_mode = random.choice(["multiple_choice", "spelling"])  # 隨機指派為四選一或拼寫題型
        if current_mode == "multiple_choice":  # 處理四選一選擇題型邏輯
            distractor_words = get_random_distractors(target["id"], limit=3)  # 從資料庫隨機抽取 3 個相異的干擾單字
            options_pool = [target] + distractor_words  # 將 1 個正確解答與 3 個干擾選項合併為 4 項候選池
            random.shuffle(options_pool)  # 隨機打亂 4 個選項在畫面上的排列順序避免位置固定
            options: List[QuizOption] = []  # 初始化該題選項物件清單
            for opt in options_pool:  # 逐一封裝各個選項資料
                options.append(QuizOption(  # 將選項資訊加入選項陣列
                    option_id=opt["id"],  # 設定選項對應之單字庫唯一 ID
                    text=opt["word"],  # 設定按鈕主視覺文字為日文漢字或表記
                    sub_text=opt["reading"]  # 設定輔助提示假名讀音
                ))  # 結束單一選項物件包裝
            questions.append(QuizQuestion(  # 封裝四選一題目物件
                question_index=idx,  # 設定題目流水序號
                word_id=target["id"],  # 設定目標解答單字 ID
                mode="multiple_choice",  # 設定題目型態為四選一
                prompt=f"請選出與「{target['meaning']}」相符的日文單字：",  # 設定題目提問提示語
                target_word=target["word"],  # 設定目標日文漢字
                target_reading=target["reading"],  # 設定目標平假名
                target_romaji=target["romaji"],  # 設定目標羅馬拼音
                options=options  # 傳入四個隨機排序後的選項列表
            ))  # 結束題目加入操作
        else:  # 處理拼寫/打字挑戰題型邏輯
            questions.append(QuizQuestion(  # 封裝拼寫挑戰題目物件
                question_index=idx,  # 設定題目流水序號
                word_id=target["id"],  # 設定目標解答單字 ID
                mode="spelling",  # 設定題目型態為拼寫打字
                prompt=f"請根據中文「{target['meaning']}」輸入其假名讀音或羅馬拼音：",  # 設定拼寫提問引導詞
                target_word=target["word"],  # 設定目標日文漢字
                target_reading=target["reading"],  # 設定目標平假名
                target_romaji=target["romaji"],  # 設定目標羅馬拼音
                options=None  # 拼寫模式不需要四選一選項清單
            ))  # 結束拼寫題目加入操作
    return questions  # 回傳本次測驗生成的題目清單
# ---------------------------------------------------------------------------------------------------------------------- # 使用者作答即時判定、Combo 連擊計分與 SRS 狀態回饋函式
def evaluate_quiz_answer(submit: QuizAnswerSubmit) -> QuizAnswerFeedback:  # 宣告作答判定服務函式
    word = get_word_by_id(submit.word_id)  # 自資料庫讀取該題目標單字詳細資訊
    if not word:  # 檢查該單字是否存在於資料庫中
        return QuizAnswerFeedback(  # 若找不到單字則回傳預設失敗回饋
            is_correct=False,  # 標記為錯誤
            correct_word="未知",  # 填入佔位單字
            correct_reading="",  # 填入空假名
            correct_romaji="",  # 填入空羅馬音
            correct_meaning="單字不存在",  # 填入錯誤訊息
            updated_combo=0,  # 連擊數重置為 0
            earned_score=0,  # 獲得分數為 0
            feedback_message="系統找不到該單字資訊",  # 顯示錯誤提醒
            recommended_srs="hard"  # 建議標記為困難
        )  # 結束例外回饋包裝
    user_ans = normalize_text(submit.user_answer)  # 對使用者輸入之答案實施正規化清理
    is_correct = False  # 初始化答對狀態布林旗標為 False
    if submit.mode == "multiple_choice":  # 判斷是否為四選一選擇題型作答
        is_correct = (user_ans == str(word["id"])) or (user_ans == normalize_text(word["word"])) or (user_ans == normalize_text(word["reading"]))  # 支援選項ID比對或字面漢字/假名比對
    else:  # 判斷為拼寫/打字挑戰作答
        target_reading_norm = normalize_text(word["reading"])  # 正規化目標平假名讀音
        target_romaji_norm = normalize_text(word["romaji"])  # 正規化目標羅馬拼音
        target_word_norm = normalize_text(word["word"])  # 正規化目標日文漢字表記
        is_correct = (user_ans == target_reading_norm) or (user_ans == target_romaji_norm) or (user_ans == target_word_norm)  # 寬容支援平假名、羅馬拼音及漢字直接比對
    base_score = 100  # 定義單題基礎滿分基準為 100 分
    if is_correct:  # 判斷若作答完全正確
        updated_combo = submit.current_combo + 1  # 連續答對次數 Combo 累加 1
        combo_multiplier = min(3.0, 1.0 + (submit.current_combo * 0.15))  # 計算連擊分數加成倍率（最高可累積達 3.0 倍）
        earned_score = int(base_score * combo_multiplier)  # 結合連擊倍率計算本題實得總分
        if updated_combo >= 5:  # 當連擊數達到 5 次以上時
            feedback_msg = f"🔥 勢不可擋！{updated_combo} 連擊超神速！(+{earned_score} 分)"  # 產生超高連擊狂熱回饋詞
        elif updated_combo >= 3:  # 當連擊數達到 3 次以上時
            feedback_msg = f"⚡ 手感火熱！達成 {updated_combo} 連擊！(+{earned_score} 分)"  # 產生中高連擊鼓勵回饋詞
        else:  # 連擊 1 至 2 次基礎答對
            feedback_msg = f"✨ 答對了！太厲害了！(+{earned_score} 分)"  # 產生基礎正確讚賞回饋詞
        recommended_srs = "mastered" if updated_combo >= 2 else "need_practice"  # 根據連擊信心度建議評定為已掌握或需練習
    else:  # 判斷若作答錯誤
        updated_combo = 0  # 答錯時連續連擊計數器立即重置歸零
        earned_score = 0  # 本題獲得分數為 0 分
        feedback_msg = f"💡 再接再厲！正確答案是「{word['word']}」({word['reading']})"  # 產生溫馨解答提醒訊息
        recommended_srs = "hard"  # 答錯之單字自動推薦調整為困難以強化複習頻率
    update_word_srs(word["id"], recommended_srs, is_correct=is_correct)  # 即時同步將作答結果寫入雲端單字庫資料表
    return QuizAnswerFeedback(  # 封裝即時測驗回饋資料物件並回傳給前端
        is_correct=is_correct,  # 回傳正誤布林結果
        correct_word=word["word"],  # 回傳標準單字日文表記
        correct_reading=word["reading"],  # 回傳標準平假名發音
        correct_romaji=word["romaji"],  # 回傳標準羅馬拼音
        correct_meaning=word["meaning"],  # 回傳標準中文釋義
        updated_combo=updated_combo,  # 回傳結算後的最新連擊數
        earned_score=earned_score,  # 回傳本題獲得分數
        feedback_message=feedback_msg,  # 回傳互動評語字串
        recommended_srs=recommended_srs  # 回傳建議 SRS 等級
    )  # 結束回饋物件建立並回傳
