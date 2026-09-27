# 画像来歴

以下の3ファイルは、既存プロジェクト `projects/fractal-engineering-dialogue-video/assets/dining-room/` からバイト単位でコピーした。新しい生成や加工はしていない。

| 保存先 | コピー元 | SHA-256 |
|---|---|---|
| `assets/base.png` | `base.png` | `2b49969ee044c24f2749d9289aebb8e6ec5e20f5ed4a6b32bd59428824027947` |
| `assets/left-speaking.png` | `left-speaking.png` | `91209ad7c78e36703b861e06de03fafb1691e17842512c2292e302d561385b56` |
| `assets/right-speaking.png` | `right-speaking.png` | `0ec4193606ac7113245092fc0d0b84e0ca4b424750340b225d9b058205b25489` |

すべて941×1672、RGB PNG。各speaking画像は頭部の向きまで異なる完成ポーズのため、レンダラーは半透明合成を行わず、発話ターン単位で対応する完成画像へ切り替える。ターン間はbase画像へ戻す。
