from typing import List, Optional, Dict, Any, Literal, Union  # 從 typing 模組導入常用型別標註工具以維持資料結構之型別安全性
from pydantic import BaseModel, Field  # 從 pydantic 模組導入 BaseModel（基礎資料模型）與 Field（欄位驗證約束工具）
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義五大境界等級枚舉型別
UserLevelType = Literal["新手小白", "外門弟子", "內門弟子", "長老", "訪客"]  # 定義修真階級系統之五種身分等級字面常數
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義使用者個人資料與身分偏好模型
class UserProfile(BaseModel):  # 定義使用者帳號完整個人檔案模型 UserProfile
    uid: str = Field(..., description="Firebase Google 帳號唯一識別代碼 UID")  # 使用者唯一帳號識別代碼
    email: str = Field(..., description="使用者 Google 綁定之電子郵件地址")  # 電子信箱地址
    display_name: str = Field(default="日語學習者", description="使用者自訂或 Google 同步之顯示暱稱")  # 暱稱姓名
    photo_url: str = Field(default="", description="使用者 Google 帳號大頭照圖像 URL 連結")  # 個人頭像網址
    user_level: UserLevelType = Field(default="新手小白", description="當前等級：新手小白 / 外門弟子 / 內門弟子 / 長老 / 訪客")  # 修真階級
    hobbies: List[str] = Field(default_factory=list, description="使用者個人興趣標籤列表（上限 10 個，例如動漫、音樂、美食、科技）")  # 興趣標籤
    default_sub_ja: bool = Field(default=True, description="影片預設日文字幕開關偏好設定（預設為開啟 True）")  # 日文字幕偏好
    default_sub_zh: bool = Field(default=True, description="影片預設中文字幕開關偏好設定（預設為開啟 True）")  # 中文字幕偏好
    kana_completed: bool = Field(default=False, description="是否已完成基礎五十音圖解學習模組")  # 五十音完成旗標
    game1_acc: float = Field(default=0.0, description="新手試煉第一關：假名翻牌記憶配對之最高答對正確率 (0.0 ~ 100.0%)")  # 遊戲一正確率
    game2_acc: float = Field(default=0.0, description="新手試煉第二關：假名聽音辨字挑戰之最高答對正確率 (0.0 ~ 100.0%)")  # 遊戲二正確率
    game3_acc: float = Field(default=0.0, description="新手試煉第三關：羅馬拼音極速打字之最高答對正確率 (0.0 ~ 100.0%)")  # 遊戲三正確率
    onboarding_completed: bool = Field(default=False, description="是否已完成沈浸式引導與動態能力分級定級")  # 開箱定級旗標
    badges: List[str] = Field(default_factory=list, description="已解鎖之榮耀成就與境界徽章識別碼清單")  # 已解鎖徽章清單
    behavior_weights: Dict[str, float] = Field(default_factory=dict, description="使用者動態行為偏好加權分佈字典")  # 行為加權字典
    total_study_seconds: int = Field(default=0, description="使用者累計學習互動總秒數")  # 累計學習總秒數
    created_at: str = Field(default="", description="帳號首次透過 Google 註冊建立之時間戳記字串")  # 帳號建立時間
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義 Google 登入驗證請求模型
class UserLoginRequest(BaseModel):  # 定義 Google 登入驗證請求模型 UserLoginRequest
    uid: str = Field(..., description="Firebase Google 帳號唯一識別代碼 UID")  # 使用者唯一 UID 識別代碼
    email: str = Field(default="user@example.com", description="使用者 Google 帳號電子郵件地址")  # 使用者電子信箱
    display_name: str = Field(default="日語學習者", description="使用者 Google 帳號暱稱")  # 使用者顯示暱稱
    photo_url: str = Field(default="", description="使用者 Google 帳號頭像圖像網址")  # 使用者個人頭像網址
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義使用者興趣偏好設定更新請求模型（支援最多 10 項標籤）
class UserPreferencesUpdate(BaseModel):  # 定義偏好更新請求模型 UserPreferencesUpdate
    hobbies: List[str] = Field(default_factory=list, max_items=10, description="自選興趣標籤列表，強制最多選取 10 項")  # 興趣標籤限制最多 10 個
    default_sub_ja: bool = Field(default=True, description="記憶使用者日文字幕手動切換開關狀態")  # 日文字幕設定值
    default_sub_zh: bool = Field(default=True, description="記憶使用者中文字幕手動切換開關狀態")  # 中文字幕設定值
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義成就徽章項目模型
class BadgeItem(BaseModel):  # 定義徽章收藏館展示項目模型 BadgeItem
    id: str = Field(..., description="徽章唯一英文識別碼 ID")  # 徽章代碼
    name: str = Field(..., description="徽章正體中文尊榮名稱")  # 徽章名稱
    tier: str = Field(..., description="徽章分類：境界徽章 / 里程碑成就")  # 徽章分類
    icon: str = Field(..., description="徽章圖示或 Emoji 代表符號")  # 徽章圖示
    description: str = Field(..., description="徽章達成條件與修煉意境描述")  # 解鎖條件描述
    unlocked: bool = Field(default=False, description="當前使用者是否已成功解鎖該徽章")  # 解鎖狀態旗標
    unlocked_at: Optional[str] = Field(default=None, description="解鎖之年月日時分秒字串")  # 解鎖時間戳記
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義動態能力測試分級題目模型
class PlacementQuestion(BaseModel):  # 定義分級測試題目模型 PlacementQuestion
    id: int = Field(..., description="題目唯一識別編號 ID")  # 題目主鍵
    target_tier: UserLevelType = Field(..., description="本題目所屬的目標門檻階級")  # 對應境界
    prompt: str = Field(..., description="測驗題目題目幹文字或日語文法語句")  # 題目內容
    options: List[str] = Field(..., description="四選一作答選項列表")  # 作答選項
    correct_answer: str = Field(..., description="標準正確答案文字")  # 正確解答
    explanation: str = Field(default="", description="答案考點與辭意詳解")  # 題目解析說明
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義能力分級測驗送出作答模型
class PlacementTestSubmit(BaseModel):  # 定義分級測驗作答送出模型 PlacementTestSubmit
    uid: Optional[str] = Field(default=None, description="使用者唯一識別代碼 UID（選填，亦可自路徑參數提取）")  # 使用者唯一帳號識別代碼
    target_tier: UserLevelType = Field(..., description="使用者自選挑戰之目標修真境界")  # 自選目標階級
    hobbies: Optional[List[str]] = Field(default=None, description="使用者自選之興趣標籤陣列（最多 10 個）")  # 興趣標籤陣列
    answers: Union[Dict[str, str], List[Dict[str, Any]]] = Field(default_factory=dict, description="作答對照字典或作答物件清單")  # 作答對照
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義能力分級測驗結算與智慧降階回饋模型
class PlacementTestResult(BaseModel):  # 定義分級測驗結算回饋模型 PlacementTestResult
    target_tier: UserLevelType = Field(..., description="挑戰之原始目標修真境界")  # 挑戰目標
    score: float = Field(..., description="本次分級測驗實得分數百分比 (0.0 ~ 100.0%)")  # 測驗得分
    assigned_tier: UserLevelType = Field(..., description="系統根據實力判定或智慧降階後最終授予之修真境界")  # 定級階級
    passed: bool = Field(..., description="是否完全通過目標境界門檻")  # 是否過關
    fallback_triggered: bool = Field(default=False, description="是否觸發智慧降階保護機制")  # 智慧降階旗標
    message: str = Field(..., description="定級結果說明與鼓勵性評語")  # 評定說明語
    unlocked_badge: Optional[str] = Field(default=None, description="本次定級順帶解鎖之境界徽章名稱")  # 解鎖徽章
    badges_awarded: List[str] = Field(default_factory=list, description="本次定級解鎖之所有徽章名稱清單")  # 解鎖徽章清單陣列
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義使用者動態行為偏好遙測回報模型
class BehaviorTelemetrySubmit(BaseModel):  # 定義使用者動態行為追蹤回報模型 BehaviorTelemetrySubmit
    category: str = Field(..., description="互動之興趣領域分類（例如動漫、J-Pop、美食、科技）")  # 興趣主題類別
    action_type: str = Field(..., description="互動行為類型：view_media / hover_word / review_card / quiz_action")  # 行為動作類型
    duration_seconds: float = Field(default=0.0, ge=0.0, description="停頓駐留或研讀互動之秒數")  # 互動時長秒數
    word: Optional[str] = Field(default=None, description="觸發互動之特定日文詞彙（選填）")  # 關聯單字
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義新手小白試煉迷你小遊戲成績送出模型
class BeginnerGameSubmit(BaseModel):  # 定義新手試煉關卡成績提交模型 BeginnerGameSubmit
    game_id: int = Field(..., ge=1, le=3, description="試煉遊戲關卡編號：1（翻牌配對）、2（聽音辨字）、3（拼寫打字）")  # 遊戲編號約束 1 至 3
    accuracy: float = Field(..., ge=0.0, le=100.0, description="本輪遊戲作答正確率百分比 (0.0 ~ 100.0)")  # 本輪正確率百分比數值
    score: int = Field(default=0, ge=0, description="本輪遊戲實得分數")  # 遊戲得分數值
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義新手晉級外門弟子判定回饋模型
class BeginnerPromotionFeedback(BaseModel):  # 定義試煉晉級回饋模型 BeginnerPromotionFeedback
    game_id: int = Field(..., description="剛完成之試煉關卡編號")  # 完成的關卡編號
    current_acc: float = Field(..., description="本次關卡結算之正確率百分比")  # 本次正確率
    game1_acc: float = Field(..., description="第一關假名翻牌最佳正確率")  # 第一關歷史最佳
    game2_acc: float = Field(..., description="第二關聽音辨字最佳正確率")  # 第二關歷史最佳
    game3_acc: float = Field(..., description="第三關拼寫打字最佳正確率")  # 第三關歷史最佳
    overall_avg_acc: float = Field(..., description="三關試煉之平均最佳正確率百分比")  # 三關綜合平均正確率
    kana_completed: bool = Field(..., description="是否已研讀完成五十音學習模組")  # 五十音學習狀態
    is_promoted: bool = Field(..., description="是否滿足條件並成功自動晉級為『外門弟子』")  # 晉級判定布林值結果
    new_level: UserLevelType = Field(..., description="結算後的最新修真身分等級")  # 使用者最新修真階級
    message: str = Field(..., description="系統判定激勵訊息或晉級賀詞")  # 系統互動回饋語句
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義影片單字辭典懸浮提示結構模型
class VideoWordDetail(BaseModel):  # 定義影片內嵌單字詞典模型 VideoWordDetail
    word: str = Field(..., description="單字表面形日文漢字或假名表記")  # 單字漢字
    reading: str = Field(..., description="平假名或片假名發音標記")  # 假名讀音
    romaji: str = Field(..., description="英文字母羅馬拼音讀音")  # 羅馬拼音
    meaning: str = Field(..., description="繁體中文精準辭義說明")  # 中文解釋
    example_ja: str = Field(default="", description="單字情境實用日文例句")  # 實用日文例句
    example_zh: str = Field(default="", description="日文例句繁體中文翻譯")  # 例句中文翻譯
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義雙語時間軸字幕資料條目模型
class VideoSubtitleLine(BaseModel):  # 定義時間軸雙語字幕模型 VideoSubtitleLine
    start_time: float = Field(..., description="字幕開始時間秒數（例如 12.5 秒）")  # 起始秒數
    end_time: float = Field(..., description="字幕結束時間秒數（例如 16.8 秒）")  # 結束秒數
    text_ja: str = Field(..., description="日文完整句子原文")  # 日文字幕本體
    text_zh: str = Field(..., description="對應之繁體中文語意翻譯")  # 中文字幕翻譯
    words: List[VideoWordDetail] = Field(default_factory=list, description="該句中所有可供懸浮查閱與一鍵收藏的單字字典清單")  # 單字列表
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義官方合法內嵌多媒體影音項目模型
class VideoMediaItem(BaseModel):  # 定義合法影音項目模型 VideoMediaItem
    id: str = Field(..., description="影音唯一識別編號 ID")  # 唯一影音 ID
    title: str = Field(..., description="影音正版官方名稱標題")  # 影音名稱
    category: str = Field(..., description="主題分類標籤（例如動漫經典 Anime、J-Pop 熱門歌曲、文化觀光）")  # 領域類別
    youtube_id: str = Field(..., description="YouTube 官方合法 oEmbed/Iframe 影片代碼")  # YouTube 唯一視訊識別碼
    description: str = Field(default="", description="影片背景故事與日語重點簡介")  # 影片簡述
    subtitles: List[VideoSubtitleLine] = Field(default_factory=list, description="該影片時間軸切片雙語互動字幕列表")  # 時間軸字幕清單
    likes_count: int = Field(default=0, description="使用者標記『👍 感興趣 (Interested)』的累計總次數")  # 感興趣計數
    dislikes_count: int = Field(default=0, description="使用者標記『👎 不感興趣 (Not Interested)』的累計總次數")  # 不感興趣計數
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義影音感興趣回饋請求模型
class MediaInterestFeedback(BaseModel):  # 定義影音推薦偏好回饋模型 MediaInterestFeedback
    media_id: str = Field(..., description="被評價的目標多媒體影音 ID")  # 影片 ID
    action: Literal["interested", "not_interested"] = Field(..., description="回饋動作：interested（喜歡）或 not_interested（不感興趣）")  # 回饋型態
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義直接寄送意見回饋表單模型
class DirectFeedbackForm(BaseModel):  # 定義意見反饋送出模型 DirectFeedbackForm
    user_name: str = Field(..., description="提出反饋之使用者姓名或代稱")  # 反饋者姓名
    user_email: str = Field(..., description="提出反饋之使用者聯絡電子郵件信箱")  # 聯絡郵箱
    category: str = Field(default="功能建議", description="反饋分類：功能建議 / 程式錯誤 / 學習疑問 / 其他")  # 反饋類別
    message: str = Field(..., min_length=5, description="詳細意見回饋文字描述內容（至少 5 個字元）")  # 反饋內容本文
    target_email: str = Field(default="ytpre.new1@gmail.com", description="強制指派之官方接收電子信箱")  # 目標郵箱地址
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義單字基礎資料模型
class WordBase(BaseModel):  # 定義單字基礎模型類別 WordBase，供新增與更新共用核心欄位
    word: str = Field(..., description="日文單字漢字或主要書寫表記，例如：勉強")  # 日文單字主體，為必填字串欄位
    reading: str = Field(..., description="平假名或片假名讀音表記，例如：べんきょう")  # 單字假名發音標註，為必填字串欄位
    romaji: str = Field(..., description="羅馬拼音讀音，方便拼寫輸入比對，例如：benkyou")  # 羅馬拼音表示法，為必填字串欄位
    meaning: str = Field(..., description="繁體中文釋義說明，例如：學習、讀書")  # 中文翻譯解釋，為必填字串欄位
    example_ja: str = Field(default="", description="日文情境實用例句")  # 日文例句字串，預設為空字串
    example_zh: str = Field(default="", description="日文例句對應的繁體中文翻譯")  # 例句中文翻譯字串，預設為空字串
    level: str = Field(default="N5", description="日語檢定分級標籤，例如：N5、N4、N3 等")  # 單字難度等級標記，預設為 N5
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義單字建立請求模型
class WordCreate(WordBase):  # 定義新增單字請求模型 WordCreate，繼承基礎單字模型
    pass  # 保留基礎模型的所有欄位設定，無需額外擴充欄位即可進行新增操作
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義單字完整資料回傳模型
class WordResponse(WordBase):  # 定義單字完整回傳資料模型 WordResponse，包含後端資料庫的元數據
    id: int = Field(..., description="資料庫唯一主鍵編號 ID")  # 單字在雲端資料庫中的唯一識別整數代碼
    srs_status: str = Field(default="need_practice", description="SRS間隔重複複習狀態：mastered / need_practice / hard")  # 複習掌握度評級
    review_count: int = Field(default=0, description="總累計複習測驗次數")  # 使用者複習該單字的總次數統計
    correct_count: int = Field(default=0, description="答對總次數統計")  # 使用者在測驗中正確回答該單字的次數累計
    created_at: str = Field(default="", description="單字加入雲端單字本的建立時間字串")  # 記錄加入生詞本的年月日時分秒資訊
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義 SRS 掌握度更新請求模型
class SRSUpdateRequest(BaseModel):  # 定義 SRS 狀態更新請求模型 SRSUpdateRequest
    srs_status: str = Field(..., description="目標掌握度狀態：'mastered'（已掌握）、'need_practice'（需練習）、'hard'（困難）")  # 新的掌握度標籤
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義測驗生成請求模型
class QuizGenerateRequest(BaseModel):  # 定義測驗題目生成請求模型 QuizGenerateRequest
    mode: str = Field(default="multiple_choice", description="測驗模式：multiple_choice（四選一）、spelling（拼寫打字）、mixed（混合）")  # 遊戲模式選擇
    pool: str = Field(default="all", description="單字池來源：all（全部雲端單字）、hard（標記困難）、need_practice（需練習）、mastered（已掌握）")  # 出題篩選範圍
    count: int = Field(default=10, ge=1, le=50, description="本輪測驗題目數量，限制範圍為 1 至 50 題")  # 指定單次測驗的題目總數量
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義四選一選項結構模型
class QuizOption(BaseModel):  # 定義測驗四選一選項模型 QuizOption
    option_id: int = Field(..., description="選項所對應的單字識別 ID")  # 選項內部繫結的資料庫單字編號
    text: str = Field(..., description="選項按鈕顯示文字，通常為日文漢字或假名讀音")  # 渲染在使用者介面按鈕上的文字內容
    sub_text: Optional[str] = Field(default=None, description="選項輔助讀音或假名提示文字")  # 選項下方微小字體的輔助讀音提示
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義單一測驗題目結構模型
class QuizQuestion(BaseModel):  # 定義單一題目結構模型 QuizQuestion
    question_index: int = Field(..., description="題目在本次測驗中的順序索引序號（從 1 開始）")  # 當前題目編號
    word_id: int = Field(..., description="正確答案對應之雲端單字庫 ID")  # 目標單字資料庫唯一編號
    mode: str = Field(..., description="該題題型：'multiple_choice'（四選一）或 'spelling'（拼寫挑戰）")  # 本題目的遊戲機制類型
    prompt: str = Field(..., description="題目主要提示提示詞，通常為中文釋義或聽音指示")  # 測驗畫面呈現給使用者的提問主旨
    target_word: str = Field(..., description="目標日文單字（供前端音訊播放或拼寫比對參考）")  # 正確單字表面形（漢字）
    target_reading: str = Field(..., description="目標平假名讀音（供拼寫比對或提示）")  # 正確單字平假名發音
    target_romaji: str = Field(..., description="目標羅馬拼音讀音（供拼寫輸入比對容錯）")  # 正確單字英文字母羅馬音
    options: Optional[List[QuizOption]] = Field(default=None, description="四選一模式之 4 個隨機選項列表")  # 選擇題模式專用選項陣列
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義測驗作答送出模型
class QuizAnswerSubmit(BaseModel):  # 定義前端提交使用者答案模型 QuizAnswerSubmit
    word_id: int = Field(..., description="作答的單字唯一識別碼 ID")  # 作答對應的資料庫單字代碼
    user_answer: str = Field(..., description="使用者輸入或點選的答案字串（日文/假名/羅馬音或選項ID）")  # 使用者所提供的答案內容
    current_combo: int = Field(default=0, ge=0, description="使用者送出答案前當前已連續答對的連擊次數 Combo")  # 連續答對次數計數
    mode: str = Field(default="multiple_choice", description="作答所屬模式：'multiple_choice' 或 'spelling'")  # 當前題目的測驗型態
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義測驗即時回饋模型
class QuizAnswerFeedback(BaseModel):  # 定義後端即時驗證回饋模型 QuizAnswerFeedback
    is_correct: bool = Field(..., description="作答是否正確判定結果（True 為正確，False 為錯誤）")  # 答題正誤布林旗標
    correct_word: str = Field(..., description="標準日文單字漢字")  # 正確單字日文漢字表記
    correct_reading: str = Field(..., description="標準日文平假名發音")  # 正確單字假名表記
    correct_romaji: str = Field(..., description="標準羅馬拼音讀音")  # 正確單字羅馬拼音表記
    correct_meaning: str = Field(..., description="標準中文繁體釋義說明")  # 正確單字中文解釋
    updated_combo: int = Field(..., description="結算後的最新連續答對連擊數（答對加一，答錯歸零）")  # 最新 Combo 數值
    earned_score: int = Field(..., description="本題獲得之基礎分數與 Combo 加權獎勵分總和")  # 本題獲得的分數計算結果
    feedback_message: str = Field(..., description="友善的激勵性或提示性回饋訊息文字")  # 介面顯示之互動提示評語
    recommended_srs: str = Field(..., description="系統根據作答結果建議之 SRS 複習狀態標記")  # 建議調整的間隔重複掌握度標籤
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義學習統計資訊模型
class StudyStats(BaseModel):  # 定義學習者雲端整體統計資料模型 StudyStats
    total_words: int = Field(..., description="雲端單字庫中的總單字收藏數量")  # 總收錄單字數
    mastered_count: int = Field(..., description="已標記為『已掌握 (Mastered)』的精通單字數量")  # 精通單字數量計數
    need_practice_count: int = Field(..., description="標記為『需練習 (Need Practice)』的學習中單字數量")  # 練習中單字數量計數
    hard_count: int = Field(..., description="標記為『困難 (Hard)』的高優先級生詞數量")  # 困難生詞數量計數
    total_reviews: int = Field(..., description="所有單字在系統中累計執行的總複習次數")  # 累計複習作答總次數
    total_correct: int = Field(..., description="所有複習中累計答對的總次數")  # 累計答對總次數
    overall_accuracy: float = Field(..., description="全體單字複習的平均答對正確率百分比 (0.0 ~ 100.0%)")  # 綜合準確率百分比數值
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義打卡日曆單日資訊模型
class StreakDayInfo(BaseModel):  # 定義打卡日曆單一日期格子資料結構 StreakDayInfo
    day: int = Field(..., description="該日期所對應的月份日期號碼（1 ~ 31）")  # 幾月幾號的號碼
    date_str: str = Field(..., description="標準年月日格式字串，例如：2026-09-26")  # 完整的 ISO 日期格式字串
    is_active: bool = Field(..., description="該日是否已完成學習打卡活動")  # 當日是否有複習或測驗記錄
    words_count: int = Field(default=0, description="當天累計複習單字總數量")  # 當日複習的單字總數量
    quizzes_count: int = Field(default=0, description="當天累計完成測驗次數")  # 當日參與的測驗總回數
    is_today: bool = Field(default=False, description="該日期是否為今天")  # 是否標記為今天焦點
# ---------------------------------------------------------------------------------------------------------------------- # 模組分隔線：定義學習連續打卡日曆回應模型
class StreakCalendarResponse(BaseModel):  # 定義連續打卡統計與月份日曆回應模型 StreakCalendarResponse
    current_streak: int = Field(..., description="當前持續連續學習天數（Streak）")  # 當前連續登入/學習天數計數
    longest_streak: int = Field(..., description="歷史累計最長連續學習天數紀錄")  # 歷史最長紀錄天數
    total_active_days: int = Field(..., description="累計有學習紀錄的歷史總天數")  # 歷史累計學習總天數
    today_studied: bool = Field(..., description="今天是否已經完成學習打卡")  # 今日打卡完成布林狀態
    current_year: int = Field(..., description="當前檢視日曆的西元年份")  # 日曆所屬年份數值
    current_month: int = Field(..., description="當前檢視日曆的月份數值（1 ~ 12）")  # 日曆所屬月份數值
    month_days: List[StreakDayInfo] = Field(..., description="當前月份的所有日期打卡狀態陣列")  # 當月全部天數狀態清單
