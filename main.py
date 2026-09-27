import os  # 導入作業系統標準函式庫以解析目錄與前端靜態資源路徑
import uvicorn  # 導入非同步 ASGI 伺服器 Uvicorn 用於本機伺服器啟動與監聽
from contextlib import asynccontextmanager  # 從 contextlib 模組導入非同步上下文管理工具以定義伺服器生命週期函式
from typing import List, Optional, Dict, Any  # 從 typing 模組導入 List、Optional、Dict 與 Any 以進行型別標註
from fastapi import FastAPI, HTTPException, Query, Body, status  # 從 fastapi 框架導入核心應用程式、例外處理、查詢與主體參數及狀態碼
from fastapi.middleware.cors import CORSMiddleware  # 從 fastapi 跨來源中介軟體模組導入 CORSMiddleware 解決瀏覽器跨域限制
from fastapi.staticfiles import StaticFiles  # 從 fastapi 靜態檔案模組導入 StaticFiles 以掛載 CSS 與 JS 檔案
from fastapi.responses import FileResponse, JSONResponse  # 從 fastapi 回應模組導入 FileResponse 傳送網頁檔案與 JSONResponse
from models import (  # 從 models 模組匯入資料模型定義以確保資料格式校驗
    UserProfile,  # 匯入使用者個人檔案模型
    UserLoginRequest,  # 匯入使用者登入驗證請求模型
    UserPreferencesUpdate,  # 匯入興趣標籤與字幕切換偏好更新模型
    BadgeItem,  # 匯入徽章展示項目模型
    PlacementQuestion,  # 匯入分級測驗題目模型
    PlacementTestSubmit,  # 匯入分級測驗作答送出模型
    PlacementTestResult,  # 匯入分級測驗結算結果模型
    BehaviorTelemetrySubmit,  # 匯入動態行為偏好追蹤遙測模型
    BeginnerGameSubmit,  # 匯入新手試煉小遊戲成績提交模型
    BeginnerPromotionFeedback,  # 匯入新手自動晉升判定回饋模型
    VideoMediaItem,  # 匯入官方合法影音項目模型
    MediaInterestFeedback,  # 匯入影音推薦興趣反饋模型
    DirectFeedbackForm,  # 匯入直接意見反饋表單模型
    WordCreate,  # 匯入新增單字請求模型類別
    WordResponse,  # 匯入單字詳情回傳模型類別
    SRSUpdateRequest,  # 匯入 SRS 狀態更新請求模型類別
    QuizGenerateRequest,  # 匯入測驗產生請求模型類別
    QuizQuestion,  # 匯入單一測驗題目模型類別
    QuizAnswerSubmit,  # 匯入測驗答案送出模型類別
    QuizAnswerFeedback,  # 匯入測驗即時判定回饋模型類別
    StudyStats,  # 匯入整體學習統計資料模型類別
    StreakCalendarResponse  # 匯入連續打卡日曆統計模型類別
)  # 結束 models 模組匯入宣告
from database import (  # 從 database 模組匯入資料庫核心操作函式
    init_db,  # 匯入資料庫表格與種子資料初始化函式
    get_or_create_user,  # 匯入使用者 Google 帳號讀取與自動建立函式
    update_user_preferences,  # 匯入使用者興趣與字幕偏好更新函式
    get_user_badges,  # 匯入查詢使用者徽章館資料函式
    get_placement_questions,  # 匯入取得能力分級考卷題目函式
    evaluate_placement_test,  # 匯入結算分級測驗與智慧降階函式
    record_behavior_telemetry,  # 匯入紀錄動態行為偏好加權函式
    evaluate_and_update_user_tier_and_badges,  # 匯入自動階級與徽章升級評估函式
    mark_kana_completed,  # 匯入標記五十音完成函式
    record_beginner_game_score,  # 匯入記錄新手試煉成績並自動晉級函式
    get_all_media,  # 匯入取得官方影音與字幕清單函式
    record_media_feedback,  # 匯入記錄影音感興趣反饋函式
    save_feedback,  # 匯入儲存意見反饋至官方信箱函式
    get_all_words,  # 匯入查詢全部單字函式
    get_word_by_id,  # 匯入單筆單字主鍵查詢函式
    create_word,  # 匯入新增單字寫入函式
    update_word_srs,  # 匯入更新單字掌握度函式（內含高密度記憶曲線 SRS 間隔排程）
    delete_word,  # 匯入刪除單字函式
    get_study_statistics,  # 匯入計算學習進度統計函式
    get_streak_calendar_data  # 匯入連續打卡日曆統計函式
)  # 結束 database 模組匯入宣告
from quiz_service import (  # 從 quiz_service 模組匯入測驗出題與計分服務函式
    generate_quiz_session,  # 匯入題目生成主服務函式
    evaluate_quiz_answer  # 匯入作答判定與連擊計算服務函式
)  # 結束 quiz_service 模組匯入宣告

# ---------------------------------------------------------------------------------------------------------------------- # 現代非同步生命週期管理器宣告
@asynccontextmanager  # 宣告非同步生命週期管理裝飾器
async def lifespan(app: FastAPI):  # 定義 FastAPI 現代非同步生命週期管理器
    init_db()  # 伺服器啟動時自動檢查資料庫結構並初始化種子單字、影音與打卡資料
    yield  # 將控制權移交給運行中的應用程式直到服務關閉

# ---------------------------------------------------------------------------------------------------------------------- # 建立 FastAPI 核心應用程式實例
app = FastAPI(  # 初始化 FastAPI 應用程式主物件
    title="日語智慧學習助手 API 3.1",  # 設定 API 說明文件主標題
    description="提供 100% 免費無廣告合法日語學習平台，支援高密度記憶曲線 SRS、防快取、能力分級定級與意見反饋",  # 系統詳細功能描述
    version="3.1.0",  # 設定本專案釋出版本號為 3.1.0
    lifespan=lifespan  # 掛載現代非同步生命週期管理器確保啟動時資料庫正常就緒
)  # 結束 FastAPI 應用程式初始化

# ---------------------------------------------------------------------------------------------------------------------- # 設定 CORS 跨來源資源共用中介軟體
app.add_middleware(  # 為 FastAPI 實例加入中介軟體設定
    CORSMiddleware,  # 指定套用跨來源資源共用中介軟體 CORSMiddleware
    allow_origins=["*"],  # 允許所有來源網址進行連線存取以利前端介面整合
    allow_credentials=True,  # 允許跨來源請求攜帶 Cookie 憑據與身分認證資訊
    allow_methods=["*"],  # 允許所有 HTTP 請求方法（GET, POST, PATCH, DELETE 等）
    allow_headers=["*"]  # 允許客戶端在請求標頭中傳入所有自訂欄位
)  # 結束中介軟體配置

# ---------------------------------------------------------------------------------------------------------------------- # 解析靜態資源目錄路徑並配置掛載
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 取得當前檔案所在的絕對路徑目錄
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")  # 計算前端靜態資源目錄 frontend 之絕對路徑
if not os.path.exists(FRONTEND_DIR):  # 檢查前端資料夾若尚不存在
    os.makedirs(FRONTEND_DIR, exist_ok=True)  # 自動建立 frontend 資料夾以避免掛載失敗報錯
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")  # 將 frontend 目錄掛載至 /static 路由提供樣式與腳本載入

# ---------------------------------------------------------------------------------------------------------------------- # 前端首頁進入點路由（附加防快取標頭）
@app.get("/", summary="提供前端首頁 HTML 網頁介面")  # 註冊首頁根目錄 GET 請求端點
def serve_index() -> FileResponse:  # 定義首頁回應處理函式
    index_path = os.path.join(FRONTEND_DIR, "index.html")  # 計算前端首頁 index.html 之檔案路徑
    if os.path.exists(index_path):  # 檢查首頁檔案是否存在於本機磁碟中
        headers = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}  # 建立首頁防快取標頭字典
        return FileResponse(index_path, headers=headers)  # 若存在則回傳完整的 HTML 網頁檔案給瀏覽器渲染
    return JSONResponse(content={"message": "日語學習系統後端服務運行中，前端首頁建置中。"})  # 若尚未建立首頁則回傳友善提示 JSON

# ---------------------------------------------------------------------------------------------------------------------- # PWA 漸進式網頁應用服務：Manifest 資訊清單端點
@app.get("/manifest.json", summary="提供 PWA 應用安裝設定資訊清單")  # 註冊 Manifest 資訊清單路由
def serve_manifest() -> FileResponse:  # 定義傳送 manifest 檔案函式
    manifest_path = os.path.join(FRONTEND_DIR, "manifest.json")  # 計算 manifest 檔案路徑
    if os.path.exists(manifest_path):  # 檢查檔案是否存在
        headers = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}  # 建立防快取標頭
        return FileResponse(manifest_path, media_type="application/manifest+json", headers=headers)  # 設定正確的 MIME 格式回傳
    raise HTTPException(status_code=404, detail="找不到 manifest.json 檔案")  # 若無檔案拋出 404

# ---------------------------------------------------------------------------------------------------------------------- # PWA 漸進式網頁應用服務：Service Worker 快取守護腳本端點
@app.get("/sw.js", summary="提供 PWA 離線快取守護腳本 Service Worker")  # 註冊 Service Worker 路由
def serve_sw() -> FileResponse:  # 定義傳送 sw 檔案函式
    sw_path = os.path.join(FRONTEND_DIR, "sw.js")  # 計算 sw.js 檔案路徑
    if os.path.exists(sw_path):  # 檢查檔案是否存在
        headers = {"Service-Worker-Allowed": "/", "Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}  # 附帶根權限與防快取標頭
        return FileResponse(sw_path, media_type="application/javascript", headers=headers)  # 附帶根權限標頭回傳
    raise HTTPException(status_code=404, detail="找不到 sw.js 檔案")  # 若無檔案拋出 404

# ---------------------------------------------------------------------------------------------------------------------- # 使用者驗證端點：Google Sign-In 帳號登入與個人檔案取得
@app.post("/api/user/login", response_model=UserProfile, summary="Google 登入驗證並同步個人帳號檔案與五重階級")  # 註冊 Google 登入端點
def api_user_login(login_req: UserLoginRequest) -> UserProfile:  # 定義 Google 登入處理函式
    user_data = get_or_create_user(  # 呼叫資料庫取得或自動建立使用者檔案
        uid=login_req.uid,  # 傳入使用者 Google UID
        email=login_req.email,  # 傳入電子郵件地址
        display_name=login_req.display_name,  # 傳入個人暱稱
        photo_url=login_req.photo_url  # 傳入大頭照網址
    )  # 取得使用者字典
    return UserProfile(**user_data)  # 封裝為標準 UserProfile 模型實例回傳

# ---------------------------------------------------------------------------------------------------------------------- # 使用者個人檔案查詢端點
@app.get("/api/user/profile", response_model=UserProfile, summary="依 UID 取得使用者個人檔案與境界等級")  # 註冊查詢個人檔案端點
def api_get_user_profile(uid: str = Query(..., description="使用者 Google UID")) -> UserProfile:  # 定義查詢個人檔案函式
    user_data = get_or_create_user(uid=uid, email="")  # 讀取使用者資料
    return UserProfile(**user_data)  # 封裝為標準 UserProfile 模型實例回傳

# ---------------------------------------------------------------------------------------------------------------------- # 使用者個人興趣標籤與雙語字幕偏好更新端點
@app.patch("/api/user/preferences", response_model=UserProfile, summary="更新使用者興趣標籤（最多10個）與雙語字幕記憶偏好")  # 註冊更新偏好端點
def api_update_preferences(pref_in: UserPreferencesUpdate, uid: str = Query(..., description="使用者 Google UID")) -> UserProfile:  # 定義更新偏好函式
    updated_user = update_user_preferences(  # 呼叫資料庫更新偏好函式
        uid=uid,  # 使用者唯一代碼
        hobbies=pref_in.hobbies,  # 興趣標籤陣列
        default_sub_ja=pref_in.default_sub_ja,  # 日文字幕偏好值
        default_sub_zh=pref_in.default_sub_zh  # 中文字幕偏好值
    )  # 取得更新後的使用者資料
    return UserProfile(**updated_user)  # 封裝為標準模型回傳

# ---------------------------------------------------------------------------------------------------------------------- # 徽章收藏館查詢端點
@app.get("/api/badges", response_model=List[BadgeItem], summary="查詢全體成就與境界徽章清單及當前解鎖狀態")  # 註冊徽章查詢端點
def api_get_badges(uid: str = Query(..., description="使用者 Google UID")) -> List[BadgeItem]:  # 定義查詢徽章函式
    badge_list = get_user_badges(uid=uid)  # 呼叫資料庫查詢所有徽章與解鎖狀態
    return [BadgeItem(**b) for b in badge_list]  # 轉換為標準 BadgeItem 清單回傳

# ---------------------------------------------------------------------------------------------------------------------- # 動態能力分級測驗：考卷題目取得端點
@app.get("/api/onboarding/placement-questions", response_model=List[PlacementQuestion], summary="依目標階級取得 4 道分級考卷測驗題目")  # 註冊考卷題目端點
def api_get_placement_questions(target_tier: str = Query(..., description="目標挑戰階級：外門弟子 / 內門弟子 / 長老")) -> List[PlacementQuestion]:  # 定義考卷題目函式
    questions = get_placement_questions(target_tier=target_tier)  # 呼叫資料庫讀取該境界之題目
    return [PlacementQuestion(**q) for q in questions]  # 轉換為考卷模型陣列回傳

# ---------------------------------------------------------------------------------------------------------------------- # 動態能力分級測驗：結算與智慧降階端點
@app.post("/api/onboarding/placement-submit", response_model=PlacementTestResult, summary="提交能力分級測驗作答並執行結算與智慧降階")  # 註冊結算分級測驗端點
def api_submit_placement_test(submit_in: PlacementTestSubmit, uid: Optional[str] = Query(default=None, description="使用者 Google UID")) -> PlacementTestResult:  # 定義結算函式
    try:  # 包覆例外保護區塊防止非預期伺服器崩潰
        target_uid = uid or submit_in.uid  # 優先從 Query 取用，其次容錯由 JSON Body 提取 UID
        if not target_uid:  # 若兩者皆未提供 UID
            raise HTTPException(status_code=400, detail="缺少使用者唯一識別碼 (UID)")  # 拋出 400 錯誤提示
        if submit_in.hobbies:  # 若提交資料中包含自選興趣偏好清單
            update_user_preferences(uid=target_uid, hobbies=submit_in.hobbies)  # 同步更新使用者興趣標籤
        result = evaluate_placement_test(uid=target_uid, target_tier=submit_in.target_tier, answers=submit_in.answers)  # 呼叫分級判定引擎
        return PlacementTestResult(**result)  # 封裝為標準結果模型回傳
    except HTTPException:  # 攔截標準 HTTP 例外
        raise  # 重新拋出維持原始狀態碼
    except Exception as e:  # 攔截其餘非預期計算異常
        raise HTTPException(status_code=500, detail=f"定級測驗結算處理失敗：{str(e)}")  # 回傳詳細 500 錯誤訊息

# ---------------------------------------------------------------------------------------------------------------------- # 動態行為偏好遙測追蹤回報端點
@app.post("/api/user/behavior", summary="回報使用者互動時長與點擊行為以動態校準推薦演算法權重")  # 註冊行為遙測端點
def api_record_behavior(telemetry_in: Dict[str, Any] = Body(default_factory=dict), uid: Optional[str] = Query(default=None, description="使用者 Google UID")) -> dict:  # 定義行為紀錄函式
    try:
        target_uid = uid or telemetry_in.get("uid")
        if not target_uid:
            return {"status": "skipped", "message": "未提供 UID，略過遙測紀錄"}
        category = str(telemetry_in.get("category") or telemetry_in.get("dwell_category") or "綜合")
        action_type = str(telemetry_in.get("action_type") or "view_media")
        duration = float(telemetry_in.get("duration_seconds") or telemetry_in.get("dwell_seconds") or 0.0)
        res = record_behavior_telemetry(uid=target_uid, category=category, action_type=action_type, duration_seconds=duration)
        return res
    except Exception as e:
        return {"status": "error", "message": f"遙測處理異常：{str(e)}"}

# ---------------------------------------------------------------------------------------------------------------------- # 全自動階級與成就徽章晉階評估端點
@app.post("/api/user/evaluate-tier", summary="依據單字掌握度、複習次數與打卡紀錄自動升級境界與頒發徽章")  # 註冊自動晉升端點
def api_evaluate_tier(uid: str = Query(..., description="使用者 Google UID")) -> dict:  # 定義自動晉升函式
    res = evaluate_and_update_user_tier_and_badges(uid=uid)  # 呼叫全盤階級升級評估引擎
    return res  # 回傳評估結果

# ---------------------------------------------------------------------------------------------------------------------- # 新手小白五十音學習模組研讀完成端點
@app.post("/api/beginner/kana-complete", response_model=UserProfile, summary="標記使用者已研讀完成五十音基礎學習模組")  # 註冊五十音完成端點
def api_kana_complete(uid: str = Query(..., description="使用者 Google UID")) -> UserProfile:  # 定義五十音完成處理函式
    user_data = mark_kana_completed(uid=uid)  # 標記五十音完成並檢驗是否觸發自動晉級
    return UserProfile(**user_data)  # 回傳最新個人檔案模型實例

# ---------------------------------------------------------------------------------------------------------------------- # 新手試煉小遊戲成績提交與自動晉升審核端點
@app.post("/api/beginner/game-submit", response_model=BeginnerPromotionFeedback, summary="提交新手試煉關卡成績並審核是否晉升外門弟子")  # 註冊試煉成績提交端點
def api_beginner_game_submit(game_in: BeginnerGameSubmit, uid: str = Query(..., description="使用者 Google UID")) -> BeginnerPromotionFeedback:  # 定義試煉提交處理函式
    feedback = record_beginner_game_score(
        uid=uid,
        game_id=game_in.game_id,
        accuracy=game_in.accuracy,
        score=game_in.score
    )
    return BeginnerPromotionFeedback(**feedback)

# ---------------------------------------------------------------------------------------------------------------------- # 官方合法嵌入影音與雙語時間軸字幕列表查詢端點
@app.get("/api/media", response_model=List[VideoMediaItem], summary="取得官方合法嵌入影音與雙語互動字典字幕清單")  # 註冊影音庫查詢端點
def api_get_media(category: Optional[str] = Query(None, description="影音分類過濾"), uid: Optional[str] = Query(None, description="使用者 UID")) -> List[VideoMediaItem]:  # 定義影音清單查詢函式
    media_list = get_all_media(category=category, uid=uid)
    return [VideoMediaItem(**m) for m in media_list]

# ---------------------------------------------------------------------------------------------------------------------- # 使用者對影音之感興趣/不感興趣偏好反饋端點
@app.post("/api/media/{media_id}/feedback", summary="記錄使用者對特定影片之評價")  # 註冊影音評價反饋端點
def api_media_feedback(media_id: str, fb_in: MediaInterestFeedback) -> dict:
    res = record_media_feedback(media_id=media_id, action=fb_in.action)
    return res

# ---------------------------------------------------------------------------------------------------------------------- # 使用者直接意見反饋端點 (直達 ytpre.new1@gmail.com)
@app.post("/api/feedback", summary="提交使用者寶貴意見反饋，系統直接路由至官方信箱 ytpre.new1@gmail.com")  # 註冊意見反饋端點
def api_direct_feedback(fb_in: DirectFeedbackForm) -> dict:
    res = save_feedback(
        user_name=fb_in.user_name,
        user_email=fb_in.user_email,
        category=fb_in.category,
        message=fb_in.message,
        target_email=fb_in.target_email
    )
    return res

# ---------------------------------------------------------------------------------------------------------------------- # 單字查詢列表端點（支援 SRS 狀態與搜尋過濾）
@app.get("/api/words", response_model=List[WordResponse], summary="查詢個人雲端單字本列表")
def api_get_words(
    srs_status: Optional[str] = Query(None, description="掌握度篩選條件：all / mastered / need_practice / hard"),
    search: Optional[str] = Query(None, description="關鍵字模糊搜尋字串")
) -> List[WordResponse]:
    return get_all_words(srs_status=srs_status, search=search)

# ---------------------------------------------------------------------------------------------------------------------- # 單一單字詳情查詢端點
@app.get("/api/words/{word_id}", response_model=WordResponse, summary="依 ID 查詢單一單字完整資料")
def api_get_word(word_id: int) -> WordResponse:
    word = get_word_by_id(word_id)
    if not word:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到指定的單字")
    return word

# ---------------------------------------------------------------------------------------------------------------------- # 新增單字至雲端單字本端點
@app.post("/api/words", response_model=WordResponse, status_code=status.HTTP_201_CREATED, summary="新增自訂單字至個人雲端生詞本")
def api_create_word(word_in: WordCreate) -> WordResponse:
    word_dict = word_in.model_dump() if hasattr(word_in, "model_dump") else word_in.dict()
    new_word = create_word(word_dict)
    return new_word

# ---------------------------------------------------------------------------------------------------------------------- # 更新單字 SRS 掌握度標記端點（高密度記憶曲線排程）
@app.patch("/api/words/{word_id}/srs", response_model=WordResponse, summary="更新單字的 SRS 高密度記憶曲線掌握度等級")
def api_update_srs(word_id: int, srs_in: SRSUpdateRequest) -> WordResponse:
    valid_statuses = ["mastered", "need_practice", "hard"]
    if srs_in.srs_status not in valid_statuses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="無效的 SRS 狀態值")
    updated_word = update_word_srs(word_id, srs_in.srs_status)
    if not updated_word:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="找不到欲更新的單字")
    return updated_word

# ---------------------------------------------------------------------------------------------------------------------- # 刪除雲端單字端點
@app.delete("/api/words/{word_id}", summary="從個人雲端單字本中刪除指定單字")
def api_delete_word(word_id: int) -> dict:
    success = delete_word(word_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="欲刪除的單字不存在")
    return {"message": "單字已成功從雲端單字本移除", "word_id": word_id}

# ---------------------------------------------------------------------------------------------------------------------- # 單字小測驗遊戲：題目動態生成端點
@app.post("/api/quiz/generate", response_model=List[QuizQuestion], summary="生成單字小測驗題庫")
def api_generate_quiz(quiz_req: QuizGenerateRequest) -> List[QuizQuestion]:
    questions = generate_quiz_session(quiz_req)
    if not questions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="單字本中無足夠詞彙以生成測驗")
    return questions

# ---------------------------------------------------------------------------------------------------------------------- # 單字小測驗遊戲：使用者答案即時送出與計分端點
@app.post("/api/quiz/submit", response_model=QuizAnswerFeedback, summary="提交測驗作答並即時取得判定與 Combo 獎勵")
def api_submit_answer(answer_in: QuizAnswerSubmit) -> QuizAnswerFeedback:
    feedback = evaluate_quiz_answer(answer_in)
    return feedback

# ---------------------------------------------------------------------------------------------------------------------- # 學習者總體進度統計端點
@app.get("/api/stats", response_model=StudyStats, summary="取得雲端單字掌握度分佈與測驗準確率整體統計")
def api_get_stats() -> StudyStats:
    return get_study_statistics()

# ---------------------------------------------------------------------------------------------------------------------- # 學習連續打卡天數與月份日曆查詢端點
@app.get("/api/streak", response_model=StreakCalendarResponse, summary="取得連續學習打卡天數與月份日曆格子數據")
def api_get_streak(year: Optional[int] = Query(None), month: Optional[int] = Query(None)) -> StreakCalendarResponse:
    data = get_streak_calendar_data(target_year=year, target_month=month)
    return StreakCalendarResponse(**data)

# ---------------------------------------------------------------------------------------------------------------------- # 本機直接啟動應用程式服務進入點
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)