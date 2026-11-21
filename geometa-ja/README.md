# geometa-ja

[GeoGuessr Learnable Meta](https://userscript.learnablemeta.com/geometa.user.js) の userscript を改変し、
メタの説明（`metaName` と `note`）を Gemini API で日本語に翻訳してから表示するようにしたもの。

- `geometa-ja.user.js` … 改変済みの userscript（元: v0.97）
- `geometa-ja.patch` … 元スクリプトとの差分（バージョンアップ時の再適用用）

## 使い方

1. `geometa-ja.user.js` 冒頭の `GEMINI_API_KEY` に API キーを入れる
2. Tampermonkey などにインストールする
3. 元の「GeoGuessr Learnable Meta」は無効にする（両方有効だとパネルが2つ出る）

`GEMINI_API_KEY` が空なら翻訳は行わず、元スクリプトと同じ動作になる。
翻訳に失敗したときは英語のまま表示する（エラーはブラウザのコンソールに `[geometa-ja]` 付きで出る）。

翻訳結果は `GM_setValue` に最大 1000 件キャッシュするので、同じメタで API を再度呼ぶことはない。

## 元スクリプトからの変更点

| 場所 | 変更 |
| --- | --- |
| ヘッダー `@name` | `(JA)` を付ける（元スクリプトと別物として扱わせるため） |
| ヘッダー `@downloadURL` / `@updateURL` | 削除（自動更新で改変が消えないように） |
| ヘッダー `@connect` | `generativelanguage.googleapis.com` を追加 |
| `==/UserScript==` の直後 | `geometa-ja: BEGIN` 〜 `END` のブロックを追加 |
| `var _GM_xmlhttpRequest = ...` の1行 | `geometaJaWrapXhr(...)` で包む |

本体のコードに入れた変更は最後の1行だけ。
`learnablemeta.com/api/userscript/location?...` へのリクエストの `onload` だけを横取りし、
レスポンス JSON の `metaName` / `note` を翻訳したものに差し替えてから本体の `onload` に渡している。
それ以外のリクエストはそのまま通る。

## バージョンアップへの追従

```bash
cd geometa-ja
```

```bash
curl -sSL -o geometa.user.js https://userscript.learnablemeta.com/geometa.user.js
```

```bash
patch -o geometa-ja.new.user.js geometa.user.js < geometa-ja.patch
```

パッチが当たったら `GEMINI_API_KEY` を入れ直してインストールする。
当たらない場合は上の表の5か所を手で直す。確認ポイント：

- `var _GM_xmlhttpRequest = ...` の行が残っているか
- メタ取得の URL が `https://learnablemeta.com/api/userscript/location?` のままか
- 表示に使うフィールドが `metaName` / `note` のままか（`html(..., () => get$1(geoInfo).note)` 付近）

`geometa-ja.patch` を作り直すときは：

```bash
diff -u --label geometa.user.js --label geometa-ja.user.js geometa.user.js geometa-ja.user.js > geometa-ja.patch
```

## 補足

- モデルは `GEMINI_MODEL`（既定 `gemini-3.1-flash-lite`）。thinking は `minimal`。
- 保存値（パネル位置・map maker 用トークンなど）はスクリプトごとに別管理なので、元スクリプトの設定は引き継がれない。
