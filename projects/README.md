# projects/

実際のPlatformIO Projectはすべてこの配下に置きます。

各Projectは普通の独立PlatformIO Projectです。

```text
projects/<category>/<project>/
├─ platformio.ini
├─ src/
├─ include/
├─ lib/
└─ test/
```

Projectの深さに制限はありません。`platformio.ini`があるFolderが1つのPlatformIO Projectとして自動検出されます。

例:

```text
projects/firmware/main-controller/platformio.ini
projects/tests/motors/DC/platformio.ini
projects/tests/sensors/tof/platformio.ini
```
カテゴリ名は機能に影響しません。`firmware`や`tests`は例です。必要に応じて`robot/`、`sensors/`、`experiments/`等へ変更できます。

Explorer上の表示名だけを`platformio-workspace.json`で設定します。

```json
{
  "groups": [
    { "path": "firmware", "label": "FW" },
    { "path": "tests", "label": "TEST" }
  ]
}
```

設定にないカテゴリもProject探索対象です。その場合は`PJ / ...`という表示名になります。

外部Projectを持ち込む場合は手動コピーよりMaintenance GUIの`Import project`を推奨します。ローカル生成物を除外してからBuild検証できます。
