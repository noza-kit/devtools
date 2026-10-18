# snapclip — 実装レポート

## ステータス: 完了(保留中の質問なし)

snapclip_detail.mdのモジュールA(Snap)・モジュールB(Clip)、
デーモンモード/CLIモード両方を実装しました。

## 完了した機能

### モジュールA: 高度なキャプチャ機能 (Snap)
- **スタック(キュー)キャプチャモード** — Alt+Shift+Sで撮影する度に画像を
  保存し、生成したMarkdown/LaTeX構文を共有FIFOキューにpush
- **Markdown/LaTeX構文の自動生成** — `snapclip config --mode latex/markdown`
  で切替。撮影と同時にファイル保存+構文生成
- **自動結合スクロールキャプチャ** — ホットキー押しっぱなし→マウスドラッグで
  領域選択→領域内スクロールでフレーム取得→キーを離して確定、という
  ご指定の設計で実装(`ScrollCaptureSession`状態機械)。OpenCVの
  テンプレートマッチングで前フレームの下端ストリップを次フレーム内から
  検出し、重複しない行だけを連結する自前の縦方向スティッチャーを実装
  (`cv2.Stitcher`のような汎用パノラマ合成ではなく、UI縦スクロールに特化した
  1次元オフセット探索)
- **URL指定フルページキャプチャ** — Playwright(headless Chromium)、
  `[web]` extra

### モジュールB: クリップボード履歴・拡張管理機能 (Clip)
- **FIFO連続ペースト** — Alt+Shift+Vで古い順に1件ずつペースト
  (`--paste-mode all`で一括ペーストも選択可、spec記載の「一気に」との両対応)
- **CLI/TUIインクリメンタル検索** — `snapclip history`でfzf風の
  インクリメンタル検索TUI(msvcrt+rich実装)。選択でクリップボードに再セット

### 設計上の重要な統合ポイント
モジュールAの「スタックキュー」とモジュールBの「FIFOペースト」は、
仕様書を読み解くと同一のキューを指していると判断し、`PasteQueue`という
単一のFIFOに統合しました。スクリーンショット撮影で生成された構文テキストと、
通常のCtrl+Cでコピーされたテキスト/画像が同じキューに積まれ、
Alt+Shift+Vで古い順に取り出されます(README「The shared paste queue」に
具体例付きで説明を記載)。

## テスト

`pytest snapclip/tests` — **78件全てパス**。

**実機で実際に動作確認できた部分(モック不要)**:
- Windowsクリップボードへの実際のテキスト/画像の読み書き
  (`pywin32`経由、`test_win32_backend_*`)— この開発環境で実際に動作することを
  確認済み
- `keyboard`/`mouse`ライブラリでの実際のグローバルフック登録・解除
  (`test_register_hooks_with_real_keyboard_and_mouse_modules_does_not_crash`)
- OpenCVスティッチングロジック — 合成した縦長画像から重複ウィンドウを
  切り出して再構成し、ピクセル完全一致することを検証済み

**モック化した部分(動作未実機確認、summaryへの記載指示に基づく)**:
- **ホットキーの実発火**: `keyboard.add_hotkey()`でホットキーを登録し
  `keyboard.send()`で同じキー入力をシミュレートしても、この開発環境では
  コールバックが確実にクロス発火しませんでした(サンドボックス/非対話
  セッション特有の制約と推測されます)。フック自体の登録・解除は実際に
  動作確認済みですが、「実際にキーを押したときにデーモンが反応するか」は
  実機での手動確認が必要です。
- **画面キャプチャ(`mss`)**: 実際のスクリーンショット取得は
  `ScreenCapture`プロトコルの`FakeScreenCapture`を注入してテストして
  います(合成画像を返すダミー)。ロジック(ファイル保存・キュー投入・
  ユニーク命名等)は実際に検証済みですが、「本物の画面が正しく
  キャプチャされるか」自体は未検証です。
- **Playwright Web capture**: ブラウザバイナリのダウンロードが必要
  (`playwright install chromium`)なため、CLIコマンドのテストでは
  `webcapture.capture_full_page`をモック化しています。
- **`snapclip history`のTUIループ本体**: 対話的なキー入力ループ
  (`msvcrt.getwch()`)自体は自動テスト対象外です。フィルタリングロジック
  (`filter_entries`)は純粋関数として直接テストしています。

## 発生した問題・設計判断

1. **`mouse`ライブラリに`on_wheel`が存在しない**: 実装当初
   `mouse_module.on_wheel(callback)`を想定していましたが、実際のAPIには
   存在せず、汎用の`mouse.hook(callback)`+`WheelEvent`型フィルタリングに
   修正しました。
2. **`ScrollCaptureSession`のタイマー呼び出し回数**: 当初`on_scroll()`内で
   デバウンス判定用と実際のキャプチャ記録用で`now_fn()`を2回呼んでいましたが、
   1回の呼び出し結果を使い回すよう修正(わずかながらより正確、かつ
   テストしやすい設計になりました)。
3. **`HistoryStore`のデフォルト引数バグ**: `db_path: Path = DEFAULT_DB_PATH`
   という書き方だとモジュールロード時に値が固定されてしまい、テストで
   `monkeypatch`しても反映されない不具合がありました。`config.py`の
   `load_settings`と同じ「関数本体でデフォルト値を解決する」パターンに
   修正しています。
4. **キューの統合設計**: 上記の通り、モジュールA/Bの「キュー」を単一の
   `PasteQueue`として統合しました。仕様書の記述(モジュールAは撮影の蓄積、
   モジュールBはコピーの蓄積、という書き分け)から見ると2つの別キューとも
   解釈できますが、「Alt+Shift+Sで撮ってからAlt+Shift+Vで戻す」動作と
   「Ctrl+Cを連続してAlt+Shift+Vで戻す」動作が同じインターフェース
   (Alt+Shift+V/1つのペースト操作)で説明されている以上、実装上も
   同一キューにするのが自然と判断しました。異なる解釈だった場合は
   ご指摘ください。

## 保留中の質問

なし。

## 次に着手すべき作業

なし(snapclipは完了)。次は slidecraft の実装に進みます。
