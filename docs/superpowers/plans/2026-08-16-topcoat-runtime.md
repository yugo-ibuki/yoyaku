# Topcoat Runtime UI Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Yoyaku's handwritten browser JavaScript with Topcoat Runtime signals and a server-rendered search Shard while preserving the current UI and article JSON workflow.

**Architecture:** Search state lives in Topcoat browser signals and is sent to one registered Shard. Pure Rust code normalizes, filters, and sorts the embedded `ArticleIndex`; the Shard returns counts, conditions, cards, and CSS-target modals. The pinned Topcoat runtime script is embedded in the Worker at build time and served as the only JavaScript asset.

**Tech Stack:** Rust 1.95, Topcoat 0.5.0 Runtime and Assets, workers-rs 0.8.5, Unicode Normalization, Wrangler 4

---

## File map

- `app/src/search.rs`: validated query model plus pure filtering and sorting.
- `app/src/page.rs`: signals, search form, Shard markup, cards, and fragment modals.
- `app/src/runtime_asset.rs`: Topcoat Runtime asset manifest and embedded script accessor.
- `app/build.rs`: locates the pinned Topcoat browser runtime in Cargo's source cache.
- `app/src/routes.rs`: CSS, Topcoat Runtime JavaScript, health, and article JSON routes.
- `app/src/lib.rs`: registers the Shard and Runtime Asset Context.
- `app/tests/app.rs`: SSR, routes, runtime asset, and removal regression tests.
- `app/web/style.css`: fragment modal and shard loading styles.
- `package.json`: Rust test command; no application JavaScript test runner.

### Task 1: Pure Rust search

**Files:**
- Create: `app/src/search.rs`
- Modify: `app/src/lib.rs`
- Modify: `app/Cargo.toml`

- [ ] **Step 1: Write failing tests for normalized AND filtering and sorting**

Add tests that build two `Article` values and assert that `SearchQuery::default()` returns both, full-width `ＲＵＳＴ` matches `Rust`, all selected facets and ranges are applied together, and each supported sort has a deterministic ID tie-breaker.

- [ ] **Step 2: Run the search tests and verify RED**

Run: `cargo test -p yoyaku-app search::tests`

Expected: compilation fails because `SearchQuery` and `search_articles` do not exist.

- [ ] **Step 3: Implement the minimal search module**

Define:

```rust
#[derive(Debug, Clone, Default, PartialEq, Eq, serde::Deserialize)]
pub struct SearchQuery {
    pub keyword: String,
    pub genre: String,
    pub technology: String,
    pub source: String,
    pub created_from: String,
    pub created_to: String,
    pub max_minutes: String,
    pub sort: String,
}

pub fn search_articles<'a>(index: &'a ArticleIndex, query: &SearchQuery) -> Vec<&'a Article>;
```

Use Unicode NFKC plus lowercase for keyword comparison. Accept only valid ISO date strings and known sort names; parse an invalid reading-time limit as zero.

- [ ] **Step 4: Run the search tests and verify GREEN**

Run: `cargo test -p yoyaku-app search::tests`

Expected: every search unit test passes.

### Task 2: Topcoat Runtime asset

**Files:**
- Create: `app/build.rs`
- Create: `app/src/runtime_asset.rs`
- Modify: `app/Cargo.toml`
- Modify: `app/src/routes.rs`
- Modify: `app/src/lib.rs`
- Test: `app/tests/app.rs`

- [ ] **Step 1: Write failing route tests**

Assert that `/assets/topcoat-runtime.js` returns `200`, `text/javascript; charset=utf-8`, and recognizable Topcoat runtime code; assert that `/assets/main.js` and `/assets/filter.js` return `404`.

- [ ] **Step 2: Run the asset integration test and verify RED**

Run: `cargo test -p yoyaku-app serves_browser_assets_with_explicit_content_types`

Expected: the Runtime URL returns 404 and the two old routes still return 200.

- [ ] **Step 3: Embed and register the pinned Runtime**

Enable Topcoat `runtime` and `asset` features. `build.rs` must find `topcoat-runtime-0.5.0/browser/dist/index.js` below `CARGO_HOME/registry/src`, set `TOPCOAT_RUNTIME_JS`, and fail with an actionable message if missing. `runtime_asset.rs` must provide the script body and an `AssetConfig::hosted_at("/assets", manifest)` entry keyed by `topcoat::runtime::SCRIPT.id()`.

- [ ] **Step 4: Replace old JavaScript routes and verify GREEN**

Serve only `/assets/topcoat-runtime.js`, remove old JS constants/routes, register the Asset Context, then rerun the targeted test.

### Task 3: Signals, Shard, and fragment modals

**Files:**
- Modify: `app/src/page.rs`
- Modify: `app/src/lib.rs`
- Modify: `app/tests/app.rs`
- Modify: `app/web/style.css`

- [ ] **Step 1: Write failing SSR expectations**

Assert that the page contains the Topcoat Runtime URL and Shard markers, contains `href="#article-rust-workers"` and `role="dialog"`, and no longer contains `/assets/main.js`, `data-search`, or `<template` summary transport.

- [ ] **Step 2: Run the page integration test and verify RED**

Run: `cargo test -p yoyaku-app renders_the_article_archive_with_summary_templates`

Expected: assertions fail against the current handwritten-JavaScript markup.

- [ ] **Step 3: Implement Topcoat controls and result Shard**

Declare one String signal per search field. Wire controls with `@input` or `@change` and pass `$(signal.get())` into `#[topcoat::runtime::shard] article_results`. Register `article_results` through `RouterBuilderShardExt::shard` and pass every argument through `SearchQuery` before filtering.

- [ ] **Step 4: Render link cards and CSS-target dialogs**

Render each card as an anchor to its corresponding fragment dialog. Put all summary paragraphs directly in the dialog, provide backdrop and close anchors, preserve the source link, and update CSS so only `:target` is visible as a centered rounded modal with internal scrolling.

- [ ] **Step 5: Run app tests and verify GREEN**

Run: `cargo test -p yoyaku-app`

Expected: all app tests pass, including runtime, Shard, modal, API, and config coverage.

### Task 4: Remove handwritten JavaScript and verify the Worker

**Files:**
- Delete: `app/web/main.js`
- Delete: `app/web/filter.js`
- Delete: `app/web/filter.test.js`
- Modify: `package.json`
- Modify: `package-lock.json`
- Modify: `README.md`
- Modify: `CONTRIBUTING.md`

- [ ] **Step 1: Delete the obsolete JavaScript files**

Remove the DOM controller, filtering module, and Node test now covered by Rust tests.

- [ ] **Step 2: Update commands and documentation**

Set `npm test` to `cargo test --workspace` so CI retains one public test command. Document that Topcoat Runtime is experimental, browser filtering uses a server Shard, and only Wrangler remains a Node dependency.

- [ ] **Step 3: Run static verification**

Run:

```bash
cargo fmt --all --check
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
npm test
git diff --check
```

Expected: every command succeeds and no handwritten application JavaScript remains.

- [ ] **Step 4: Build the Cloudflare artifact**

Run: `npm run build`

Expected: `worker-build --release --no-panic-recovery app` produces the Worker bundle successfully for `wasm32-unknown-unknown`.

- [ ] **Step 5: Verify Wrangler packaging**

Run: `npm run deploy:dry-run`

Expected: Wrangler creates a dry-run deployment bundle without publishing it.

- [ ] **Step 6: Run browser acceptance**

Start `wrangler dev`, confirm the Runtime asset is 200, change at least two filters together, change sort order, open and close a card modal, and scroll the long summary. Confirm the existing personal article files remain unstaged and unchanged.
