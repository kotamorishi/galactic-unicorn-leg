# Galactic Unicorn 実現可能性調査

## 結論

**3つの要件すべて実現可能です。** WiFi経由で外部からコマンドを受信し、任意のタイミングで文字表示・図形表示・音声再生を行うことができます。

---

## デバイス概要

| 項目 | 仕様 |
|------|------|
| LED マトリクス | 53 x 11 RGB LED（583ピクセル） |
| コントローラー | Raspberry Pi Pico W（RP2040 デュアルコア Arm Cortex-M0+ 133MHz） |
| RAM | 264KB SRAM（MicroPython使用時は約192KB利用可能） |
| Flash | 2MB QSPI |
| オーディオ | モノラル I2S アンプ + 1Wスピーカー（ピエゾブザーではなく本物のスピーカー） |
| WiFi | Pico W搭載 CYW43439（2.4GHz 802.11n） |
| ボタン | A, B, C, D（ユーザー用）、Sleep、音量Up/Down、輝度Up/Down |
| 光センサー | フォトトランジスタ搭載（12bit ADC） |
| 拡張 | Qw/ST (Qwiic/STEMMA QT) I2Cコネクタ x2 |
| 電源 | Micro-USB + JST バッテリーコネクタ |

## SDK・開発環境

- **MicroPython**（Pimoroniカスタムファームウェア）— 推奨。プリインストール済み
- **C/C++** — `pimoroni-pico` ライブラリ経由で利用可能

主要リポジトリ:
- ライブラリ: https://github.com/pimoroni/pimoroni-pico
- サンプル: https://github.com/pimoroni/unicorn

---

## 要件1: 任意のタイミングで文字を表示

### 判定: 実現可能

`PicoGraphics` ライブラリがテキスト描画APIを提供しています。

### 利用可能なAPI

| API | 説明 |
|-----|------|
| `text(text, x, y, wordwrap, scale, angle, spacing)` | 任意位置に文字列を描画 |
| `character(char, x, y, scale)` | 単一文字を描画 |
| `measure_text(text, scale, spacing)` | 文字列幅をピクセル単位で計測（スクロール用） |
| `set_font(font)` | フォント選択 |
| `set_thickness(n)` | ベクターフォントの線の太さ |

### 利用可能なフォント

- ビットマップ: `bitmap6`, `bitmap8`, `bitmap14_outline`
- ベクター（Hershey）: `sans`, `gothic`, `cursive`, `serif_italic`, `serif`

11ピクセルの高さを考慮すると、`bitmap6` や `bitmap8` が実用的です。一度に表示できる文字数は約6〜8文字程度ですが、スクロール表示で長文にも対応可能です（公式に `scrolling_text.py` サンプルあり）。

### サンプルコード

```python
from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN

gu = GalacticUnicorn()
graphics = PicoGraphics(display=DISPLAY_GALACTIC_UNICORN)

graphics.set_font("bitmap8")
pen = graphics.create_pen(255, 255, 0)  # 黄色
graphics.set_pen(pen)
graphics.text("Hello!", 0, 2, -1, 1)
gu.update(graphics)
```

---

## 要件2: 任意のタイミングで指定された図形を表示

### 判定: 実現可能

`PicoGraphics` が2D描画APIを完備しています。

### 利用可能な描画API

| API | 説明 |
|-----|------|
| `pixel(x, y)` | 単一ピクセル |
| `pixel_span(x, y, length)` | 水平ピクセルスパン |
| `line(x1, y1, x2, y2, [thickness])` | 直線 |
| `circle(x, y, r)` | 塗りつぶし円 |
| `rectangle(x, y, w, h)` | 塗りつぶし矩形 |
| `triangle(x1, y1, x2, y2, x3, y3)` | 塗りつぶし三角形 |
| `polygon([(x1,y1), ...])` | 任意の塗りつぶしポリゴン |
| `clear()` | 画面全体クリア |
| `set_clip(x, y, w, h)` / `remove_clip()` | クリッピング領域 |

### 色指定

- `create_pen(r, g, b)` — RGB指定
- `create_pen_hsv(h, s, v)` — HSV指定（0.0〜1.0）

### 注意事項

- 解像度が53x11と非常に低いため、複雑な図形の表現には限界があります
- 描画後に `gu.update(graphics)` を呼び出してLEDに反映する必要があります
- 画像フォーマット（JPEG/PNG）のネイティブデコードは非対応。手続き的に描画するか、生ピクセルデータに変換する必要があります

---

## 要件3: 任意のタイミングで音を再生

### 判定: 実現可能

搭載されているのはピエゾブザーではなく、**I2Sアンプ駆動の1Wスピーカー**です。Commodore 64のSIDチップをモデルにしたシンセサイザーエンジンが内蔵されています。

### オーディオAPI

| API | 説明 |
|-----|------|
| `gu.play_sample(data)` | 生16bit PCMデータを再生 |
| `gu.synth_channel(channel)` | シンセチャンネル取得 |
| `gu.play_synth()` | シンセ再生開始 |
| `gu.stop_playing()` | 全音声停止 |
| `gu.set_volume(0.0〜1.0)` | 音量設定 |

### チャンネルAPI（各ボイス）

| API | 説明 |
|-----|------|
| `configure(waveforms, frequency, volume, attack, decay, sustain, release, pulse_width)` | ADSR エンベロープ付きで設定 |
| `frequency(freq)` | 周波数設定 |
| `volume(vol)` | 音量設定 |
| `trigger_attack()` / `trigger_release()` | 発音開始/停止 |
| `play_tone(frequency, volume, attack, release)` | 簡易トーン再生 |

波形タイプ: 矩形波、三角波、鋸歯波、ノイズ、サイン波（SIDスタイル）

### サンプルコード

```python
channel = gu.synth_channel(0)
channel.configure(
    waveforms=GalacticUnicorn.WAVEFORM_SQUARE,
    frequency=440,
    volume=0.5,
    attack=0.1,
    decay=0.1,
    sustain=0.8,
    release=0.5
)
gu.set_volume(0.5)
channel.trigger_attack()
gu.play_synth()
```

---

## WiFi経由での制御（「任意のタイミング」の実現方式）

Pico WのWiFiを使い、HTTPサーバーとして動作させることで外部から任意タイミングでコマンドを送信できます。

### 公式で実証済みのアーキテクチャ

公式サンプル `galactic_paint` が以下を実演しています:
- **microdot**（軽量MicroPython Webフレームワーク）でHTTPサーバーを起動
- ブラウザからPico WのIPアドレスに接続
- HTTP リクエストでピクセル描画コマンドを送信
- リアルタイムでLEDマトリクスに反映

また `cheerlights.py` サンプルでは外部API（HTTPクライアント）へのアクセスも実証されています。

### WiFi関連ライブラリ

- `micropython-phew` — WiFi接続ヘルパー
- `microdot` — 軽量Webフレームワーク
- 標準 `network`, `urequests` モジュール

---

## 制約・注意点

| 項目 | 詳細 |
|------|------|
| RAM制約 | MicroPython使用時は約192KB。WiFi + ディスプレイ + オーディオ同時使用でメモリ逼迫の可能性あり |
| 解像度 | 53x11は非常に低解像度。一度に表示できる文字は6〜8文字程度 |
| CPU性能 | 133MHz Cortex-M0+。WiFiサーバー + 描画更新 + 音声を同時実行すると負荷が高い |
| 並行処理 | MicroPythonは基本シングルスレッド。`asyncio` による協調マルチタスクが必要 |
| WiFi | 2.4GHzのみ、Bluetooth非対応 |
| 画像 | JPEG/PNGのネイティブデコード不可 |
| カラー | デフォルトRGB332（256色）。RGB565/888も可能だがメモリ消費増 |
| ストレージ | 2MB Flashをファームウェアとユーザーコードで共有 |

---

## 推奨アーキテクチャ

```
[外部クライアント (PC/スマホ)]
        |
        | HTTP リクエスト (WiFi)
        v
[Galactic Unicorn (Pico W)]
    ├── microdot HTTPサーバー (コマンド受信)
    ├── PicoGraphics (文字・図形描画)
    └── シンセエンジン (音声再生)
```

`asyncio` を使って以下を協調的に実行:
1. HTTPサーバーでコマンド待受
2. コマンドに応じて文字表示・図形描画・音声再生を実行

---

## 参考リンク

- [Pimoroni 製品ページ](https://shop.pimoroni.com/products/space-unicorns?variant=40842033561683)
- [Galactic Unicorn MicroPython API](https://github.com/pimoroni/pimoroni-pico/blob/main/micropython/modules/galactic_unicorn/README.md)
- [PicoGraphics API](https://github.com/pimoroni/pimoroni-pico/blob/main/micropython/modules/picographics/README.md)
- [サンプルコード集](https://github.com/pimoroni/unicorn/tree/main/examples/galactic_unicorn)
