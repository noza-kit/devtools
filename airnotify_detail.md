ファイル受信・自動処理デーモン（仮: airnotify）完全仕様書
1. コアコンセプト
airshareの完璧な相棒: iPhoneから airshare 経由でPCのInboxフォルダに投げ込まれたファイルを検知し、整理から通知までを全自動化するバックグラウンドデーモン。

既存モジュールとのシームレスな統合: すでに作成済みの notify モジュールをそのまま呼び出し、通知UIを共通化。さらに pdfcraft や notesearch などの自作ツール群と連携する「糊（グルー）」として機能する。

Inboxのゼロ・メンテナンス: 賢い振り分けと自動お掃除により、ユーザーは手作業でファイルを移動したり、ゴミ箱を空にしたりする手間から完全に解放される。

2. 処理パイプラインと機能詳細
ステップ1: インテリジェントな検知 (Event Watcher)
一時ファイルの除外: .tmp, .part, .crdownload などの転送中・ダウンロード中の拡張子を無視。最終的なファイル書き込みが完了したタイミングでイベントを発火させる。

デバウンス（通知スパム防止）: ファイルが連続で投げ込まれた場合、一定時間（例: 3秒間）イベントをバッファリングし、「5件のファイルを受信」として1つの処理・通知にまとめる。

ステップ2: アクションフック (Pre-Processing)
ファイルの拡張子に応じて、事前に設定した他の自作ツール（CLIコマンド）を裏側で自動実行する。

例: .pdf なら pdfcraft compress をかけてサイズを減らす。

例: .md なら notesearch sync を走らせて即座に検索インデックスへ追加する。

ステップ3: スマート・ルーティング (Routing)
設定ファイル（YAML）のルールに基づき、Inboxに届いたファイルをPC内の適切なディレクトリへ自動移動（整理）させる。

ルール例:

画像 (.png, .jpg, .heic) → ~/Pictures/Airshare/

ドキュメント (.pdf, .docx) → ~/Documents/Airshare/

その他 → ~/Downloads/Airshare_Inbox/ にそのまま残す。

ステップ4: リッチな通知生成 (Notification)
既存の notify モジュールを import してデスクトップ通知を生成する。

内容: 「3件の画像を受信し、Picturesへ移動しました（うち1件は圧縮済み）」といった処理結果のサマリーを表示。

クリッカブル化: 通知をクリックすると、移動先のディレクトリがOSのエクスプローラー（Finder）で自動的に開き、該当ファイルが選択された状態になる。

ステップ5: 自動クリーンアップ (Auto-Cleanup)
常駐デーモンが1日1回（または起動時に）、指定されたInboxフォルダやルーティング先フォルダをスキャンする。

設定された期限（例: 7日間）を過ぎた未アクセスのファイルを自動的に削除（またはOSのゴミ箱へ移動）し、ストレージの圧迫を防ぐ。

3. 設定ファイル (config.yaml) の設計イメージ
ユーザーがPythonコードを書き換えなくても、ルールの追加・変更が柔軟にできる設計とします。

YAML
# airnotify configuration
inbox_dir: "~/Airshare_Inbox"
debounce_seconds: 3

routing:
  pictures:
    extensions: [".jpg", ".png", ".heic"]
    destination: "~/Pictures/Airshare"
  docs:
    extensions: [".pdf", ".md"]
    destination: "~/Documents/Airshare"

hooks:
  ".pdf": "pdfcraft compress {filepath} --replace"
  ".md": "notesearch sync"

cleanup:
  enabled: true
  expire_days: 7
4. CLI インターフェース設計（使用例）
基本的にはバックグラウンドで動き続けますが、CLIからも管理できるようにします。

Bash
# 1. デーモンとしてバックグラウンド起動（OS起動時に自動実行させる想定）
airnotify daemon start

# 2. 現在のデーモンの稼働状況や、過去24時間の受信・処理ログを確認
airnotify status

# 3. 期限切れファイルのクリーンアップを手動で即座に実行
airnotify clean --force