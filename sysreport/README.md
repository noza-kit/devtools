# sysreport

PC起動時のシステム状態チェック + 通知ツール。ストレージ空き容量
([`diskcheck`](../diskcheck)の`human_size`フォーマットを再利用)、バッテリー残量・
充電状態、CPU/メモリ使用率のスナップショットを1行のレポートにまとめ、
[`notify`](../notify)経由でデスクトップ通知/Slack/Discord/LINEに送信します。
Windowsのタスクスケジューラにログオン時自動実行のタスクを登録する機能も
持っています。

## 要件

- コマンド `sysreport run` で状態チェック+通知を1回実行する。
- チェック内容:
  - 主要ドライブの空き容量(`diskcheck`と同じ`human_size`フォーマットで表示)
  - バッテリー残量・充電状態(`psutil`。バッテリー非搭載機では項目自体を省略)
  - CPU使用率・メモリ使用率のスナップショット
- レポートは絵文字付きの1行テキストに整形し、`notify()`で送信する。
- 各項目に閾値を設定でき、`--highlight-warnings`を付けたときだけ閾値を
  下回った(または上回った)項目に警告マークを付ける(デフォルトはマーク無し)。
- `sysreport setup-autostart` でWindowsのタスクスケジューラに、ログオン時に
  `sysreport run`を自動実行するタスクを登録できる(`--remove`で削除)。

## Install

```bash
cd sysreport
pip install -e ../reqretry   # notify の依存
pip install -e ../confload
pip install -e ../diskcheck
pip install -e ../notify
pip install -e ".[dev]"
```

From GitHub (this package lives in the `sysreport/` subdirectory of the repo):

```bash
pip install "git+https://github.com/noza-kit/devtools.git#subdirectory=sysreport"
```

## Usage

### `sysreport run` — チェック + 通知

```bash
sysreport run
sysreport run --channels desktop,discord
sysreport run --highlight-warnings
sysreport run --json --dry-run
sysreport run --storage-min-percent 15 --cpu-max-percent 80 --highlight-warnings
sysreport run --config thresholds.yaml
```

主要ドライブの空き容量、バッテリー残量・充電状態、CPU使用率、メモリ使用率を
取得し、1行のレポートに整形して`notify()`で送信します。

```
💾 C:\ 空き容量: 45.00 GB (18%) / 🔋 バッテリー: 80% (充電中) / 🖥️ CPU: 12% / 🧠 メモリ: 55%
```

閾値を下回った(または上回った)項目には、`--highlight-warnings`を付けたときだけ
末尾に`⚠️`が付きます:

```
💾 C:\ 空き容量: 4.20 GB (4%) ⚠️ / 🔋 バッテリー: 15% (バッテリー駆動) ⚠️ / 🖥️ CPU: 12% / 🧠 メモリ: 55%
```

### `sysreport setup-autostart` — Windows起動時の自動実行

```bash
sysreport setup-autostart
sysreport setup-autostart --channels desktop,discord --highlight-warnings
sysreport setup-autostart --task-name SysReport --config thresholds.yaml
sysreport setup-autostart --remove
```

タスクスケジューラに `SysReport`(デフォルト名)という名前のタスクを登録し、
**ログオン時**に `sysreport run` を実行します。`--channels` / `--config` /
`--highlight-warnings` は、登録するタスクが実行する `sysreport run` に
そのまま引き継がれます。`--remove` で登録したタスクを削除します。

## 仕様

### コマンド一覧

| コマンド | 説明 |
| --- | --- |
| `sysreport run` | チェックを1回実行し、レポートを表示 + `notify()`で送信 |
| `sysreport setup-autostart` | ログオン時自動実行タスクの登録・削除 |

#### `sysreport run` オプション

| オプション | デフォルト | 説明 |
| --- | --- | --- |
| `--channels` | `desktop` | `notify`に渡すチャンネル名(カンマ区切り。`desktop`/`slack`/`discord`/`line`) |
| `--config` | なし | 閾値オーバーライド用のYAML/JSONファイル(`confload`経由) |
| `--storage-min-percent` | なし(未指定なら閾値ファイル/デフォルト値を使用) | ストレージ空き容量%の下限しきい値を上書き |
| `--battery-min-percent` | なし | バッテリー残量%の下限しきい値を上書き |
| `--cpu-max-percent` | なし | CPU使用率%の上限しきい値を上書き |
| `--memory-max-percent` | なし | メモリ使用率%の上限しきい値を上書き |
| `--highlight-warnings` / `-w` | `False` | 閾値を超えた項目に`⚠️`マークを付ける |
| `--json` | `False` | レポートをJSONで出力(`--dry-run`と併用可) |
| `--dry-run` | `False` | レポートを表示するだけで通知を送信しない |
| `--cpu-interval` | `0.5`(秒) | CPU使用率サンプリング区間。長いほど正確だがその分ブロックする |

#### `sysreport setup-autostart` オプション

| オプション | デフォルト | 説明 |
| --- | --- | --- |
| `--task-name` | `SysReport` | タスクスケジューラに登録するタスク名 |
| `--channels` | `desktop` | 登録するタスクが実行する`sysreport run`に渡すチャンネル |
| `--config` | なし | 登録するタスクが実行する`sysreport run`に渡す閾値ファイル |
| `--highlight-warnings` | `False` | 登録するタスクの`sysreport run`に`--highlight-warnings`を付ける |
| `--remove` | `False` | タスクを登録する代わりに削除する |

### チェック項目の仕様

| 項目 | 取得方法 | 備考 |
| --- | --- | --- |
| ストレージ | `psutil.disk_partitions(all=False)` で列挙 → `psutil.disk_usage(mountpoint)` | `fstype`が空(CD-ROM等、メディア無し)のエントリはスキップ。複数ドライブがあれば全て1行ずつレポートに含まれる |
| バッテリー | `psutil.sensors_battery()` | `None`(バッテリー非搭載機、多くのデスクトップ)の場合はレポートから`🔋`セクションごと省略される |
| CPU | `psutil.cpu_percent(interval=cpu_interval)` | `interval`秒だけブロックして計測(デフォルト0.5秒) |
| メモリ | `psutil.virtual_memory().percent` | 物理メモリの使用率 |

### レポートフォーマット

各項目を` / `区切りで連結した1行のテキスト。

| 絵文字 | 項目 | 表示内容 |
| --- | --- | --- |
| 💾 | ストレージ(ドライブごとに1セグメント) | `<マウントポイント> 空き容量: <human_size> (<空き%>%)` |
| 🔋 | バッテリー(非搭載時は省略) | `バッテリー: <残量%>% (<充電中/バッテリー駆動>)` |
| 🖥️ | CPU | `CPU: <使用率%>%` |
| 🧠 | メモリ | `メモリ: <使用率%>%` |

`--highlight-warnings`指定時、各セグメントの末尾に条件を満たすと` ⚠️`が付く
(条件は下記「閾値」を参照)。

### JSON出力スキーマ(`--json`)

```json
{
  "drives": [
    {"mountpoint": "C:\\", "free": 20000000000, "free_human": "18.63 GB", "total": 100000000000, "free_percent": 20.0, "warn": false}
  ],
  "cpu": {"percent": 12.0, "warn": false},
  "memory": {"percent": 55.0, "warn": false},
  "battery": {"percent": 80.0, "plugged": true, "warn": false}
}
```

バッテリー非搭載機では `"battery": null` になります。各項目の`warn`は
「閾値の条件」に基づき常に計算されますが、`--highlight-warnings`はテキスト
出力(`⚠️`マーク)にのみ影響し、JSON出力の`warn`フラグ自体には影響しません。

### 閾値

| フィールド | デフォルト | 警告になる条件 |
| --- | --- | --- |
| `storage_min_free_percent` | `10.0` | ドライブの空き容量% ≦ 閾値 |
| `battery_min_percent` | `20.0` | 未充電(`plugged=False`)かつバッテリー残量% ≦ 閾値。充電中は警告にならない |
| `cpu_max_percent` | `90.0` | CPU使用率% ≧ 閾値 |
| `memory_max_percent` | `90.0` | メモリ使用率% ≧ 閾値 |

適用優先順位: **CLIオプション(`--storage-min-percent`等)** > **`--config`ファイル**
> **デフォルト値**。`--config`ファイルは4フィールドのうち一部だけ指定しても
残りはデフォルト値のままになります:

```yaml
# thresholds.yaml
storage_min_free_percent: 15
battery_min_percent: 25
cpu_max_percent: 80
memory_max_percent: 80
```

### 自動起動タスクの仕様

- `sysreport setup-autostart` は内部で以下を実行します:

  ```
  schtasks /create /sc ONLOGON /tn <task-name> /tr "<sysreportコマンド> run [options]" /rl LIMITED /f
  ```

  - トリガーは`ONLOGON`(ログオン時)。`ONSTART`(PC起動時、SYSTEMアカウント)
    ではなく`ONLOGON`にしているのは、デスクトップ通知の表示にはユーザーの
    ログインセッションが必要なためです。
  - `/rl LIMITED` で管理者権限なしのユーザー権限でタスクを実行します。
  - `/f` で同名タスクがあれば上書き登録します(再実行しても安全)。
  - 実行コマンドは `Scripts/sysreport.exe`(pip installed console script)が
    見つかればそれを、無ければ`<python.exe> -m sysreport.cli`を使います。
- `sysreport setup-autostart --remove` は `schtasks /delete /tn <task-name> /f`
  を実行します。タスクが存在しない場合はエラーにせず正常終了します。
- Windows専用機能です(`schtasks`コマンドに依存)。

### 終了コード

| コード | 意味 |
| --- | --- |
| `0` | 成功(通知チャンネルの一部が失敗しても`0`。標準エラー相当のメッセージが黄色で表示される) |
| `1` | `--config`ファイルが存在しない/不正、または`schtasks`の実行に失敗 |

### 制限事項

- `sysreport setup-autostart`はWindows専用(`schtasks`)。
- バッテリー非搭載のデスクトップでは`🔋`セクションがレポートに含まれません
  (`psutil.sensors_battery()`が`None`を返す環境全般)。
- `notify()`のチャンネル送信失敗(Webhook未設定など)は`sysreport run`を
  失敗させません。失敗したチャンネル名を警告として表示するのみです。

## Development

```bash
pip install -e ../reqretry -e ../confload -e ../diskcheck -e ../notify
pip install -e ".[dev]"
pytest
```

Tests monkeypatch `psutil` (CPU/メモリ/バッテリー/ディスク) and
`subprocess.run` (schtasks), so no real hardware state or scheduled tasks are
touched.
