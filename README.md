# PlatformIO VS Code Multi-root Template

複数の独立したPlatformIO Projectを、1つのリポジトリ・1つのVS Code Windowで扱うための雛形です。

各子Projectはそれぞれ独自の`platformio.ini`を持ち、単体でも普通のPlatformIO Projectとして動きます。ルート側は実機コードを持たず、VS Code Workspaceを自動構成するためだけに存在します。

## 何を解決するものか

PlatformIO IDEは、VS CodeのWorkspace Folder直下にある`platformio.ini`を正式Projectとして扱うのが基本です。そのため、1つのルートの下にPlatformIO Projectを多数入れただけでは、nested ProjectごとのBuild / Upload / Monitor / IntelliSense切替が扱いにくくなります。

この雛形では、nested Projectを独自IDEで処理するのではなく、**各子ProjectをVS Code Multi-root Workspaceの正式Folderへ自動昇格**させます。

```text
root folderをVS Codeで開く
        ↓
rootのbootstrap PlatformIO Projectが起動
        ↓
projects/**/platformio.ini を自動探索
        ↓
ローカルの.code-workspaceを自動生成
        ↓
各子Projectが正式なWorkspace Folderになる
        ↓
以後はstock PlatformIO IDEが通常どおり処理
```

## 基本構成

```text
.
├─ projects/                    # 実際のPlatformIO Project群
│  ├─ firmware/                 # 例: 正式ファームウェア
│  └─ tests/                    # 例: 単体試験・実験
├─ tools/platformio/            # Workspace / Repair / Import本体
├─ .vscode/                     # Maintenance起動用Task等
├─ platformio.ini               # Workspace bootstrap専用
├─ platformio-workspace.json    # 表示名設定
├─ PlatformIO Maintenance.cmd   # Windows初心者向けGUI入口
└─ PlatformIO Maintenance.command # macOS初心者向けGUI入口
```

実際のPlatformIO Projectは必ず`projects/`以下に置きます。深さに制限はありません。

```text
projects/tests/motors/DC/platformio.ini
projects/tests/sensors/tof/platformio.ini
projects/firmware/main-controller/platformio.ini
```

## 使い始める

必要なのはVisual Studio Codeと`PlatformIO IDE`拡張です。VS Codeでこのリポジトリのルートを普通に`Open Folder...`するだけです。

数秒後にgenerated Multi-root Workspaceへ自動切替されます。`.code-workspace`を手動で開く必要はありません。

## 表示階層

VS CodeのMulti-root Workspace自体はFolderを入れ子表示できないため、物理パスを表示名へ埋め込みます。設定は`platformio-workspace.json`です。

```json
{
  "workspaceName": "platformio-workspace",
  "groups": [
    { "path": "firmware", "label": "FW" },
    { "path": "tests", "label": "TEST" }
  ]
}
```

この設定なら、次のように表示されます。

```text
FW / main-controller
TEST / motors / DC
TEST / sensors / tof
```

`groups`にないProjectも消えず、`PJ / <relative path>`として表示されます。

## 普段のPlatformIO操作

子Projectのファイルを開くと、そのProjectがActive Projectへ自動切替されます。Build / Upload / Clean / Monitor / env / port / `lib_deps`は、各子Project自身の`platformio.ini`がSource of Truthです。

独自Build wrapperや独自Upload処理はありません。Multi-root化した後はstock PlatformIO IDEへ処理を任せます。

## Repair / Import

通常は不要です。壊れたProjectの復旧や、外部PlatformIO Projectの移行時だけ使います。

- Windows: `PlatformIO Maintenance.cmd`をダブルクリック
- macOS: `PlatformIO Maintenance.command`をダブルクリック
- VS Code: `Ctrl+Shift+B`

GUIには次があります。

- `Repair project`: `.pio`等を捨て、依存取得・Build・VS Code metadata再生成を行う
- `Import project`: 外部Projectからローカル生成物を除外して`projects/`配下へコピーし、Build検証する
- `Repair all projects`: 全子Projectをclean generated stateからBuildし直す

Repairはソースや`platformio.ini`を勝手に書き換えません。

## 自動追従

ルート`platformio.ini`の`lib_dir = projects`を利用し、stock PlatformIO IDEが持つ既存Watcherの監視対象へ`projects/`全体を入れています。新しい`platformio.ini`を追加・Project Folderを削除/移動すると、bootstrapが再実行されgenerated Workspaceも更新されます。

常駐独自Watcherは使いません。

## 生成物

`.pio/`、generated `.code-workspace`、各子ProjectのPlatformIO生成metadataはローカル生成物です。雛形本体のSource of Truthではありません。

詳細な内部構造は[`docs/architecture.md`](docs/architecture.md)を参照してください。`projects/`の使い方は[`projects/README.md`](projects/README.md)にまとめています。
