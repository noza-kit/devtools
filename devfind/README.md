# devfind

`fd` / `ripgrep` / `fzf` を組み合わせたファイル検索ラッパー。「こんな内容か
タイトルのファイルがあった気がする」を、ファイル名一致・内容一致の両方から
横断的に素早く探すための CLI。検索エンジン自体は自作せず、外部コマンドを
そのまま呼び出す薄いラッパーになっている。

## 目次

- [必須の外部コマンド](#必須の外部コマンド)
- [Install](#install)
- [使い方](#使い方)
- [動作仕様](#動作仕様)
- [設定ファイル仕様](#設定ファイル仕様)
- [モジュール構成](#モジュール構成)
- [Development](#development)

## 必須の外部コマンド

`fd` / `ripgrep`(`rg`) / `fzf` はこのパッケージの依存関係には含まれていない
(検索エンジン自体を自作しない方針のため)。事前に別途インストールし、PATH
が通っている必要がある。

| コマンド | 役割 | 必須/任意 | インストール例 |
| --- | --- | --- | --- |
| [`fd`](https://github.com/sharkdp/fd) | ファイル名検索 | 必須 | `winget install sharkdp.fd` / `choco install fd` / `scoop install fd` / `brew install fd` / `apt install fd-find` |
| [`ripgrep`](https://github.com/BurntSushi/ripgrep) (`rg`) | ファイル内容検索 | 必須 | `winget install BurntSushi.ripgrep.MSVC` / `choco install ripgrep` / `scoop install ripgrep` / `brew install ripgrep` / `apt install ripgrep` |
| [`fzf`](https://github.com/junegunn/fzf) | 検索結果の選択UI | 必須 | `winget install junegunn.fzf` / `choco install fzf` / `scoop install fzf` / `brew install fzf` / `apt install fzf` |
| [`bat`](https://github.com/sharkdp/bat) | プレビュー表示のシンタックスハイライト | 任意 | `winget install sharkdp.bat` / `choco install bat` / `scoop install bat` / `brew install bat` / `apt install bat` |

`bat` は無くても動作する(プレビューが `cat`/Windowsでは `type` にフォール
バックする)が、`fd` / `rg` / `fzf` はいずれか欠けていると検索を始める前に
エラーで停止し、インストール手順を表示する(詳細は
[エラーハンドリング](#エラーハンドリング未インストール時)を参照)。

## Install

```bash
cd devfind
pip install -e ".[dev]"
```

From GitHub (this package lives in the `devfind/` subdirectory of the repo):

```bash
pip install "git+https://github.com/noza-kit/devtools.git#subdirectory=devfind"
```

`confload` は同リポジトリ内のローカルパッケージなので、devfind単体を別環境
に入れる場合は先に `pip install "git+https://...#subdirectory=confload"` も
必要。

## 使い方

```bash
devfind <キーワード>
```

例:

```bash
devfind 見積書
devfind invoice --config ./devfind.yaml
devfind 見積書 | code -        # 選択したファイルをエディタで開く
```

### オプション

| オプション | 説明 |
| --- | --- |
| `keyword` (位置引数, 必須) | 検索キーワード。ファイル名・内容の両方に適用される |
| `--config PATH` | 設定ファイルのパスを明示する。省略時は `~/.devfind/config.yaml` を自動的に探し、それも無ければ組み込みのデフォルト値を使う。明示したのにファイルが存在しない場合はエラーになる |

### 出力

選択したファイルの実パス(`[NAME]`/`[CONTENT]` プレフィックスは除去済み)を
標準出力に1行だけ書き込む。ステータス表示・エラーメッセージ・プロンプトの
類は標準出力を汚さないよう、すべて標準エラー出力に出す。`| code -` や
`| xargs` などパイプで実パスをそのまま渡せる。

## 動作仕様

`devfind <キーワード>` 実行時の内部フローは以下の通り。

```
1. 外部コマンド(fd/rg/fzf)の存在チェック
      │  いずれか欠けていれば、この時点で中断してインストール手順を表示
2. 設定ファイルの読み込み(target_dirs / exclude)
3. fd と rg を並行実行(ThreadPoolExecutor, 2並列)
      ├─ fd  --type f --exclude <pattern>... <keyword> <target_dirs...>
      └─ rg  --files-with-matches --glob '!<pattern>'... <keyword> <target_dirs...>
4. 結果をマージ (グループ分け + 重複除去)
      ├─ fd の結果          → 先頭に [NAME]   として並べる
      └─ rg の結果のうち、   → 続けて [CONTENT] として並べる
         fd と重複しないもの
5. マージ済みリストを fzf に渡す (--no-sort で [NAME] 優先順を維持)
      └─ --preview で選択中の行を bat(無ければ cat/type)表示
6. 選択された行からラベルを除去し、実パスを標準出力
```

### マッチング方法

- `fd`/`rg` とも既定のスマートケース(キーワードに大文字が含まれない限り
  大文字小文字を区別しない)・正規表現マッチで動作する。特別なフラグは
  付けていないので、`fd`/`rg` を単体で使うときと同じ感覚で正規表現も使える。
- 隠しファイル・隠しディレクトリ(`.` で始まるもの)は `fd`/`rg` の既定動作
  通り検索対象外。`.git` などを `exclude` に含めているのは、`--hidden` を
  付けて使うケースや、隠しディレクトリでないが除外したい場合への備え。
- `fd` は `--type f` でファイルのみを対象にし、ディレクトリは結果に含めない。

### グループ分け・重複除去のルール

- 実装は [`search.py`](src/devfind/search.py) の `merge_results()`。
- 判定用のパス正規化は `os.path.abspath` → `os.path.normpath` →
  `os.path.normcase` の順で行う(相対/絶対表記の違いや `./` の有無、
  Windows での大文字小文字・区切り文字の違いを吸収して同一ファイルと判定
  する)。
- 同一ファイルが `fd` と `rg` の両方でヒットした場合は `[NAME]` 側にのみ
  残り、`[CONTENT]` 側からは除外される。
- `fd`/`rg` それぞれの結果内に重複があっても除去される。
- 最終的なリストの並び順は「`[NAME]` グループ(fd の出力順)→ `[CONTENT]`
  グループ(rg の出力順)」で固定。`fzf` には `--no-sort` を付けて渡すため、
  絞り込み中もこの順序(ファイル名一致が上位)が保たれる。

### プレビュー仕様

- `fzf` の `--preview` には `{2..}` プレースホルダを使い、`--delimiter ' '`
  と組み合わせて選択行の先頭トークン(`[NAME]`/`[CONTENT]`)を除いた部分
  (実パス)だけをプレビューコマンドに渡す。
- `bat` が PATH 上にあれば `bat --style=numbers --color=always
  --line-range=:200 {2..}`、無ければ `sys.platform` に応じて `cat {2..}`
  (非Windows)または `type {2..}`(Windows)にフォールバックする。

### 終了コード

| 終了コード | 状況 | 標準出力 | 標準エラー出力 |
| --- | --- | --- | --- |
| `0` | ファイルを選択して確定 | 選択パス1行 | (なし) |
| `1` | `fd`/`rg`/`fzf` のいずれかが未インストール | (なし) | インストール手順 |
| `1` | `fd`/`rg` とも該当ファイル無し | (なし) | 「一致するファイルが見つかりませんでした。」 |
| `130` | `fzf` 上で何も選択せずキャンセル(Esc など) | (なし) | (なし) |

### エラーハンドリング(未インストール時)

`fd`/`rg`/`fzf` の存在確認は `shutil.which()` で行い(実装:
[`tools.py`](src/devfind/tools.py))、検索を一切実行する前にまとめてチェック
する。1つでも欠けていれば、欠けているコマンドすべてを列挙し、コマンドごと
のインストール例(winget/choco/scoop/brew/apt)を添えたメッセージを標準エラー
出力に表示して終了コード `1` で終わる。`bat` はこのチェック対象外(任意
ツールのため、無くてもプレビューが `cat`/`type` にフォールバックするだけ)。

## 設定ファイル仕様

YAML/JSON ファイル(読み込みは [`confload`](../confload/README.md) パッケー
ジ経由)で、検索対象フォルダと除外パターンをカスタマイズできる。

デフォルトの探索パス: `~/.devfind/config.yaml`(無ければ以下のデフォルト値
を使用)

```yaml
# ~/.devfind/config.yaml
target_dirs:
  - ~/Downloads
  - ~/Documents

exclude:
  - venv
  - .venv
  - node_modules
  - __pycache__
  - .git
```

| キー | 型 | デフォルト | 説明 |
| --- | --- | --- | --- |
| `target_dirs` | `list[str]` | `[~/Downloads, ~/Documents]` | `fd`/`rg` の検索対象ルート。`~` は展開される。相対パスも可(カレントディレクトリ基準) |
| `exclude` | `list[str]` | `[venv, .venv, node_modules, __pycache__, .git]` | 除外するディレクトリ/ファイル名パターン。`fd --exclude <pattern>` / `rg --glob '!<pattern>'` にそのまま渡される |

補足:

- 設定ファイルに `target_dirs`/`exclude` の片方しか書かなければ、書かなかっ
  た方は上記デフォルト値のまま使われる(部分上書き)。
- `confload` 経由の読み込みなので、`.yaml`/`.yml`/`.json` いずれの拡張子も
  使える。`${VAR}` 参照や環境変数展開など `confload` の機能もそのまま使える
  (詳細は [confload/README.md](../confload/README.md))。
- `--config` を明示してそのパスにファイルが無い場合はエラー(`FileNotFoundError`)
  になる。デフォルトパス(`~/.devfind/config.yaml`)については、無くてもエラー
  にならず組み込みデフォルト値にフォールバックする。

## モジュール構成

```
src/devfind/
  config.py   設定読み込み(confload連携) — Settings(target_dirs, exclude)
  tools.py    fd/rg/fzf/bat の存在チェックとインストール案内メッセージ
  search.py   fd/rgコマンド組み立て・実行、グループ分け・重複除去 (merge_results)
  fzf.py      ラベル付き入力の組み立て、previewコマンド組み立て、選択結果のパース
  cli.py      typer製CLIエントリポイント。上記を並行実行してオーケストレーション
```

| モジュール | 主な公開関数/クラス | 責務 |
| --- | --- | --- |
| `config.py` | `Settings`, `load_settings()` | YAML/JSON設定の読み込みとデフォルト値へのフォールバック |
| `tools.py` | `ensure_required_tools()`, `MissingToolError`, `is_bat_available()` | 外部コマンドの存在確認とエラーメッセージ生成 |
| `search.py` | `run_fd()`, `run_rg()`, `merge_results()`, `Match` | `fd`/`rg` の実行(subprocess)とグループ分け・重複除去ロジック(purely functional) |
| `fzf.py` | `run_fzf()`, `format_line()`, `strip_label()`, `build_preview_command()` | `fzf` への入力整形・起動・選択結果のパース |
| `cli.py` | `app`, `main()` | 上記モジュールをつないだ全体のオーケストレーション、終了コード制御 |

`merge_results()` はsubprocess呼び出しから独立した純粋関数になっており、
`fd`/`rg` の出力(文字列のリスト)を渡すだけでグループ分け・重複除去の結果
を検証できる。

## Development

```bash
pip install -e ".[dev]"
pytest
```

外部コマンド(`fd`/`rg`/`fzf`)の呼び出しはテスト内で `subprocess.run` を
モック化しており、実際にこれらのコマンドがインストールされていなくても
テストは実行できる(`tests/conftest.py` の `fake_subprocess_run` フィク
スチャ)。
