# CLAUDE.md

このリポジトリで作業する際のメモ。

## n8n ワークフロー 作成後チェックリスト

n8n のワークフローを作成・更新したら、公開（publish）前に以下を確認する。
特に AI ビルダー（`aiBuilderAssisted`）で生成したワークフローは要注意。

### 1. 式フィールドの `=` プレフィックス（最重要）

n8n では、式（`{{ ... }}`）を含むフィールドは**値の先頭が `=` で始まっていなければ評価されない**。
`=` が無いと `{{ ... }}` は**ただの文字列**として扱われ、値が渡らない。

- [ ] `{{ }}` を使うフィールドはすべて `"={{ ... }}"` の形になっているか
- [ ] 特に **AI/LLM ノードの `text`（プロンプト）** を確認する
      （AI ビルダーがここだけ `=` を落とすことがある）
- 参考：正しい例
  - Slack `text`: `"=:newspaper: ... {{ $json.text }}"`
  - DataTable: `"contentHash": "={{ $('Extract Content').item.json.contentHash }}"`
  - If ノード: `"leftValue": "={{ ... }}"`

> 実例：`OCaml Weekly News Daily Digest`（`pM67UJhKzOrmbemG`）で、Summarize ノードの
> プロンプトが `=` 無しだったため本文が Gemini に渡らず、存在しない情報を捏造していた。

### 2. データが実際に流れているかを実行ログで確認

publish 後や動作確認時は、成功ステータスだけでなく**中身**を見る。

- [ ] `get_execution`（`includeData: true`）で各ノードの入出力を確認
- [ ] LLM ノードの `metadata.tracing.llm.tokens.in` を見る。
      本文を渡しているはずなのに**入力トークンが極端に少ない**場合、
      式が評価されず本文が届いていないサイン
- [ ] 出力に、入力本文に**存在しない情報（捏造）**が混ざっていないか

### 3. 基本チェック

- [ ] HTTP Request（`responseFormat: text`）の出力は `$json.data` で参照しているか
- [ ] Code ノードで参照する前ノードのプロパティ名が実際の出力と一致しているか
- [ ] 更新後は **publish** して `activeVersionId` がドラフトの `versionId` と一致することを確認
      （更新しただけでは draft のまま。アクティブ版には反映されない）
- [ ] `validate_workflow` / 更新時の `validationWarnings` を確認。
      ただし既存の無害な警告（例：動作中の Slack ノードの `resource` discriminator 警告）は
      今回の変更と切り分ける

### 4. Form Trigger / Webhook を公開する場合はアクセス制御の経路を確認

n8n の手前に Cloudflare Access（Zero Trust）などのリバースプロキシ認証がある場合、
`/form/*` や ``/webhook/*` のパスがそのアクセス制御でブロックされていないか確認する。

- [ ] `curl -I <production form URL>` して **302 で Access ログインページへリダイレクトされていないか** 確認する
      （ワークフロー実行ログには記録が残らないため、実行ログだけ見ても気づけない）
- [ ] ブロックされている場合は、n8n 側ではなく Cloudflare（等）の Access Application 設定で
      該当パスに Bypass（認証不要）ポリシーを追加する必要がある

> 実例：`毎日の振り返り`（`kxAsviuzSS6yyARz`）で、フォーム送信が
> 「Problem submitting response」エラーになる不具合。ワークフロー設定は正しかったが、
> `n8n.dza810.com` ドメイン全体が Cloudflare Access で保護されており、
> `/form/reflection` への GET/POST が Access ログインページへ 302 リダイレクトされていたため、
> ブラウザからの送信リクエストが n8n まで届いていなかった。
