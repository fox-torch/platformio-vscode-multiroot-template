# Architecture

## 設計目的

この雛形は、1つのルート配下に多数の**独立したPlatformIO Project**を置きながら、VS Codeでは1つのWindowで自然に扱うためのものです。

重要なのは、子ProjectのBuild / Upload / Monitorを自前実装しないことです。各子ProjectをVS Codeの正式なWorkspace Folderへ昇格させ、その後はstock PlatformIO IDEへ処理を戻します。

```text
nested PlatformIO Projects
        ↓
VS Code Multi-rootへ自動昇格
        ↓
stock PlatformIO IDEが正式Projectとして認識
```

各子Projectの`platformio.ini`が常にSource of Truthです。
## 起動シーケンス

1. 利用者がVS CodeでルートFolderを開く。
2. ルート`platformio.ini`をstock PlatformIO IDEが認識する。
3. `extra_scripts`から`pio-workspace-bootstrap.py`が実行される。
4. `projects/**/platformio.ini`を再帰探索する。
5. `.pio/workspace/<name>.code-workspace`を生成する。
6. 初回だけ`pio-workspace-switch.py`が同じVS Code Windowをgenerated Workspaceへ切り替える。
7. 各子Projectが正式Workspace Folderになる。

generated WorkspaceにはルートFolder自身も残します。ルートは全体構造を見るNavigator、子FolderはPlatformIO操作対象という役割分担です。

## なぜroot PlatformIO Projectがあるか

stock PlatformIO IDEにbootstrapを起動させるためです。root Project自身は実機コードを持たず、`build_src_filter = -<*>`でBuild対象を空にしています。
## Project探索と表示名

探索範囲は`projects/`全体です。Projectの深さに制限はありません。

表示名だけは`platformio-workspace.json`の`groups`で分類できます。たとえば`firmware`を`FW`、`tests`を`TEST`と表示できます。

```text
projects/firmware/main-controller → FW / main-controller
projects/tests/sensors/tof        → TEST / sensors / tof
projects/other/demo               → PJ / other / demo
```

VS Code Multi-rootはWorkspace Folder自体を入れ子表示できないため、階層を表示名へ埋め込み、名前順でカテゴリがまとまるようにしています。

## Active Project

generated Workspaceでは`platformio-ide.activateProjectOnTextEditorChange`を有効化します。子Project内のファイルを開くと、そのWorkspace Folderがstock PlatformIOのActive Projectへ切り替わります。
## 変更検知

独自常駐Watcherは置きません。root `platformio.ini`の`lib_dir = projects`によって、stock PlatformIO IDEが既に持っているFileSystemWatcherの監視範囲へ`projects/`を入れます。

新しいProject Folderや`platformio.ini`が追加されるとroot Projectが再評価され、bootstrapがgenerated Workspaceを更新します。Project Folderの削除・移動も同じ経路で追従します。

## 初回Window切替

単純な`code --reuse-window`は、複数のVS Code Windowがあると最後にActiveだったWindowへ作用する可能性があります。

そのためhelperは先にrootの`platformio.ini`をVS Code CLIで開き、対象repositoryを所有するWindowへフォーカスさせてからgenerated Workspaceへ切り替えます。起動直後のraceを避けるため、PlatformIOのextra scriptからdetached processとして実行します。

同一VS Code sessionで何度も切り替えないよう、`VSCODE_PID`と`VSCODE_IPC_HOOK`からsession markerを作ります。
## Repair / Importの境界

RepairはProjectのSourceを修正する機能ではありません。`.pio`、Compilation Database、PlatformIO生成VS Code metadataを捨て、`platformio.ini`をSource of Truthとして依存取得・Build・metadata生成をやり直します。

Importは外部Projectの`.git`、`.pio`、`.vscode`、IDE cache、ログ等を除外して`projects/`配下へ移します。コピー途中のProjectをWatcherが拾わないよう、最初に`.pio/maintenance/import-staging`で完成させてから正式配置へmoveします。

## Source of Truthと生成物

Source of Truth:

- 各子Projectの`platformio.ini`
- `projects/`配下のSource / include / lib / test
- `platformio-workspace.json`
- `tools/platformio/`

生成物:

- `.pio/`
- generated `.code-workspace`
- 子ProjectのPlatformIO生成`.vscode` metadata
- `compile_commands.json`

生成物を共有状態の根拠にはしません。壊れた場合は再生成できる設計です。
## 意図的にしないこと

- nested Project用の独自Build / Upload / Monitorを作らない
- PlatformIO IDEをforkしない
- 常駐Watcherを置かない
- Projectごとの設定をrootへ統合しない
- generated IntelliSense情報をSource of Truthにしない

この雛形が自作するのは、**Project発見・Workspace生成・初回Window切替・保守ツール**までです。実際のPlatformIO機能はできるだけstock PlatformIOへ委譲します。

## 制約

VS CodeのMulti-root WorkspaceはWorkspace Folderの階層表示をサポートしません。そのため`FW / ...`のような表示名で視覚的に分類します。

また、Project Folderを残したまま`platformio.ini`だけを削除する特殊ケースは、即時Watcher eventにならない場合があります。通常のFolder追加・削除・移動は追従対象です。
