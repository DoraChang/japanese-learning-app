import os  # 導入作業系統標準函式庫以進行檔案路徑運算與檢查
import json  # 導入 json 模組以序列化與反序列化興趣標籤、徽章與雙語字幕陣列
import sqlite3  # 導入輕量級關聯式資料庫模組 SQLite3
import calendar  # 導入日曆標準函式庫以計算各月份總天數與星期排列
from datetime import datetime, timedelta  # 從 datetime 模組導入日期時間處理類別與時間差工具
from typing import List, Dict, Any, Optional, Union  # 從 typing 模組導入型別標註工具以維持程式碼嚴謹度
# ---------------------------------------------------------------------------------------------------------------------- # 資料庫配置設定區塊
DB_PATH = os.path.join(os.path.dirname(__file__), "vocab.db")  # 計算並定義 SQLite 資料庫檔案 vocab.db 之絕對路徑
# ---------------------------------------------------------------------------------------------------------------------- # 全系統成就與境界徽章常數定義列表
ALL_BADGES = [  # 定義全系統 8 大榮耀徽章元資料字典清單
    {"id": "badge_novice", "name": "初入道途 · 假名破曉", "tier": "境界徽章", "icon": "🌱", "description": "開啟日語修真大門，立志向學之始"},  # 新手小白徽章
    {"id": "badge_outer", "name": "登堂入室 · 詞海泛舟", "tier": "境界徽章", "icon": "🥋", "description": "突破新手試煉或分級過關，晉升外門弟子"},  # 外門弟子徽章
    {"id": "badge_inner", "name": "心領神會 · 聽音明理", "tier": "境界徽章", "icon": "⚔️", "description": "修為精湛，晉升內門弟子，通曉高階雙語辭庫"},  # 內門弟子徽章
    {"id": "badge_elder", "name": "登峰造極 · 日語大宗師", "tier": "境界徽章", "icon": "👑", "description": "日語實力深不可測，晉升最高長老尊位"},  # 長老境界徽章
    {"id": "badge_combo_5", "name": "連擊王者 · 勢如破竹", "tier": "里程碑成就", "icon": "🔥", "description": "在單字小測驗中達成連續答對 5 題 (Combo x5)"},  # 連擊成就徽章
    {"id": "badge_streak_3", "name": "持之以恆 · 三日修行", "tier": "里程碑成就", "icon": "📅", "description": "連續學習打卡達 3 天以上"},  # 打卡成就徽章
    {"id": "badge_vocab_5", "name": "博聞強記 · 熟稔生詞", "tier": "里程碑成就", "icon": "📚", "description": "個人雲端單字本中標記已掌握單字達 5 個以上"},  # 生詞成就徽章
    {"id": "badge_media_lover", "name": "視聽合一 · 影音行者", "tier": "里程碑成就", "icon": "🎬", "description": "積極互動官方雙語影音字典並留下評價"}  # 影音成就徽章
]  # 徽章元資料定義結束
# ---------------------------------------------------------------------------------------------------------------------- # 資料庫連接輔助函式（設定 20 秒逾時等待以防止鎖表）
def get_db_connection() -> sqlite3.Connection:  # 定義建立資料庫連接的函式並標註回傳連線物件
    conn = sqlite3.connect(DB_PATH, timeout=20.0)  # 連接指定路徑的 SQLite 資料庫並設定 20 秒鎖定等待逾時
    conn.row_factory = sqlite3.Row  # 設定查詢結果資料列轉換為具備字典鍵值存取特性的 Row 格式
    return conn  # 回傳已完成配置的資料庫連線實例
# ---------------------------------------------------------------------------------------------------------------------- # 資料庫初始化與多表建構函式
def init_db() -> None:  # 定義全系統資料庫表格結構建立與初始種子資料填充函式
    conn = get_db_connection()  # 取得資料庫操作連線
    cursor = conn.cursor()  # 建立 SQL 語句執行游標
    cursor.execute("CREATE TABLE IF NOT EXISTS words (id INTEGER PRIMARY KEY AUTOINCREMENT, word TEXT NOT NULL, reading TEXT NOT NULL, romaji TEXT NOT NULL, meaning TEXT NOT NULL, example_ja TEXT DEFAULT '', example_zh TEXT DEFAULT '', level TEXT DEFAULT 'N5', srs_status TEXT DEFAULT 'need_practice', review_count INTEGER DEFAULT 0, correct_count INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")  # 建立單字資料表 words 存放雲端生詞
    cursor.execute("CREATE TABLE IF NOT EXISTS study_activity (id INTEGER PRIMARY KEY AUTOINCREMENT, activity_date TEXT NOT NULL UNIQUE, words_reviewed INTEGER DEFAULT 0, quizzes_taken INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")  # 建立每日學習打卡表記錄連續天數
    cursor.execute("CREATE TABLE IF NOT EXISTS users (uid TEXT PRIMARY KEY, email TEXT NOT NULL, display_name TEXT DEFAULT '日語學習者', photo_url TEXT DEFAULT '', user_level TEXT DEFAULT '新手小白', hobbies TEXT DEFAULT '[]', default_sub_ja INTEGER DEFAULT 1, default_sub_zh INTEGER DEFAULT 1, kana_completed INTEGER DEFAULT 0, game1_acc REAL DEFAULT 0.0, game2_acc REAL DEFAULT 0.0, game3_acc REAL DEFAULT 0.0, onboarding_completed INTEGER DEFAULT 0, badges TEXT DEFAULT '[\"badge_novice\"]', behavior_weights TEXT DEFAULT '{}', total_study_seconds INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")  # 建立使用者個人資料與修真五重境界表
    cursor.execute("CREATE TABLE IF NOT EXISTS media (id TEXT PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL, youtube_id TEXT NOT NULL, description TEXT DEFAULT '', subtitles_json TEXT NOT NULL, likes_count INTEGER DEFAULT 0, dislikes_count INTEGER DEFAULT 0)")  # 建立官方合法嵌入影音與雙語單字字幕庫
    cursor.execute("CREATE TABLE IF NOT EXISTS feedbacks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_name TEXT, user_email TEXT, category TEXT, message TEXT, target_email TEXT DEFAULT 'ytpre.new1@gmail.com', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")  # 建立專屬意見反饋表直接對接官方信箱
    cursor.execute("CREATE TABLE IF NOT EXISTS placement_questions (id INTEGER PRIMARY KEY AUTOINCREMENT, target_tier TEXT NOT NULL, prompt TEXT NOT NULL, options_json TEXT NOT NULL, correct_answer TEXT NOT NULL, explanation TEXT DEFAULT '')")  # 建立動態能力分級題目表
    conn.commit()  # 提交所有資料表的建構交易
    for col, dtype, def_val in [("onboarding_completed", "INTEGER", "0"), ("badges", "TEXT", "'[\"badge_novice\"]'"), ("behavior_weights", "TEXT", "'{}'"), ("total_study_seconds", "INTEGER", "0")]:  # 迭代走訪需無痛移轉之新欄位清單
        try:  # 嘗試透過 ALTER TABLE 動態追加欄位以相容舊版資料庫
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {dtype} DEFAULT {def_val}")  # 執行資料表擴充
            conn.commit()  # 提交擴充異動
        except sqlite3.OperationalError:  # 攔截欄位已存在之例外錯誤
            pass  # 若欄位已存在則優雅略過
    cursor.execute("SELECT COUNT(*) FROM words")  # 查詢資料表中既有之單字紀錄總筆數
    count_words = cursor.fetchone()[0]  # 取得單字查詢計數
    if count_words == 0:  # 判斷單字庫若為空則寫入種子詞彙
        seed_words = [  # 構建常用核心日語種子詞彙列表
            ("勉強", "べんきょう", "benkyou", "學習、讀書", "毎日日本語を楽しく勉強します。", "每天都快樂地學習日文。", "N5", "need_practice"),  # 勉強
            ("桜", "さくら", "sakura", "櫻花", "春になると綺麗な桜が満開になります。", "一到了春天美麗的櫻花就會盛開。", "N5", "mastered"),  # 桜
            ("食べる", "たべる", "taberu", "吃", "友達と一緒に美味しい朝ご飯を食べる。", "和朋友一起吃美味的早餐。", "N5", "mastered"),  # 食べる
            ("友達", "ともだち", "tomodachi", "朋友", "彼はずっと仲の良い大切な友達です。", "他一直是我感情很好且重要的朋友。", "N5", "mastered"),  # 友達
            ("猫", "ねこ", "neko", "貓咪", "公園の日向で可愛い猫が眠っています。", "一隻可愛的貓咪在公園向陽處睡覺。", "N5", "mastered"),  # 猫
            ("夢", "ゆめ", "yume", "夢想", "私の大きな夢は日本で働くことです。", "我的遠大夢想是在日本工作。", "N5", "need_practice"),  # 夢
            ("素晴らしい", "すばらしい", "subarashii", "極好的、絕妙的", "昨日の夜空と花火は本当に素晴らしかった。", "昨晚的夜空與煙火真的很棒。", "N4", "need_practice"),  # 素晴らしい
            ("約束", "やくそく", "yakusoku", "約定、承諾", "大切な友達と週末に会う約束をした。", "和重要的朋友約好了週末見面。", "N4", "hard"),  # 約束
            ("家族", "かぞく", "kazoku", "家人", "週末は家族と一緒に団らんを楽しみます。", "週末與家人一起享受天倫之樂。", "N5", "mastered"),  # 家族
            ("旅行", "りょこう", "ryokou", "旅行", "来年の春に京都へ旅行に行きたいです。", "希望明年春天能去京都旅行。", "N5", "need_practice"),  # 旅行
            ("美味しい", "おいしい", "oishii", "好吃的、美味的", "母が作った手料理はいつもとても美味しい。", "媽媽做的家常菜總是特別美味。", "N5", "mastered"),  # 美味しい
            ("希望", "きぼう", "kibou", "希望", "どんな困難な時でも未来への希望を失わない。", "無論何時都不失去對未來的希望。", "N3", "hard"),  # 希望
            ("本", "ほん", "hon", "書本", "休みの日は静かな図書館で本を読みます。", "休假時會在安靜的圖書館讀書。", "N5", "mastered"),  # 本
            ("雨", "あめ", "ame", "雨水、下雨", "朝から冷たい雨が静かに降り続いています。", "從早晨開始冰涼的雨水就靜靜地下著。", "N5", "need_practice"),  # 雨
            ("幸せ", "しあわせ", "shiawase", "幸福、快樂", "穏やかな日常を過ごせることが何よりの幸せです。", "能夠度過平靜的日常就是最大的幸福。", "N4", "need_practice"),  # 幸せ
            ("時間", "じかん", "jikan", "時間", "時間を大切にして夢を追いかけましょう。", "好好珍惜時間，一起追逐夢想吧。", "N5", "mastered"),  # 時間
            ("始める", "はじめる", "hajimeru", "開始", "今日から新しい挑戦を始めます。", "從今天開始展開全新的挑戰。", "N4", "hard"),  # 始める
            ("感謝", "かんしゃ", "kansha", "感謝、感激", "いつも支えてくれる人に深く感謝します。", "由衷感謝身邊一直支持我的人。", "N3", "hard"),  # 感謝
            ("電車", "でんしゃ", "densha", "電車", "毎朝電車に乗って通勤しています。", "每天早晨搭乘電車通勤。", "N5", "mastered"),  # 電車
            ("写真", "しゃしん", "shashin", "照片", "旅先で思い出の写真をたくさん撮りました。", "在旅途中拍了許多回憶的照片。", "N5", "need_practice"),  # 写真
        ]  # 種子單字陣列定義結尾
        cursor.executemany("INSERT INTO words (word, reading, romaji, meaning, example_ja, example_zh, level, srs_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", seed_words)  # 批次寫入種子詞彙
        conn.commit()  # 提交單字寫入
    cursor.execute("SELECT COUNT(*) FROM study_activity")  # 檢查打卡表記錄是否已有初始資料
    if cursor.fetchone()[0] == 0:  # 若打卡表為全新狀態則預先注入最近數天的初始打卡活動
        today_date = datetime.now().date()  # 取得當前本地系統日期物件
        sample_activities = []  # 初始化樣本活動清單
        for past_day in range(4, -1, -1):  # 走訪過去 4 天至今天共 5 天
            act_date_str = (today_date - timedelta(days=past_day)).strftime("%Y-%m-%d")  # 格式化日期字串
            words_cnt = 5 + (past_day * 2)  # 模擬複習生詞張數
            quiz_cnt = 1 if past_day % 2 == 0 else 2  # 模擬參與測驗回數
            sample_activities.append((act_date_str, words_cnt, quiz_cnt))  # 加入樣本資料元組
        cursor.executemany("INSERT OR IGNORE INTO study_activity (activity_date, words_reviewed, quizzes_taken) VALUES (?, ?, ?)", sample_activities)  # 批次注入打卡資料
        conn.commit()  # 提交寫入交易
    cursor.execute("SELECT COUNT(*) FROM media")  # 檢查官方多媒體影音庫是否已初始化
    if cursor.fetchone()[0] == 0:  # 若影音庫為空則注入官方合法嵌入影片種子資料
        sub1_data = [{"start_time": 0.0, "end_time": 5.2, "text_ja": "毎日の生活を心から楽しんでいます。", "text_zh": "我從心底享受著每一天的生活。", "words": [{"word": "毎日", "reading": "まいにち", "romaji": "mainichi", "meaning": "每天、日常", "example_ja": "毎日日本語を勉強します。", "example_zh": "每天都學習日文。"}, {"word": "生活", "reading": "せいかつ", "romaji": "seikatsu", "meaning": "生活、日子", "example_ja": "楽しい生活を送る。", "example_zh": "過著快樂的生活。"}, {"word": "楽しむ", "reading": "たのしむ", "romaji": "tanoshimu", "meaning": "享受、樂在其中", "example_ja": "音楽を楽しむ。", "example_zh": "享受音樂。"}]}, {"start_time": 5.3, "end_time": 10.8, "text_ja": "新しい友達と一緒に冒険を始めましょう！", "text_zh": "和新朋友一起展開冒險吧！", "words": [{"word": "新しい", "reading": "あたらしい", "romaji": "atarashii", "meaning": "新的、嶄新的", "example_ja": "新しい本を買いました。", "example_zh": "買了新書。"}, {"word": "友達", "reading": "ともだち", "romaji": "tomodachi", "meaning": "朋友、友人", "example_ja": "友達と映画を見る。", "example_zh": "和朋友看電影。"}, {"word": "冒険", "reading": "ぼうけん", "romaji": "bouken", "meaning": "冒險、挑戰", "example_ja": "大冒険に出発する。", "example_zh": "出發去大冒險。"}]}]  # 定義 SPYxFAMILY 雙語切片字幕清單
        sub2_data = [{"start_time": 0.0, "end_time": 6.5, "text_ja": "沈むように溶けてゆくように、夜の空へ。", "text_zh": "彷彿沉落般、彷彿融化般，奔向夜空。", "words": [{"word": "沈む", "reading": "しずむ", "romaji": "shizumu", "meaning": "沉沒、落下", "example_ja": "太陽が沈む。", "example_zh": "太陽西沉。"}, {"word": "溶ける", "reading": "tokeru", "romaji": "tokeru", "meaning": "融化、溶解", "example_ja": "氷が溶ける。", "example_zh": "冰塊融化。"}, {"word": "夜", "reading": "よる", "romaji": "yoru", "meaning": "夜晚、黑夜", "example_ja": "静かな夜。", "example_zh": "安靜的夜晚。"}, {"word": "空", "reading": "そら", "romaji": "sora", "meaning": "天空", "example_ja": "青い空を見上げる。", "example_zh": "仰望藍天。"}]}]  # 定義 YOASOBI 雙語切片字幕清單
        sample_media = [  # 建立官方合法 YouTube oEmbed 影片與雙語互動時間軸字幕清單
            ("anime_01", "SPY×FAMILY 間諜家家酒 - Official Theme Clip", "Anime", "fG5n4qK_8vM", "超人氣日劇動漫，跟隨安妮亞學習實用日常對話與豐富單字。", json.dumps(sub1_data, ensure_ascii=False), 12, 0),  # 種子影片 1：SPYxFAMILY
            ("jpop_01", "YOASOBI - 夜に駆ける (Official Music Video)", "J-Pop", "x8VYWazR5mE", "席捲全球的現象級日語神曲，歌詞蘊含優美的日語文學修辭。", json.dumps(sub2_data, ensure_ascii=False), 28, 1)  # 種子影片 2：YOASOBI
        ]  # 影音種子定義結束
        cursor.executemany("INSERT INTO media (id, title, category, youtube_id, description, subtitles_json, likes_count, dislikes_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", sample_media)  # 批次寫入影音庫
        conn.commit()  # 提交影音交易
    cursor.execute("SELECT COUNT(*) FROM placement_questions")  # 查詢分級題目庫數量
    if cursor.fetchone()[0] == 0:  # 若題庫為空則注入分級測試題庫
        seed_questions = [  # 構建動態分級題目種子陣列
            ("外門弟子", "請問問候語「こんにちは」對應哪一個中文意思？", json.dumps(["你好、日安", "再見", "早安", "晚安"], ensure_ascii=False), "你好、日安", "「こんにちは」是日語中最普遍的日間問候語。"),  # 外門弟子題 1
            ("外門弟子", "單字「勉強（べんきょう）」在日文中的主要含意是？", json.dumps(["學習、讀書", "強迫自己", "工作、就業", "運動休憩"], ensure_ascii=False), "學習、讀書", "「勉強」在日語代表用功讀書之意。"),  # 外門弟子題 2
            ("外門弟子", "請問日文第一人稱「私」的標準平假名讀音是？", json.dumps(["わたし", "あなた", "かれ", "これ"], ensure_ascii=False), "わたし", "「私」是日語第一人稱代名詞，發音為わたし。"),  # 外門弟子題 3
            ("外門弟子", "提示主題的助詞「は」作為文法助詞時應發音為？", json.dumps(["wa", "ha", "ga", "wo"], ensure_ascii=False), "wa", "提示主題時之假名「は」須讀作 wa。"),  # 外門弟子題 4
            ("內門弟子", "「週末は友達と映画を（　）に行きます。」空格應填入？", json.dumps(["見", "見て", "見る", "見ます"], ensure_ascii=False), "見", "動詞連用形（ます形去ます）+ に行く 表示移動之目的。"),  # 內門弟子題 1
            ("內門弟子", "「雨が（　）ので、傘を持っていきます。」空格應填入？", json.dumps(["降る", "降った", "降り", "降れば"], ensure_ascii=False), "降る", "客觀原因理由助詞「ので」前接動詞普通形。"),  # 內門弟子題 2
            ("內門弟子", "單字「約束（やくそく）」的繁體中文解釋是？", json.dumps(["約定、承諾", "節約束縛", "規則條文", "契約商談"], ensure_ascii=False), "約定、承諾", "「約束」代表朋友或彼此之間的約定。"),  # 內門弟子題 3
            ("內門弟子", "「先生から本を（　）。」表示從老師處得到贈書應填入？", json.dumps(["いただきました", "さしあげました", "くださる", "やりました"], ensure_ascii=False), "いただきました", "「いただく」為「もらう」的謙讓語表記。"),  # 內門弟子題 4
            ("長老", "「お名前を伺っても（　）でしょうか。」商務敬語尊稱詢問空格應填入？", json.dumps(["よろしい", "いい", "まいります", "おっしゃる"], ensure_ascii=False), "よろしい", "「伺ってもよろしいでしょうか」為極致禮貌之詢問語句。"),  # 長老題 1
            ("長老", "日語慣用句「顔が広い」的深刻引申義為？", json.dumps(["人脈廣闊、交友遍天下", "臉型寬大", "愛好面子", "面善心嚴"], ensure_ascii=False), "人脈廣闊、交友遍天下", "「顔が広い」形容認識的人極多，交遊圈極為廣闊。"),  # 長老題 2
            ("長老", "「結果がどうであれ、最善を尽くす（　）だ。」表示道義應當？", json.dumps(["べき", "はず", "わけ", "こと"], ensure_ascii=False), "べき", "動詞辭書形 + べきだ 表示依常理道義上應當如此作為。"),  # 長老題 3
            ("長老", "四字熟語「一期一會（いちごいちえ）」源自茶道，其哲學寓意為？", json.dumps(["珍惜一生僅有一次的珍貴相遇", "四季輪迴每天都是新生", "朋友應經常聚集暢談", "一年只有一次開花機會"], ensure_ascii=False), "珍惜一生僅有一次的珍貴相遇", "叮囑世人珍惜當下每一次萍水相逢的人事緣分。")  # 長老題 4
        ]  # 分級題目清單結尾
        cursor.executemany("INSERT INTO placement_questions (target_tier, prompt, options_json, correct_answer, explanation) VALUES (?, ?, ?, ?, ?)", seed_questions)  # 批次寫入分級題庫
        conn.commit()  # 提交分級題目交易
    conn.close()  # 關閉連線釋放資源
# ---------------------------------------------------------------------------------------------------------------------- # 使用者驗證與登入檔案取得/自動建檔函式（Firebase 整合）
def get_or_create_user(uid: str, email: str, display_name: str = "日語學習者", photo_url: str = "") -> Dict[str, Any]:  # 定義登入獲取帳號函式
    conn = get_db_connection()  # 取得資料庫連線
    cursor = conn.cursor()  # 建立操作游標
    cursor.execute("SELECT * FROM users WHERE uid = ?", (uid,))  # 依 UID 查詢帳號
    row = cursor.fetchone()  # 讀取查詢結果
    if not row:  # 若為首次透過 Google Sign-In 登入之全新使用者
        cursor.execute("INSERT INTO users (uid, email, display_name, photo_url, user_level, hobbies, default_sub_ja, default_sub_zh, kana_completed, onboarding_completed, badges, behavior_weights, total_study_seconds) VALUES (?, ?, ?, ?, '新手小白', '[]', 1, 1, 0, 0, '[\"badge_novice\"]', '{}', 0)", (uid, email, display_name, photo_url))  # 建立新手小白預設記錄
        conn.commit()  # 提交寫入
        cursor.execute("SELECT * FROM users WHERE uid = ?", (uid,))  # 重新查詢新建立之使用者資料
        row = cursor.fetchone()  # 讀取剛建立之資料列
    user_dict = dict(row)  # 轉換為原生字典
    conn.close()  # 關閉連線釋放資源
    user_dict["hobbies"] = json.loads(user_dict.get("hobbies") or "[]")  # 解析興趣標籤 JSON 字串為陣列
    user_dict["default_sub_ja"] = bool(user_dict.get("default_sub_ja", 1))  # 轉換日文字幕布林值
    user_dict["default_sub_zh"] = bool(user_dict.get("default_sub_zh", 1))  # 轉換中文字幕布林值
    user_dict["kana_completed"] = bool(user_dict.get("kana_completed", 0))  # 轉換五十音完成布林值
    user_dict["onboarding_completed"] = bool(user_dict.get("onboarding_completed", 0))  # 轉換定級完成布林值
    user_dict["badges"] = json.loads(user_dict.get("badges") or '["badge_novice"]')  # 解析已解鎖徽章清單
    user_dict["behavior_weights"] = json.loads(user_dict.get("behavior_weights") or "{}")  # 解析行為權重字典
    user_dict["total_study_seconds"] = int(user_dict.get("total_study_seconds", 0) or 0)  # 取得累計學習秒數
    return user_dict  # 回傳完整使用者個人檔案字典
# ---------------------------------------------------------------------------------------------------------------------- # 使用者興趣偏好與字幕開關記憶更新函式（支援最多 10 個標籤）
def update_user_preferences(uid: str, hobbies: List[str], default_sub_ja: Optional[bool] = None, default_sub_zh: Optional[bool] = None) -> Dict[str, Any]:  # 定義更新偏好函式
    user = get_or_create_user(uid, "")  # 取得使用者目前偏好以保留原有字幕設定
    sub_ja = default_sub_ja if default_sub_ja is not None else user.get("default_sub_ja", True)  # 容錯保留舊有日文字幕設定
    sub_zh = default_sub_zh if default_sub_zh is not None else user.get("default_sub_zh", True)  # 容錯保留舊有中文字幕設定
    conn = get_db_connection()  # 取得資料庫連線
    cursor = conn.cursor()  # 建立操作游標
    hobbies_json = json.dumps(hobbies[:10], ensure_ascii=False)  # 強制限制上限 10 個標籤並轉 JSON
    cursor.execute("UPDATE users SET hobbies = ?, default_sub_ja = ?, default_sub_zh = ? WHERE uid = ?", (hobbies_json, 1 if sub_ja else 0, 1 if sub_zh else 0, uid))  # 執行偏好欄位更新
    conn.commit()  # 提交交易
    conn.close()  # 關閉連線
    return get_or_create_user(uid, "")  # 回傳最新使用者資料
# ---------------------------------------------------------------------------------------------------------------------- # 標記使用者已完成五十音基礎學習模組函式
def mark_kana_completed(uid: str) -> Dict[str, Any]:  # 定義標記五十音完成函式
    conn = get_db_connection()  # 取得資料庫連線
    cursor = conn.cursor()  # 建立操作游標
    cursor.execute("UPDATE users SET kana_completed = 1 WHERE uid = ?", (uid,))  # 更新五十音完成旗標為 1
    conn.commit()  # 提交交易
    conn.close()  # 關閉連線
    check_and_auto_promote(uid)  # 檢查是否立即符合自動晉升外門弟子條件
    evaluate_and_update_user_tier_and_badges(uid)  # 評估解鎖相關成就徽章
    return get_or_create_user(uid, "")  # 回傳最新使用者個人檔案
# ---------------------------------------------------------------------------------------------------------------------- # 新手試煉迷你遊戲成績紀錄與自動晉升判定核心函式 (Automated Level-Up Gate)
def record_beginner_game_score(uid: str, game_id: int, accuracy: float, score: int) -> Dict[str, Any]:  # 定義記錄試煉成績函式
    conn = get_db_connection()  # 取得資料庫連線
    cursor = conn.cursor()  # 建立操作游標
    acc_col = f"game{game_id}_acc"  # 計算對應關卡欄位名稱
    cursor.execute(f"SELECT {acc_col} FROM users WHERE uid = ?", (uid,))  # 讀取該關卡歷史最高正確率
    row = cursor.fetchone()  # 取得結果
    prev_acc = row[0] if row and row[0] is not None else 0.0  # 取得歷史正確率數值
    new_acc = max(prev_acc, round(accuracy, 1))  # 保留歷史最高表現紀錄
    cursor.execute(f"UPDATE users SET {acc_col} = ? WHERE uid = ?", (new_acc, uid))  # 更新最高正確率至資料庫
    conn.commit()  # 提交交易
    conn.close()  # 關閉連線以防互鎖
    record_study_activity(words_count=2, quiz_count=1)  # 進行試煉小遊戲自動計入今日打卡
    promotion_info = check_and_auto_promote(uid, last_game_id=game_id, current_acc=accuracy)  # 呼叫自動晉級檢驗引擎
    evaluate_and_update_user_tier_and_badges(uid)  # 觸發全盤階級與徽章更新評估
    return promotion_info  # 回傳晉級判定詳細結果字典
# ---------------------------------------------------------------------------------------------------------------------- # 審核並執行自動晉升「外門弟子」門檻檢查函式
def check_and_auto_promote(uid: str, last_game_id: int = 1, current_acc: float = 0.0) -> Dict[str, Any]:  # 定義自動晉級判斷函式
    user = get_or_create_user(uid, "")  # 取得使用者當前最新個人檔案
    g1 = user.get("game1_acc", 0.0)  # 第一關翻牌正確率
    g2 = user.get("game2_acc", 0.0)  # 第二關辨字正確率
    g3 = user.get("game3_acc", 0.0)  # 第三關打字正確率
    overall_avg = round((g1 + g2 + g3) / 3.0, 1)  # 計算三項試煉小遊戲之平均正確率
    kana_done = user.get("kana_completed", False)  # 是否已研讀五十音
    is_promoted = False  # 初始化晉級布林旗標為 False
    new_level = user.get("user_level", "新手小白")  # 取得當前等級
    if new_level == "新手小白":  # 僅在當前處於新手小白階段才觸發外門弟子晉階
        if kana_done and g1 >= 80.0 and g2 >= 80.0 and g3 >= 80.0:  # 嚴格門檻：五十音研讀完成且三關皆達 80% 以上
            is_promoted = True  # 判定晉級成功
            new_level = "外門弟子"  # 升級為外門弟子
            conn = get_db_connection()  # 取得連線
            cursor = conn.cursor()  # 建立游標
            cursor.execute("UPDATE users SET user_level = '外門弟子' WHERE uid = ?", (uid,))  # 將新階級寫入資料庫
            conn.commit()  # 提交交易
            conn.close()  # 關閉連線
            msg = "🎉 恭喜！通過五十音與三項試煉考驗，境界成功突破，晉升為【外門弟子】！全站影片與高級生詞庫全面解鎖！"  # 晉級賀詞
        else:  # 若尚未全部達標
            msg = f"⚔️ 試煉進行中！三關平均正確率：{overall_avg}%。需完成五十音且三項遊戲皆達 80% 即可晉升外門弟子！"  # 激勵提示語
    else:  # 已為外門弟子或更高境界
        msg = f"🏆 您已是【{new_level}】，修為穩固，請繼續挑戰高階單字與視聽辭典！"  # 讚許提示語
    return {  # 回傳判定結果封裝字典
        "game_id": last_game_id,  # 剛結算關卡
        "current_acc": current_acc,  # 當次正確率
        "game1_acc": g1,  # 遊戲一最佳紀錄
        "game2_acc": g2,  # 遊戲二最佳紀錄
        "game3_acc": g3,  # 遊戲三最佳紀錄
        "overall_avg_acc": overall_avg,  # 綜合平均正確率
        "kana_completed": kana_done,  # 五十音狀態
        "is_promoted": is_promoted,  # 是否本次觸發晉級
        "new_level": new_level,  # 最新修真階級
        "message": msg  # 回饋訊息
    }  # 結束晉級字典回傳
# ---------------------------------------------------------------------------------------------------------------------- # 徽章館資料查詢函式（計算使用者已解鎖與未解鎖徽章）
def get_user_badges(uid: str) -> List[Dict[str, Any]]:  # 宣告查詢使用者所有徽章狀態函式
    user = get_or_create_user(uid, "")  # 讀取使用者個人檔案
    user_badges_set = set(user.get("badges", ["badge_novice"]))  # 取得已解鎖徽章集合
    result_badges = []  # 初始化結果陣列
    for b in ALL_BADGES:  # 走訪全域徽章定義
        item = dict(b)  # 複製徽章元資料字典
        is_unlocked = b["id"] in user_badges_set  # 判定是否已解鎖
        item["unlocked"] = is_unlocked  # 設定解鎖狀態旗標
        item["unlocked_at"] = user.get("created_at", "2026-09-26") if is_unlocked else None  # 設定解鎖日期
        result_badges.append(item)  # 加入回傳清單
    return result_badges  # 回傳徽章清單陣列
# ---------------------------------------------------------------------------------------------------------------------- # 自動晉升階級審核與成就徽章解鎖核心引擎 (Automated Tier & Badges Progression)
def evaluate_and_update_user_tier_and_badges(uid: str) -> Dict[str, Any]:  # 定義階級與徽章自動升級評估函式
    user = get_or_create_user(uid, "")  # 取得使用者檔案
    curr_level = user.get("user_level", "新手小白")  # 當前階級
    badges = set(user.get("badges", ["badge_novice"]))  # 已有徽章集合
    badges.add("badge_novice")  # 登入者皆擁有初始新手徽章
    stats = get_study_statistics()  # 讀取整體學習統計
    streak_data = get_streak_calendar_data()  # 讀取連續打卡資料
    total_reviews = stats.get("total_reviews", 0)  # 總複習次數
    mastered_count = stats.get("mastered_count", 0)  # 已掌握單字數
    acc = stats.get("overall_accuracy", 0.0)  # 測驗綜合正確率
    streak_cnt = streak_data.get("current_streak", 0)  # 連續打卡天數
    new_level = curr_level  # 預設維持當前階級
    newly_promoted = False  # 是否觸發晉升旗標
    if curr_level == "新手小白":  # 判斷新手小白晉階
        if user.get("kana_completed", False) and user.get("game1_acc", 0) >= 80.0 and user.get("game2_acc", 0) >= 80.0 and user.get("game3_acc", 0) >= 80.0:  # 滿足三關與五十音
            new_level = "外門弟子"  # 升為外門弟子
            newly_promoted = True  # 標記晉升
    elif curr_level == "外門弟子":  # 判斷外門弟子晉階內門弟子
        if (total_reviews >= 15 or mastered_count >= 4) and acc >= 70.0:  # 掌握一定生詞且準確率達標
            new_level = "內門弟子"  # 升為內門弟子
            newly_promoted = True  # 標記晉升
    elif curr_level == "內門弟子":  # 判斷內門弟子晉階長老
        if (total_reviews >= 35 or mastered_count >= 8) and streak_cnt >= 3 and acc >= 80.0:  # 長期修行且高準確率
            new_level = "長老"  # 升為長老
            newly_promoted = True  # 標記晉升
    if new_level in ["外門弟子", "內門弟子", "長老"]:  # 若階級達到外門弟子以上
        badges.add("badge_outer")  # 解鎖外門弟子徽章
    if new_level in ["內門弟子", "長老"]:  # 若階級達到內門弟子以上
        badges.add("badge_inner")  # 解鎖內門弟子徽章
    if new_level == "長老":  # 若為長老
        badges.add("badge_elder")  # 解鎖長老宗師徽章
    if streak_cnt >= 3:  # 連續打卡達 3 天
        badges.add("badge_streak_3")  # 解鎖三日修行徽章
    if mastered_count >= 5:  # 掌握單字達 5 個
        badges.add("badge_vocab_5")  # 解鎖熟稔生詞徽章
    conn = get_db_connection()  # 取得連線
    cursor = conn.cursor()  # 建立操作游標
    cursor.execute("UPDATE users SET user_level = ?, badges = ? WHERE uid = ?", (new_level, json.dumps(list(badges), ensure_ascii=False), uid))  # 更新資料庫階級與徽章
    conn.commit()  # 提交交易
    conn.close()  # 關閉連線
    return {"new_level": new_level, "is_promoted": newly_promoted, "badges": list(badges)}  # 回傳升級評估字典
# ---------------------------------------------------------------------------------------------------------------------- # 取得特定階級之能力分級測驗題目清單函式
def get_placement_questions(target_tier: str) -> List[Dict[str, Any]]:  # 宣告取得分級測驗題目函式
    conn = get_db_connection()  # 取得資料庫連線
    cursor = conn.cursor()  # 建立游標
    cursor.execute("SELECT * FROM placement_questions WHERE target_tier = ?", (target_tier,))  # 依階級查詢考題
    rows = cursor.fetchall()  # 讀取查詢結果
    conn.close()  # 關閉連線
    questions = []  # 初始化考題陣列
    for r in rows:  # 走訪每一道考題
        item = dict(r)  # 轉換為字典
        item["options"] = json.loads(item.get("options_json") or "[]")  # 解析四個選項陣列
        questions.append(item)  # 加入考題清單
    return questions  # 回傳考題陣列
# ---------------------------------------------------------------------------------------------------------------------- # 動態能力測試結算與智慧降階引擎 (Adaptive Placement Test & Smart Fallback)
def evaluate_placement_test(uid: str, target_tier: str, answers: Union[Dict[str, str], List[Dict[str, Any]]]) -> Dict[str, Any]:  # 定義能力分級評定函式
    norm_answers: Dict[str, str] = {}  # 初始化正規化作答對照字典
    if isinstance(answers, dict):  # 判斷若輸入即為字典
        norm_answers = {str(k): str(v) for k, v in answers.items()}  # 轉為字串鍵值對
    elif isinstance(answers, list):  # 判斷若輸入為作答物件清單
        for item in answers:  # 走訪每筆作答物件
            if isinstance(item, dict):  # 確保項目為字典結構
                q_id = str(item.get("question_id") or item.get("id") or item.get("qid") or "")  # 取得題目 ID
                ans_val = str(item.get("selected_option") or item.get("answer") or item.get("user_answer") or "")  # 取得作答文字
                if q_id:  # 若題號有效
                    norm_answers[q_id] = ans_val  # 寫入正規化字典
    if target_tier == "新手小白":  # 判斷若使用者主動選擇自新手小白從頭築基
        conn = get_db_connection()  # 取得連線
        cursor = conn.cursor()  # 建立游標
        cursor.execute("UPDATE users SET onboarding_completed = 1, user_level = '新手小白' WHERE uid = ?", (uid,))  # 標記定級完成
        conn.commit()  # 提交交易
        conn.close()  # 關閉連線
        return {  # 回傳新手定級字典
            "target_tier": "新手小白",  # 目標挑戰境界
            "score": 100.0,  # 免試預設滿分
            "assigned_tier": "新手小白",  # 定級境界
            "passed": True,  # 判定通過
            "fallback_triggered": False,  # 未觸發降階
            "message": "道基初定！踏入日語修真初途，讓我們從五十音與試煉關卡開始扎實修行！",  # 激勵評語
            "unlocked_badge": "初入道途 · 假名破曉",  # 解鎖新手徽章
            "badges_awarded": ["初入道途 · 假名破曉"]  # 頒發之徽章清單陣列
        }  # 結束新手免試回傳
    questions = get_placement_questions(target_tier)  # 取得該目標階級之試卷題目
    if not questions:  # 容錯判斷題目若不存在
        assigned_tier = "外門弟子" if target_tier != "長老" else "內門弟子"  # 指派預設降階階級
        return {  # 回傳容錯定級結果
            "target_tier": target_tier,  # 目標境界
            "score": 80.0,  # 預設得分
            "assigned_tier": assigned_tier,  # 指派境界
            "passed": True,  # 通過
            "fallback_triggered": False,  # 未觸發降階
            "message": "能力定級完成！",  # 評語
            "unlocked_badge": None,  # 無解鎖徽章
            "badges_awarded": []  # 空徽章陣列
        }  # 結束容錯回傳
    correct_count = 0  # 初始化答對題數計數器
    total_q = len(questions)  # 題目總題數
    for q in questions:  # 逐一核對作答
        qid_str = str(q["id"])  # 題目代碼字串
        user_ans = norm_answers.get(qid_str, "").strip()  # 取得使用者作答答案
        if user_ans == q["correct_answer"].strip():  # 答案正確判定
            correct_count += 1  # 答對計數累加 1
    score = round((correct_count / total_q) * 100, 1)  # 計算得分百分比
    passed = False  # 初始化通過旗標
    fallback_triggered = False  # 初始化是否觸發智慧降階旗標
    assigned_tier = "新手小白"  # 初始化授予境界
    msg = ""  # 初始化評語
    badge_name = None  # 初始化解鎖徽章
    if target_tier == "外門弟子":  # 挑戰目標為外門弟子
        if score >= 75.0:  # 得分達 75 分以上
            passed = True  # 通過考核
            assigned_tier = "外門弟子"  # 授予外門弟子境界
            badge_name = "登堂入室 · 詞海泛舟"  # 解鎖外門弟子徽章
            msg = f"🎉 恭喜！測驗得分 {score}%，精準掌握基礎假名與單字，直接通過定級並晉升為【外門弟子】！"  # 晉升賀詞
        else:  # 未達 75 分智慧降階
            fallback_triggered = True  # 標記觸發智慧降階
            assigned_tier = "新手小白"  # 智慧降階至新手小白
            msg = f"🌱 測驗得分 {score}%，基礎仍需鞏固。系統已智慧為您安排至【新手小白】境界，建議先研讀五十音圖解！"  # 鼓勵建議詞
    elif target_tier == "內門弟子":  # 挑戰目標為內門弟子
        if score >= 75.0:  # 得分達 75 分以上
            passed = True  # 通過考核
            assigned_tier = "內門弟子"  # 授予內門弟子境界
            badge_name = "心領神會 · 聽音明理"  # 解鎖內門弟子徽章
            msg = f"⚡ 太強了！測驗得分 {score}%，文法與實用詞彙功底深厚，成功定級為【內門弟子】！"  # 晉升賀詞
        elif score >= 50.0:  # 得分介於 50 至 74 分智慧降階至外門弟子
            fallback_triggered = True  # 標記觸發智慧降階
            assigned_tier = "外門弟子"  # 降階至外門弟子
            badge_name = "登堂入室 · 詞海泛舟"  # 解鎖外門弟子徽章
            msg = f"🥋 測驗得分 {score}%，表現相當優秀！系統智慧定級為【外門弟子】，全站雙語影音字典全面解鎖！"  # 降階賀詞
        else:  # 低於 50 分降至新手小白
            fallback_triggered = True  # 標記觸發智慧降階
            assigned_tier = "新手小白"  # 降階至新手小白
            msg = f"🌱 測驗得分 {score}%，已智慧安排至【新手小白】進行系統化築基修行！"  # 降階鼓勵詞
    elif target_tier == "長老":  # 挑戰目標為長老尊位
        if score >= 80.0:  # 得分達 80 分以上
            passed = True  # 通過最高考核
            assigned_tier = "長老"  # 授予長老最高境界
            badge_name = "登峰造極 · 日語大宗師"  # 解鎖長老徽章
            msg = f"👑 絕頂高手！測驗得分 {score}%，高階修辭與商務敬語運用自如，榮登【長老】大宗師寶座！"  # 封頂賀詞
        elif score >= 60.0:  # 得分介於 60 至 79 分智慧降階至內門弟子
            fallback_triggered = True  # 標記觸發智慧降階
            assigned_tier = "內門弟子"  # 降階至內門弟子
            badge_name = "心領神會 · 聽音明理"  # 解鎖內門弟子徽章
            msg = f"⚔️ 測驗得分 {score}%，日語功底極為扎實！系統智慧定級為【內門弟子】，距離長老僅一步之遙！"  # 降階賀詞
        else:  # 低於 60 分智慧降階至外門弟子
            fallback_triggered = True  # 標記觸發智慧降階
            assigned_tier = "外門弟子"  # 降階至外門弟子
            badge_name = "登堂入室 · 詞海泛舟"  # 解鎖外門弟子徽章
            msg = f"🥋 測驗得分 {score}%，系統智慧定級為【外門弟子】，持續精進必定登頂長老！"  # 降階鼓勵詞
    conn = get_db_connection()  # 取得資料庫連線
    cursor = conn.cursor()  # 建立操作游標
    kana_comp = 1 if assigned_tier in ["外門弟子", "內門弟子", "長老"] else 0  # 若定級外門以上預設自動掌握五十音
    cursor.execute("UPDATE users SET onboarding_completed = 1, user_level = ?, kana_completed = max(kana_completed, ?) WHERE uid = ?", (assigned_tier, kana_comp, uid))  # 更新使用者檔案
    conn.commit()  # 提交交易
    conn.close()  # 關閉連線
    evaluate_and_update_user_tier_and_badges(uid)  # 同步更新成就與徽章庫
    badges_awarded = [badge_name] if badge_name else []  # 整理本次解鎖之徽章名稱清單
    return {  # 回傳結算回饋字典
        "target_tier": target_tier,  # 目標挑戰境界
        "score": score,  # 實得分數百分比
        "assigned_tier": assigned_tier,  # 最終授予之境界
        "passed": passed,  # 是否通過挑戰
        "fallback_triggered": fallback_triggered,  # 是否觸發智慧降階
        "message": msg,  # 系統回饋激勵評語
        "unlocked_badge": badge_name,  # 本次解鎖之徽章名稱
        "badges_awarded": badges_awarded  # 本次頒發之徽章清單陣列
    }  # 結束結算字典回傳
# ---------------------------------------------------------------------------------------------------------------------- # 動態行為偏好遙測追蹤函式 (Dynamic Behavioral Telemetry)
def record_behavior_telemetry(uid: str, category: str, action_type: str, duration_seconds: float) -> Dict[str, Any]:  # 定義遙測紀錄函式
    user = get_or_create_user(uid, "")  # 讀取使用者個人檔案
    weights = user.get("behavior_weights", {})  # 取得行為加權字典
    cat_key = category.strip() if category else "綜合"  # 取得清理後主題類別
    curr_w = weights.get(cat_key, 1.0)  # 讀取當前類別權重預設 1.0
    action_factor = 2.0 if action_type == "hover_word" else 1.5 if action_type == "view_media" else 1.0  # 依行為重要性賦予加乘因子
    duration_bonus = min(duration_seconds * 0.1, 5.0)  # 駐留時長換算權重加成最高 5 點
    weights[cat_key] = round(curr_w + action_factor + duration_bonus, 2)  # 計算最新加權數值
    add_seconds = int(duration_seconds)  # 計算累計秒數
    conn = get_db_connection()  # 取得連線
    cursor = conn.cursor()  # 建立游標
    cursor.execute("UPDATE users SET behavior_weights = ?, total_study_seconds = total_study_seconds + ? WHERE uid = ?", (json.dumps(weights, ensure_ascii=False), add_seconds, uid))  # 更新資料庫
    conn.commit()  # 提交交易
    conn.close()  # 關閉連線
    if action_type in ["view_media", "hover_word"]:  # 若為影音互動動作
        evaluate_and_update_user_tier_and_badges(uid)  # 檢查是否觸發影音行者徽章
    return {"status": "ok", "weights": weights}  # 回傳更新後之權重字典
# ---------------------------------------------------------------------------------------------------------------------- # 取得官方合法影音清單函式（結合使用者興趣與動態行為偏好智慧推薦排序）
def get_all_media(category: Optional[str] = None, uid: Optional[str] = None) -> List[Dict[str, Any]]:  # 定義多媒體影音列表查詢函式
    conn = get_db_connection()  # 取得資料庫連線
    cursor = conn.cursor()  # 建立查詢游標
    if category and category != "all":  # 判斷是否指定特定分類
        cursor.execute("SELECT * FROM media WHERE category = ? ORDER BY likes_count DESC", (category,))  # 依分類查詢
    else:  # 查詢全部分類影音
        cursor.execute("SELECT * FROM media ORDER BY likes_count DESC")  # 按受歡迎程度排序查詢
    rows = cursor.fetchall()  # 讀取查詢結果
    conn.close()  # 關閉連線
    user_hobbies = []  # 初始化使用者興趣標籤
    user_weights = {}  # 初始化動態行為權重
    if uid:  # 若提供了使用者唯一 UID
        user = get_or_create_user(uid, "")  # 讀取使用者個人檔案
        user_hobbies = user.get("hobbies", [])  # 讀取興趣標籤陣列
        user_weights = user.get("behavior_weights", {})  # 讀取行為加權字典
    media_list = []  # 初始化結果陣列
    for r in rows:  # 走訪每筆影音記錄
        item = dict(r)  # 轉換為字典
        item["subtitles"] = json.loads(item.get("subtitles_json") or "[]")  # 解析字幕 JSON 字串為時間軸物件陣列
        rec_score = item["likes_count"] * 1.0  # 基礎喜歡數分數
        cat = item["category"]  # 影片分類標籤
        if cat in user_hobbies or any(h in cat for h in user_hobbies):  # 吻合使用者主動選擇之興趣標籤
            rec_score += 25.0  # 賦予高額興趣加權分
        if cat in user_weights:  # 吻合動態行為高頻互動分類
            rec_score += user_weights[cat] * 3.0  # 依互動權重累加加權
        item["recommendation_score"] = rec_score  # 記錄該影音推薦綜合評分
        media_list.append(item)  # 加入結果列表
    media_list.sort(key=lambda m: m.get("recommendation_score", 0), reverse=True)  # 依推薦評分降冪智慧排序
    return media_list  # 回傳解析並推薦排序完成之影音陣列
# ---------------------------------------------------------------------------------------------------------------------- # 使用者影音感興趣 / 不感興趣偏好回饋紀錄函式
def record_media_feedback(media_id: str, action: str) -> Dict[str, Any]:  # 定義影音推薦評價反饋函式
    conn = get_db_connection()  # 取得資料庫連線
    cursor = conn.cursor()  # 建立操作游標
    if action == "interested":  # 判斷若標記為喜歡感興趣
        cursor.execute("UPDATE media SET likes_count = likes_count + 1 WHERE id = ?", (media_id,))  # 累加喜歡計數
    else:  # 判斷若標記為不感興趣
        cursor.execute("UPDATE media SET dislikes_count = dislikes_count + 1 WHERE id = ?", (media_id,))  # 累加不感興趣計數
    conn.commit()  # 提交交易
    cursor.execute("SELECT likes_count, dislikes_count FROM media WHERE id = ?", (media_id,))  # 查詢更新後數據
    row = cursor.fetchone()  # 取得最新列
    conn.close()  # 關閉連線
    return {"media_id": media_id, "likes_count": row[0], "dislikes_count": row[1]} if row else {}  # 回傳最新評價計數字典
# ---------------------------------------------------------------------------------------------------------------------- # 儲存使用者直接意見反饋至資料庫函式 (直達 ytpre.new1@gmail.com)
def save_feedback(user_name: str, user_email: str, category: str, message: str, target_email: str = "ytpre.new1@gmail.com") -> Dict[str, Any]:  # 定義儲存反饋函式
    conn = get_db_connection()  # 取得資料庫連線
    cursor = conn.cursor()  # 建立操作游標
    cursor.execute("INSERT INTO feedbacks (user_name, user_email, category, message, target_email) VALUES (?, ?, ?, ?, ?)", (user_name.strip(), user_email.strip(), category.strip(), message.strip(), target_email.strip()))  # 寫入反饋資料表記錄
    new_id = cursor.lastrowid  # 取得反饋主鍵編號
    conn.commit()  # 提交交易
    conn.close()  # 關閉連線
    return {"feedback_id": new_id, "status": "sent", "target_email": target_email, "message": "意見回饋已成功記錄並路由至官方信箱！"}  # 回傳成功結果字典
# ---------------------------------------------------------------------------------------------------------------------- # 記錄使用者每日學習活動（生詞卡複習或測驗提交時自動呼叫）
def record_study_activity(words_count: int = 0, quiz_count: int = 0) -> None:  # 定義記錄每日學習打卡函式
    today_str = datetime.now().strftime("%Y-%m-%d")  # 取得當前年月日字串
    conn = get_db_connection()  # 取得資料庫連線
    cursor = conn.cursor()  # 建立 SQL 操作游標
    upsert_sql = "INSERT INTO study_activity (activity_date, words_reviewed, quizzes_taken) VALUES (?, ?, ?) ON CONFLICT(activity_date) DO UPDATE SET words_reviewed = words_reviewed + ?, quizzes_taken = quizzes_taken + ?"  # 建立 SQLite 專用之 UPSERT 語法字串
    cursor.execute(upsert_sql, (today_str, words_count, quiz_count, words_count, quiz_count))  # 執行寫入或累加
    conn.commit()  # 提交交易
    conn.close()  # 關閉連線
# ---------------------------------------------------------------------------------------------------------------------- # 計算使用者連續打卡天數（Streak）與月份日曆格子數據函式
def get_streak_calendar_data(target_year: Optional[int] = None, target_month: Optional[int] = None) -> Dict[str, Any]:  # 定義取得打卡日曆資料函式
    now = datetime.now()  # 取得當前時間物件
    year = target_year if target_year else now.year  # 若未傳入指定年份則採用當今年份
    month = target_month if target_month else now.month  # 若未傳入指定月份則採用當前月份
    conn = get_db_connection()  # 取得資料庫連線
    cursor = conn.cursor()  # 建立 SQL 操作游標
    cursor.execute("SELECT activity_date, words_reviewed, quizzes_taken FROM study_activity ORDER BY activity_date ASC")  # 依日期遞增查詢全部打卡表記錄
    all_acts = cursor.fetchall()  # 讀取全部歷史活動記錄
    conn.close()  # 關閉連線
    activity_map = {row["activity_date"]: dict(row) for row in all_acts}  # 轉換為以日期字串為鍵的活動字典
    total_active_days = len(activity_map)  # 歷史累計學習總天數
    today_obj = now.date()  # 取得今日日期物件
    today_str = today_obj.strftime("%Y-%m-%d")  # 取得今日日期格式字串
    today_studied = today_str in activity_map  # 判斷今日是否已有學習打卡紀錄
    current_streak = 0  # 初始化當前連續打卡天數為 0
    check_day = today_obj if today_studied else today_obj - timedelta(days=1)  # 若今日已打卡從今日往前回溯，否則從昨日回溯
    while True:  # 透過迴圈連續往前檢查歷史每一天
        day_str = check_day.strftime("%Y-%m-%d")  # 格式化檢查日字串
        if day_str in activity_map:  # 若該天有打卡記錄
            current_streak += 1  # 連續天數累加 1
            check_day = check_day - timedelta(days=1)  # 繼續前進至前一天
        else:  # 若中斷
            break  # 終止連續回溯迴圈
    longest_streak = 0  # 初始化歷史最長連續天數為 0
    running_streak = 0  # 初始化臨時連續天數為 0
    prev_date: Optional[datetime.date] = None  # 記錄前一筆活動日期指標
    for date_str in sorted(activity_map.keys()):  # 按照日期升冪順序迭代走訪各個學習日
        curr_d = datetime.strptime(date_str, "%Y-%m-%d").date()  # 解析日期字串為日期物件
        if prev_date is None or (curr_d - prev_date).days == 1:  # 判斷若為首筆或是恰好相差 1 天的連續日
            running_streak += 1  # 延續臨時打卡計數
        else:  # 判斷若中途有斷天
            running_streak = 1  # 重置臨時連續計數為 1
        if running_streak > longest_streak:  # 若當前臨時連續數打破歷史紀錄
            longest_streak = running_streak  # 更新最長連續天數紀錄
            prev_date = curr_d  # 指標移至當前日期
    longest_streak = max(longest_streak, current_streak)  # 確保最長紀錄不小於當前連續數
    _, total_days_in_month = calendar.monthrange(year, month)  # 計算指定年月份的自然天數總額（例如 28 ~ 31 天）
    month_days: List[Dict[str, Any]] = []  # 初始化該月份日期清單
    for day_num in range(1, total_days_in_month + 1):  # 依序走訪該月份之每一天（1 號至最後一天）
        d_str = f"{year:04d}-{month:02d}-{day_num:02d}"  # 組合完整的標準 ISO 日期字串
        act = activity_map.get(d_str)  # 查詢當日是否有活動紀錄
        month_days.append({  # 封裝單日日曆格子物件
            "day": day_num,  # 幾號
            "date_str": d_str,  # 日期字串
            "is_active": act is not None,  # 當日是否打卡布林值
            "words_count": act["words_reviewed"] if act else 0,  # 複習單字總張數
            "quizzes_count": act["quizzes_taken"] if act else 0,  # 完成測驗回數
            "is_today": d_str == today_str  # 是否標記為今天
        })  # 結束單日資料封裝
    return {  # 回傳完整的打卡日曆整合統計資料字典
        "current_streak": current_streak,  # 當前連續打卡天數
        "longest_streak": longest_streak,  # 歷史最長連續天數
        "total_active_days": total_active_days,  # 歷史累計學習總天數
        "today_studied": today_studied,  # 今日打卡完成狀態
        "current_year": year,  # 檢視之年份
        "current_month": month,  # 檢視之月份
        "month_days": month_days  # 當月日曆格子陣列
    }  # 結束日曆資料字典回傳
# ---------------------------------------------------------------------------------------------------------------------- # 取得雲端單字清單函式（支援 SRS 狀態與關鍵字篩選）
def get_all_words(srs_status: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:  # 宣告查詢所有單字函式
    conn = get_db_connection()  # 取得資料庫操作連線
    cursor = conn.cursor()  # 建立 SQL 執行游標
    query = "SELECT * FROM words WHERE 1=1"  # 起始 SQL 查詢基礎字串
    params: List[Any] = []  # 宣告 SQL 參數列表防止 SQL 注入
    if srs_status and srs_status != "all":  # 判斷若前端指定了 SRS 掌握度篩選條件
        query += " AND srs_status = ?"  # 動態串接 SRS 狀態過濾條件
        params.append(srs_status)  # 將篩選參數加入參數列表
    if search:  # 判斷若前端提供了關鍵字搜尋條件
        query += " AND (word LIKE ? OR reading LIKE ? OR meaning LIKE ? OR romaji LIKE ?)"  # 支援日文漢字、假名、中文與羅馬音模糊搜尋
        keyword = f"%{search.strip()}%"  # 建立 SQL 模糊比對萬用字元字串
        params.extend([keyword, keyword, keyword, keyword])  # 填入四個欄位對應的搜尋參數
    query += " ORDER BY id DESC"  # 設定依建立先後排序（新加入者優先顯示）
    cursor.execute(query, params)  # 帶入參數執行查詢
    rows = cursor.fetchall()  # 讀取全部符合條件之資料列
    conn.close()  # 關閉資料庫連線
    return [dict(row) for row in rows]  # 將每筆 Row 轉換為原生 Python 字典並回傳陣列
# ---------------------------------------------------------------------------------------------------------------------- # 依單字 ID 查詢單筆單字詳情函式
def get_word_by_id(word_id: int) -> Optional[Dict[str, Any]]:  # 宣告依主鍵查詢單字函式
    conn = get_db_connection()  # 取得資料庫連線
    cursor = conn.cursor()  # 建立查詢游標
    cursor.execute("SELECT * FROM words WHERE id = ?", (word_id,))  # 執行主鍵精確比對查詢
    row = cursor.fetchone()  # 讀取查詢結果第一筆
    conn.close()  # 關閉資料庫連線
    return dict(row) if row else None  # 若查詢到記錄則轉為字典回傳，若無則回傳 None
# ---------------------------------------------------------------------------------------------------------------------- # 新增單字至個人雲端單字本函式
def create_word(word_data: Dict[str, Any]) -> Dict[str, Any]:  # 宣告建立新單字函式
    conn = get_db_connection()  # 取得資料庫連線
    cursor = conn.cursor()  # 建立操作游標
    insert_sql = "INSERT INTO words (word, reading, romaji, meaning, example_ja, example_zh, level, srs_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"  # 定義新增單字 SQL 語法
    cursor.execute(insert_sql, (  # 執行寫入並傳入乾淨之欄位數值元組
        word_data["word"].strip(),  # 寫入單字日文書寫表記
        word_data["reading"].strip(),  # 寫入單字平假名發音
        word_data["romaji"].strip().lower(),  # 寫入單字小寫羅馬拼音
        word_data["meaning"].strip(),  # 寫入中文釋義
        word_data.get("example_ja", "").strip(),  # 寫入日文範例例句
        word_data.get("example_zh", "").strip(),  # 寫入範例中文翻譯
        word_data.get("level", "N5").strip(),  # 寫入日檢難度級別標籤
        word_data.get("srs_status", "need_practice")  # 寫入預設掌握度狀態
    ))  # 結束執行新增語句
    new_id = cursor.lastrowid  # 取得本次插入所自動生成的主鍵 ID
    conn.commit()  # 提交交易確認寫入
    conn.close()  # 關閉連線以釋放資料庫檔案鎖定
    record_study_activity(words_count=1)  # 新增單字時自動計入今日學習活動
    return get_word_by_id(new_id)  # 重新查詢並回傳完整的新增單字資料字典
# ---------------------------------------------------------------------------------------------------------------------- # 更新單字 SRS 間隔重複掌握度與複習成績統計函式
def update_word_srs(word_id: int, srs_status: str, is_correct: Optional[bool] = None) -> Optional[Dict[str, Any]]:  # 宣告更新 SRS 狀態函式
    conn = get_db_connection()  # 取得資料庫連線
    cursor = conn.cursor()  # 建立操作游標
    if is_correct is not None:  # 判斷是否為測驗作答觸發（需連帶累計複習統計數據）
        correct_inc = 1 if is_correct else 0  # 答對則答對次數加 1，答錯則加 0
        update_sql = "UPDATE words SET srs_status = ?, review_count = review_count + 1, correct_count = correct_count + ? WHERE id = ?"  # 定義累計統計之 SQL 語法
        cursor.execute(update_sql, (srs_status, correct_inc, word_id))  # 執行結合統計更新之 SQL 語法
    else:  # 若純粹由生詞卡介面使用者手動標記
        cursor.execute("UPDATE words SET srs_status = ? WHERE id = ?", (srs_status, word_id))  # 僅更新掌握度欄位
    conn.commit()  # 提交資料庫交易
    conn.close()  # 關閉連線以釋放檔案鎖定避免併發鎖表問題
    if is_correct is not None:  # 判斷若為測驗作答
        record_study_activity(words_count=1, quiz_count=1)  # 測驗作答時記錄單字與測驗打卡
    else:  # 判斷若為純生詞卡評級
        record_study_activity(words_count=1)  # 生詞卡評級時記錄單字打卡
    return get_word_by_id(word_id)  # 回傳更新後的最新單字物件
# ---------------------------------------------------------------------------------------------------------------------- # 刪除指定單字函式
def delete_word(word_id: int) -> bool:  # 宣告刪除單字函式
    conn = get_db_connection()  # 取得資料庫連線
    cursor = conn.cursor()  # 建立操作游標
    cursor.execute("DELETE FROM words WHERE id = ?", (word_id,))  # 執行刪除單字 SQL
    affected = cursor.rowcount  # 取得受影響的資料列筆數
    conn.commit()  # 提交交易
    conn.close()  # 關閉連線
    return affected > 0  # 若刪除筆數大於 0 則代表成功並回傳 True
# ---------------------------------------------------------------------------------------------------------------------- # 隨機取得多選題干擾選項單字函式
def get_random_distractors(exclude_word_id: int, limit: int = 3) -> List[Dict[str, Any]]:  # 宣告選取干擾項函式
    conn = get_db_connection()  # 取得資料庫連線
    cursor = conn.cursor()  # 建立操作游標
    distractor_sql = "SELECT * FROM words WHERE id != ? ORDER BY RANDOM() LIMIT ?"  # 隨機抽取不包含正確答案的干擾項 SQL
    cursor.execute(distractor_sql, (exclude_word_id, limit))  # 執行排除正解之隨機干擾單字抽取
    rows = cursor.fetchall()  # 讀取查詢結果
    conn.close()  # 關閉連線
    return [dict(row) for row in rows]  # 回傳干擾項字典陣列
# ---------------------------------------------------------------------------------------------------------------------- # 統計使用者全體學習進度與正確率函式
def get_study_statistics() -> Dict[str, Any]:  # 宣告綜合學習統計計算函式
    conn = get_db_connection()  # 取得資料庫連線
    cursor = conn.cursor()  # 建立操作游標
    cursor.execute("SELECT COUNT(*) FROM words")  # 查詢資料庫單字總數
    total_words = cursor.fetchone()[0]  # 取得總單字數量
    cursor.execute("SELECT COUNT(*) FROM words WHERE srs_status = 'mastered'")  # 查詢已掌握單字數
    mastered_count = cursor.fetchone()[0]  # 取得已掌握單字數量
    cursor.execute("SELECT COUNT(*) FROM words WHERE srs_status = 'need_practice'")  # 查詢需練習單字數
    need_practice_count = cursor.fetchone()[0]  # 取得需練習單字數量
    cursor.execute("SELECT COUNT(*) FROM words WHERE srs_status = 'hard'")  # 查詢困難單字數
    hard_count = cursor.fetchone()[0]  # 取得困難單字數量
    cursor.execute("SELECT SUM(review_count), SUM(correct_count) FROM words")  # 統計總複習次數與總答對次數
    sum_row = cursor.fetchone()  # 讀取統計加總列
    total_reviews = sum_row[0] or 0  # 取得複習總次數（空值時預設為 0）
    total_correct = sum_row[1] or 0  # 取得答對總次數（空值時預設為 0）
    overall_accuracy = round((total_correct / total_reviews * 100), 1) if total_reviews > 0 else 0.0  # 計算累積正確率百分比
    conn.close()  # 關閉資料庫連線
    return {  # 回傳封裝完成的學習統計字典
        "total_words": total_words,  # 總收錄單字數量
        "mastered_count": mastered_count,  # 已掌握單字數量
        "need_practice_count": need_practice_count,  # 需練習單字數量
        "hard_count": hard_count,  # 困難生詞數量
        "total_reviews": total_reviews,  # 總複習題目數
        "total_correct": total_correct,  # 總答對題數
        "overall_accuracy": overall_accuracy  # 整體答對百分比
    }  # 統計字典定義結尾
