# claude-bridge

Discord経由でClaude Codeを遠隔操作する常駐Bot。指定チャンネルに指示を投稿すると
`claude -p` をヘッドレス実行し、進捗・結果・diffをDiscordに返信する。PCの電源が
入っている間、常駐プロセスとして動作する。

## できること

- 指定チャンネル(`CLAUDE_BRIDGE_CHANNEL_ID`)への投稿を指示として受け取り、
  `claude -p` を実行して結果を返信する
- 送信者制限(`CLAUDE_BRIDGE_ALLOWED_USER_IDS`)・プロジェクトパスのホワイト
  リスト化(`bridge.yaml`)・実行タイムアウト・破壊的操作の事前確認
  (`yes` 返信待ち)による安全策
- `stop` 返信での実行中タスクの中断、複数指示のキュー処理(同時実行なし)
- `終了`/`起動` 返信での指示受け付けの一時停止/再開(プロセス自体は常駐した
  まま。詳細は下記「Discordからの起動/終了について」)
- プロジェクトごとのセッション継続(`claude -p --resume`)で文脈を維持した
  追加指示
- 長時間タスクの途中経過通知(編集中/実行中のツール呼び出しをstream-json
  から抽出)
- 変更内容の `diff`(既定)/`summary` 表示切り替え(メッセージ内 `mode: ...`
  またはconfigのデフォルト値)
- `claude-bridge status`/`ping` での稼働状況確認・ヘルスチェック、任意の
  定期ハートビート投稿
- `usage`(または `使用量`/`cost`/`コスト`)返信、または `claude-bridge usage`
  での概算コスト・トークン使用量の確認(全期間/直近7日間/プロジェクト別)。
  各実行完了時にも概算コストを自動投稿
- 指示・結果・使用モード・概算コスト/トークン数などの実行履歴をSQLiteに記録

## 使い方

Discordの指示メッセージの例:

```
project: hobby
mode: summary
READMEにインストール手順を追記して
```

`project:`/`mode:` 行は省略可(それぞれ `bridge.yaml` の
`default_project`/`default_mode` が使われる)。破壊的操作と判定された指示は
実行前に確認を求められるので、`yes` と返信する。実行中に `stop` と返信する
と中断できる。

## Discordからの起動/終了について

`終了`(または `shutdown`/`exit`)と送信すると、実行中のタスクを中断した上で
指示の受け付けを停止する。`起動`(または `start`/`resume`)で再開する。

**これはOSプロセス自体のkill/起動ではない**: claude-bridgeのプロセスが
完全に落ちている間はDiscordのメッセージを受け取る仕組み自体が存在しない
(Botが起動していない = 「起動して」というメッセージすら受け取れない、と
いう鶏と卵の問題があるため)。そのため実体は「指示の受け付けON/OFF」の
切り替えで、Botプロセス自体は常時起動させておく設計になっている
(`claude-bridge start` をWindowsのタスクスケジューラ等でPCログオン時に
自動起動しておくことを推奨)。待機中(一時停止中含む)のプロセスは
Discordとの接続を保持しているだけで、メモリ使用量はごく小さい
(`claude -p` を実際に実行している間だけ別途プロセスが立ち上がり、完了後
は終了する)。

## セットアップ

### 1. Discordアプリケーション + Bot

1. [Discord Developer Portal](https://discord.com/developers/applications) で
   claude-bridge専用のアプリケーションを新規作成 → **Bot** タブ → Add Bot。
   (yt-twitch-digestのBotとの使い回しは非推奨: 権限セットや障害影響範囲が
   混ざるため)
2. **Privileged Gateway Intents** で **Message Content Intent** を有効化。
3. Botトークンをコピー → `CLAUDE_BRIDGE_BOT_TOKEN`。
4. **OAuth2 → URL Generator** でスコープ `bot`、権限は **View Channel** /
   **Send Messages** / **Read Message History** / **Attach Files** のみ
   (必要最小限)。生成されたURLでBotをサーバーに招待する。
5. Discordの開発者モードを有効化し、指示を受け付けるチャンネルを右クリック
   → **Copy Channel ID** → `CLAUDE_BRIDGE_CHANNEL_ID`。
6. 指示を送るユーザー本人のIDを同様にコピー → `CLAUDE_BRIDGE_ALLOWED_USER_IDS`
   (複数はカンマ区切り)。

### 2. `bridge.yaml`

[`bridge.example.yaml`](bridge.example.yaml) を `bridge.yaml` にコピーして
編集する。実行を許可するプロジェクトパスはここに登録したものだけ
(ホワイトリスト)。

```yaml
projects:
  - alias: hobby
    path: "C:/Users/AlexD/Documents/hobby"
default_project: hobby
default_mode: diff
timeout_seconds: 1800
```

任意のキーは `CLAUDE_BRIDGE_<KEY>` 環境変数で上書き可能(`confload` 経由。
例: `CLAUDE_BRIDGE_TIMEOUT_SECONDS=900`)。

### 3. インストール・起動

`claude-bridge` ディレクトリに `cd` してから実行する(`-e .` はカレント
ディレクトリをインストール対象にするため、リポジトリのルートで実行すると
"does not appear to be a Python project" エラーになる):

```bash
cd claude-bridge
pip install -e ../reqretry -e ../confload -e ../notify -e .

export CLAUDE_BRIDGE_BOT_TOKEN=...
export CLAUDE_BRIDGE_CHANNEL_ID=...
export CLAUDE_BRIDGE_ALLOWED_USER_IDS=111111111111111111

claude-bridge ping     # 接続確認(トークン/チャンネルIDの検証のみ、常駐はしない)
claude-bridge start --config bridge.yaml
```

別ターミナルから:

```bash
claude-bridge status   # 実行中/待機中、キュー件数
```

## セキュリティ上の注意

- **`--permission-mode bypassPermissions` で実行する**: Discord経由のヘッド
  レス実行にはツール権限プロンプトに答えるTTYが存在しないため、権限確認を
  有効にしたままだと全ての実行がタイムアウトまでハングする。したがって
  Claude Codeの個々のツール呼び出し(ファイル編集・コマンド実行)は無条件で
  許可される。これを補う制御は次の4層のみ:
  1. 送信者制限(`CLAUDE_BRIDGE_ALLOWED_USER_IDS`)
  2. チャンネル制限(`CLAUDE_BRIDGE_CHANNEL_ID`)
  3. プロジェクトパスのホワイトリスト(`bridge.yaml`)
  4. 指示テキストに対する破壊的操作キーワードの事前チェック(`guard.py`。
     `git push --force`/`rm -rf`/`DROP TABLE` 等。**指示文言に対する
     ヒューリスティックであり、Claudeが実際に実行するコマンドを検査する
     ものではない**。未知の危険操作やパターンに一致しない表現は素通りする)
  - このBotのトークン・チャンネルは信頼できる用途以外で共有しないこと。
- **プロジェクトの追加は `bridge.yaml` を編集した本人のみ**行える設計。
  Discordメッセージから任意パスを指定することはできない
  (登録済みエイリアスのみ選択可)。

## 実装メモ・既存資産の再利用

- Discord接続は [discord.py](https://discordpy.readthedocs.io/)
  のGatewayクライアント(`discord_bot.py`)による新規実装。
  [`ytdigest`](../ytdigest/)の `discord_client.py` はGitHub Actionsからの
  日次バッチ実行を前提としたREST APIポーリング(WebSocket接続なし)で、
  「常時起動+即時反応」という今回の要件とは動作モデルが異なるため接続層は
  新規実装したが、Bot token認証ヘッダの形式やメッセージ2000字制限の分割
  ロジック(`diff_view.py`)は同じ考え方を踏襲している。`claude-bridge ping`
  は逆にGateway接続を張らずREST APIを直接叩くため、ytdigestの
  `discord_client.py` と同じ `reqretry` + Bot token ヘッダのパターンを
  そのまま使っている(`discord_rest.py`)。
- [`notify`](../notify/) の `notify()` はDiscordへのメイン通信路としてでは
  なく、Bot起動・破壊的操作の確認待ち・タイムアウト/失敗時にデスクトップ
  通知を飛ばす補助チャンネルとして利用している。
- [`confload`](../confload/) を `bridge.yaml` の読み込みにそのまま使用。
- `runner.py`(`claude -p` のasyncio subprocess実行)・`queue_worker.py`
  (直列実行キュー)・`history_db.py`(SQLite履歴)は今回の要件専用の新規
  実装。

## `claude -p` 呼び出しについて

セッション継続は `--session-id <uuid>` で開始し、以降の指示は
`--resume <uuid>` で同じプロジェクトの会話に追記する。進捗通知は
`--output-format stream-json --verbose` の出力を1行ずつパースし、
`tool_use` イベント(Edit/Write/Bash等)から「編集中: foo.py」のような
ラベルを組み立てて表示している(`progress_interval_seconds` で頻度を制限)。
最後の `result` イベントに含まれる `total_cost_usd`/`usage`(トークン数)を
拾って `usage` コマンドの集計に使っている。

これらのCLIフラグ・出力フィールドは手元で確認したClaude Codeの動作に基づく
もので、`claude --help` で最新のフラグ名を確認してから使うこと。バージョン
により変わる可能性がある(`total_cost_usd`/`usage` を含まないバージョンでは
コストは `null` のまま記録され、`usage` コマンドの合計には含まれない)。

## データベース

`--db`(既定 `~/.claude-bridge/history.db`)にSQLiteで記録:

- **runs** — 指示・使用モード・ステータス(running/completed/failed/
  timeout/cancelled)・結果概要・使用セッションID・概算コスト
  (`total_cost_usd`)・トークン数(`input_tokens`/`output_tokens`/
  `cache_creation_input_tokens`/`cache_read_input_tokens`)
- **sessions** — プロジェクトエイリアスごとの直近のClaudeセッションID
  (次回の `--resume` に使用)

コスト/トークン列は初回リリース後に追加されたもので、既存の
`history.db` に対しては起動時に自動でマイグレーション(`ALTER TABLE`)
される。

## 動作確認について

Discordの実トークンを用いた実機接続(Gateway接続・実際の `claude` CLI
呼び出し)はこの環境では検証していない。単体テスト(`pytest`)では、
メッセージルーティングの判定ロジック(`routing.py`)・破壊的操作検出
(`guard.py`)・diff/summary整形(`diff_view.py`)・SQLite履歴
(`history_db.py`)・キュー処理(`queue_worker.py`)・`claude -p`
実行ラッパー(`runner.py`、フェイクの実行ファイルでタイムアウト/中断/
stream-json解析を検証)をカバーしている。`discord_bot.py`
(discord.py Gatewayクライアントそのもの)はDiscordとの実接続が必要な
薄い配線部分のため、ユニットテスト対象外(実際のBotトークンでの
`claude-bridge ping`/`start` による動作確認を推奨)。
