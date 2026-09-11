# ESP32 Clock Feed

這個專案每小時由 GitHub Actions 更新一次，並透過 GitHub Pages 提供 ESP32 可直接讀取的固定檔案：

- `public/today.jpg`：當天照片，預設為 240 × 140 的 baseline JPEG
- `public/today.json`：台北目前溫度、當日日落時間、每日短句與圖片資訊

沒有照片時也會先產生一張提示用圖片，所以可先完成部署，再慢慢加入照片。不包含 Instagram 抓圖功能。

## 固定公開網址

GitHub Pages 啟用後，ESP32 請固定讀取：

- JSON：<https://augustp2k.github.io/esp32-clock/today.json>
- JPEG：<https://augustp2k.github.io/esp32-clock/today.jpg>
- 人眼預覽頁：<https://augustp2k.github.io/esp32-clock/>

## 第一次啟用

1. 進入 repo 的 **Settings → Pages**。
2. 在 **Build and deployment** 的 **Source** 選擇 **GitHub Actions**。
3. 進入 **Actions**，開啟 `Update ESP32 clock feed`。
4. 按 **Run workflow** 執行一次；完成後 Pages 網址通常需要一兩分鐘才會可用。

如果 Actions 頁面要求啟用工作流程，先按下同意啟用。此 workflow 需要 `contents: write` 來把產生的 `today.jpg` 與 `today.json` 存回 repo，並需要 `pages: write` 來部署。

## 上傳或更換照片

1. 打開 [`images/`](images/) 資料夾。
2. 按 **Add file → Upload files**，上傳 `.jpg`、`.jpeg`、`.png`、`.webp` 或 `.bmp`。
3. Commit 到 `main`。

照片依檔名排序，並按照台北日期每天輪替一張。選到的照片會以中央為基準裁切，填滿 `config.json` 指定尺寸；原始照片不會被修改。建議不要上傳含私人資訊的照片，因為此 repo 與 Pages 都是公開的。

## 修改每日英文短句

直接編輯 [`quotes.txt`](quotes.txt)，每行放一句。空白行與以 `#` 開頭的行會忽略。短句依台北日期每天輪替。

## 修改地點與圖片尺寸

編輯 [`config.json`](config.json)：

```json
{
  "latitude": 25.033,
  "longitude": 121.5654,
  "timezone": "Asia/Taipei",
  "image_width": 240,
  "image_height": 140,
  "jpeg_quality": 85
}
```

預設座標是 Taipei 101 一帶。`timezone` 必須是有效的 IANA 時區名稱。

## `today.json` 格式

```json
{
  "date": "2026-09-11",
  "updated_at": "2026-09-11T12:17:00+08:00",
  "timezone": "Asia/Taipei",
  "temperature_c": 31.2,
  "sunset": "18:03",
  "quote": "Small steps still move you forward.",
  "image": "today.jpg",
  "image_source": "my-photo.jpg",
  "image_width": 240,
  "image_height": 140,
  "weather_observed_at": "2026-09-11T12:15",
  "weather_ok": true
}
```

若 Open-Meteo 暫時無法連線，workflow 仍會部署圖片與短句，並保留上一次成功取得的溫度及日落時間；`weather_ok` 會是 `false`。

## 更新時機

- 每小時第 17 分執行一次（GitHub 排程時間可能有少量延遲）
- 上傳照片、修改短句、設定或程式時立即執行
- 可隨時在 Actions 頁面按 **Run workflow** 手動執行

天氣資料來自 [Open-Meteo](https://open-meteo.com/)；`daily=sunset` 會依 `config.json` 的時區回傳當地日落時間。

