# Summary Articles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Git管理の記事JSONをRustで検証・索引化し、HonoとCloudflare Workers Static Assetsで検索・モーダル閲覧できる公開テンプレートを作る。

**Architecture:** `content/articles`を正本、`public/data/articles.json`を生成物とし、Rust CLIが両者の境界を管理する。Hono Workerはヘルスチェックと生成済み索引APIだけを提供し、Vite製のクライアントが複合検索とモーダル表示を担当する。

**Tech Stack:** TypeScript 5、Hono 4、Vite 8、Vitest 4、Cloudflare Vite Plugin、Wrangler 4、Rust 1.87、clap、serde、reqwest、scraper

---

## File map

- `src/shared/article.ts`: 配信用記事・索引の型。
- `src/client/filter.ts`: AND検索と並び替えの純粋関数。
- `src/client/render.ts`: 安全なDOM生成、カード、モーダル。
- `src/client/main.ts`: API取得、フォーム状態、イベント接続。
- `src/client/style.css`: 承認済みの3列、固定サイドバー、モーダルの見た目。
- `worker/index.ts`: Hono API。
- `content/articles/*.json`: フォーク利用者が編集する記事正本。
- `public/data/articles.json`: Rust CLIが生成する配信用索引。
- `cli/src/model.rs`: JSONモデル。
- `cli/src/validate.rs`: 記事検証。
- `cli/src/ogp.rs`: HTMLからOGPを抽出。
- `cli/src/index.rs`: 索引生成。
- `cli/src/main.rs`: `validate`、`build`、`enrich`コマンド。

### Task 1: TypeScript基盤と検索ロジック

**Files:**
- Create: `package.json`, `tsconfig.json`, `vite.config.ts`, `vitest.config.ts`, `wrangler.jsonc`
- Create: `src/shared/article.ts`, `src/client/filter.test.ts`, `src/client/filter.ts`

- [ ] **Step 1: Write the failing search tests**

```ts
expect(filterArticles(articles, { keyword: 'rust', genre: '', technology: '', source: '', createdFrom: '', createdTo: '', maxMinutes: 0, sort: 'updated-desc' })).toHaveLength(1)
expect(filterArticles(articles, { keyword: '', genre: 'Web開発', technology: 'Rust', source: 'Zenn', createdFrom: '2026-08-01', createdTo: '2026-08-15', maxMinutes: 10, sort: 'updated-desc' })).toEqual([articles[0]])
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `npm test -- src/client/filter.test.ts`
Expected: FAIL because `filterArticles` does not exist.

- [ ] **Step 3: Implement normalized AND filtering and sorting**

```ts
export function filterArticles(articles: Article[], query: SearchQuery): Article[] {
  const keyword = normalize(query.keyword)
  return articles.filter((article) => matches(article, query, keyword)).sort(sorter(query.sort))
}
```

- [ ] **Step 4: Run the test and confirm GREEN**

Run: `npm test -- src/client/filter.test.ts`
Expected: all filter tests pass.

### Task 2: Hono Worker API

**Files:**
- Create: `worker/index.test.ts`, `worker/index.ts`

- [ ] **Step 1: Write failing API tests**

```ts
expect((await app.request('/api/health')).status).toBe(200)
expect(await (await app.request('/api/health')).json()).toEqual({ ok: true })
expect((await app.request('/api/articles')).headers.get('cache-control')).toContain('public')
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `npm test -- worker/index.test.ts`
Expected: FAIL because the Hono app is absent.

- [ ] **Step 3: Add minimal Hono routes**

```ts
const app = new Hono()
app.get('/api/health', (c) => c.json({ ok: true }))
app.get('/api/articles', (c) => c.json(articleIndex, 200, { 'Cache-Control': 'public, max-age=300' }))
export { app }
export default app
```

- [ ] **Step 4: Run the test and confirm GREEN**

Run: `npm test -- worker/index.test.ts`
Expected: both routes pass.

### Task 3: Card grid, sidebar filters, and modal

**Files:**
- Create: `index.html`, `src/client/render.test.ts`, `src/client/render.ts`, `src/client/main.ts`, `src/client/style.css`

- [ ] **Step 1: Write failing DOM tests**

```ts
const card = createArticleCard(article, () => undefined)
expect(card.tagName).toBe('BUTTON')
expect(card.textContent).toContain(article.title)
renderDialog(dialog, article)
expect(dialog.querySelector('[data-dialog-meta]')?.textContent).toContain('読了 8分')
expect(dialog.querySelector('[data-dialog-summary]')?.children).toHaveLength(article.summary.length)
```

- [ ] **Step 2: Run the test and confirm RED**

Run: `npm test -- src/client/render.test.ts`
Expected: FAIL because render helpers do not exist.

- [ ] **Step 3: Implement DOM creation without article-derived `innerHTML`**

```ts
const title = document.createElement('h3')
title.className = 'title'
title.textContent = article.title
card.append(title)
```

Connect the search form to `filterArticles`, render three columns on desktop, keep the sidebar sticky, and use `dialog.showModal()` for full-card activation.

- [ ] **Step 4: Run DOM and search tests**

Run: `npm test`
Expected: all TypeScript tests pass.

### Task 4: Rust article validation and index generation

**Files:**
- Create: `cli/Cargo.toml`, `cli/src/model.rs`, `cli/src/validate.rs`, `cli/src/index.rs`, `cli/src/lib.rs`, `cli/src/main.rs`

- [ ] **Step 1: Write failing validation tests**

```rust
#[test]
fn rejects_an_updated_date_before_created_date() {
    let article = fixture().with_dates("2026-08-15", "2026-08-14");
    assert!(validate_article(&article).unwrap_err().to_string().contains("updated_at"));
}

#[test]
fn rejects_duplicate_urls() {
    let article = fixture();
    assert!(validate_collection(&[article.clone(), article]).is_err());
}
```

- [ ] **Step 2: Run the tests and confirm RED**

Run: `cargo test --manifest-path cli/Cargo.toml`
Expected: FAIL because validation modules do not exist.

- [ ] **Step 3: Implement the model, validation, deterministic sorting, and CLI commands**

```rust
pub fn build_index(mut articles: Vec<Article>) -> ArticleIndex {
    articles.sort_by(|a, b| b.updated_at.cmp(&a.updated_at).then_with(|| a.id.cmp(&b.id)));
    ArticleIndex::from_articles(articles)
}
```

- [ ] **Step 4: Run Rust tests and confirm GREEN**

Run: `cargo test --manifest-path cli/Cargo.toml`
Expected: validation and index tests pass.

### Task 5: Rust OGP enrichment

**Files:**
- Create: `cli/src/ogp.rs`
- Modify: `cli/src/main.rs`, `cli/src/lib.rs`

- [ ] **Step 1: Write failing parser tests**

```rust
let html = r#"<meta property="og:title" content="記事"><meta property="og:image" content="/og.png">"#;
let ogp = parse_ogp(html, &Url::parse("https://example.com/post").unwrap()).unwrap();
assert_eq!(ogp.title.as_deref(), Some("記事"));
assert_eq!(ogp.image_url.as_deref(), Some("https://example.com/og.png"));
```

- [ ] **Step 2: Run the parser test and confirm RED**

Run: `cargo test --manifest-path cli/Cargo.toml ogp`
Expected: FAIL because `parse_ogp` is absent.

- [ ] **Step 3: Implement deterministic HTML parsing and bounded fetching**

```rust
let client = reqwest::blocking::Client::builder()
    .timeout(Duration::from_secs(10))
    .user_agent("yoyaku/0.1")
    .build()?;
```

Parse `property` and `name` meta attributes, resolve relative image URLs, and update only the `ogp` field.

- [ ] **Step 4: Run all Rust tests**

Run: `cargo test --manifest-path cli/Cargo.toml`
Expected: all tests pass.

### Task 6: Samples, automation, and public documentation

**Files:**
- Create: `content/articles/01-cloudflare-workers-rust.json` through `10-forkable-archive.json`
- Create: `public/data/articles.json`, `article.schema.json`, `.gitignore`, `LICENSE`, `README.md`, `CONTRIBUTING.md`
- Create: `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`

- [ ] **Step 1: Add ten non-personal sample articles**

Each file must pass `yoyaku validate`; the first sample includes enough summary paragraphs to verify modal scrolling.

- [ ] **Step 2: Generate the committed index**

Run: `cargo run --manifest-path cli/Cargo.toml -- build --content-dir content/articles --output public/data/articles.json`
Expected: ten articles and unique genre/source/technology facets.

- [ ] **Step 3: Add CI and conditional deployment**

CI runs Node and Rust tests, typecheck, build, clippy, and Wrangler dry-run. Deployment runs only on `main` when the fork has configured `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` repository secrets.

- [ ] **Step 4: Document fork setup**

README commands:

```bash
npm install
cargo run --manifest-path cli/Cargo.toml -- validate
cargo run --manifest-path cli/Cargo.toml -- build
npm run dev
```

### Task 7: Full verification and visual acceptance

**Files:**
- Modify only files required by failures discovered here.

- [ ] **Step 1: Run all automated checks**

```bash
npm test
npm run typecheck
cargo test --manifest-path cli/Cargo.toml
cargo clippy --manifest-path cli/Cargo.toml --all-targets -- -D warnings
npm run build
npx wrangler deploy --dry-run
git diff --check
```

- [ ] **Step 2: Run the built app locally**

Run: `npm run preview -- --host 0.0.0.0`
Expected: the root page and `/api/health` are reachable.

- [ ] **Step 3: Verify in a real browser**

Confirm desktop three-column cards, sticky sidebar, compound filtering, full-card modal activation, metadata above summary, modal scroll reset, external source link, and one-column mobile layout.

- [ ] **Step 4: Review repository scope**

Run: `git status --short` and `git diff --stat HEAD`
Expected: no secrets or personal article data; `.superpowers` remains ignored and uncommitted.
