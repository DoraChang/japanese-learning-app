import os  # 導入作業系統標準函式庫以處理檔案儲存路徑
import zlib  # 導入 zlib 壓縮演算法模組以壓縮 PNG 影像點陣資料
import struct  # 導入 struct 模組以二進位方式打包 PNG 區塊標頭與資料
# ---------------------------------------------------------------------------------------------------------------------- # 純 Python 標準庫生成標準 PNG 影像函式
def create_png_icon(filepath: str, size: int) -> None:  # 定義生成指定尺寸 PNG 影像檔案函式
    width = size  # 設定圖片像素寬度
    height = size  # 設定圖片像素高度
    raw_data = bytearray()  # 初始化未壓縮的點陣像素原始位元組陣列
    for y in range(height):  # 逐一走訪每一橫列像素
        raw_data.append(0)  # 每列開頭寫入 PNG 標準濾鏡類型 0（無濾鏡）
        for x in range(width):  # 逐行走訪橫列中的每一個像素點
            dx = x - width / 2  # 計算該像素相對於水平中心點的距離
            dy = y - height / 2  # 計算該像素相對於垂直中心點的距離
            dist = (dx * dx + dy * dy) ** 0.5  # 計算當前像素與中心點的幾何歐幾里得半徑
            radius = width * 0.45  # 設定外圈主要圓形徽章半徑大小
            if dist <= radius:  # 判斷像素若落在圓形徽章內部
                raw_data.extend((79, 70, 229, 255))  # 填入經典日系靛藍色 RGBA (4F, 46, E5, FF)
            else:  # 判斷像素落在圓形外部邊角
                raw_data.extend((248, 250, 252, 0))  # 填入完全透明背景 RGBA
    compressed = zlib.compress(bytes(raw_data), 9)  # 使用最高等級 9 執行 zlib 壓縮
    png_bytes = bytearray(b"\x89PNG\r\n\x1a\n")  # 寫入 PNG 檔案標準開頭 8 位元組魔術簽名
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 封裝 IHDR 影像資訊區塊（RGBA 8位元色深）
    ihdr_crc = struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xffffffff)  # 計算 IHDR 的 CRC32 校驗碼
    png_bytes.extend(struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data + ihdr_crc)  # 組合長度、名稱、資料與校驗碼寫入 IHDR 區塊
    idat_crc = struct.pack(">I", zlib.crc32(b"IDAT" + compressed) & 0xffffffff)  # 計算 IDAT 像素資料區塊的 CRC32 校驗碼
    png_bytes.extend(struct.pack(">I", len(compressed)) + b"IDAT" + compressed + idat_crc)  # 組合寫入 IDAT 區塊
    iend_crc = struct.pack(">I", zlib.crc32(b"IEND") & 0xffffffff)  # 計算 IEND 檔案結束區塊的 CRC32 校驗碼
    png_bytes.extend(struct.pack(">I", 0) + b"IEND" + iend_crc)  # 寫入長度為 0 的 IEND 標誌區塊結束 PNG 結構
    with open(filepath, "wb") as f:  # 以二進位寫入模式開啟目標檔案
        f.write(png_bytes)  # 將組裝完成的 PNG 二進位資料寫入本機檔案
# ---------------------------------------------------------------------------------------------------------------------- # 主程式執行進入點
if __name__ == "__main__":  # 判斷是否由主程式執行
    front_dir = os.path.join(os.path.dirname(__file__), "frontend")  # 解析 frontend 資料夾路徑
    create_png_icon(os.path.join(front_dir, "icon-192.png"), 192)  # 生成 192x192 規格之 PWA 圖示
    create_png_icon(os.path.join(front_dir, "icon-512.png"), 512)  # 生成 512x512 規格之 PWA 圖示
    print("PWA 圖示 icon-192.png 與 icon-512.png 建立成功！")  # 印出圖示生成成功確認訊息
