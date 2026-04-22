# 公開ダッシュボード — デプロイガイド

## リポジトリ構成

```
mashup-reporter/
├── docs/                          ← GitHub Pages の公開ディレクトリ
│   ├── index.html                 ← ダッシュボード本体
│   └── data/
│       ├── latest.json            ← 常に最新データ（Actions が上書き）
│       └── snapshot_20260422.json ← 日付別アーカイブ
├── .github/
│   └── workflows/
│       └── daily-snapshot.yml     ← 毎朝自動実行
├── snapshot.py
├── requirements.txt
└── README.md
```

---

## Step 1: GitHub リポジトリを作成

```bash
# ローカルで初期化
git init mashup-reporter
cd mashup-reporter

# ファイルをコピーして配置（このディレクトリ構造に合わせる）
git add .
git commit -m "initial commit"

# GitHub に push
gh repo create mashup-reporter --public
git push -u origin main
```

---

## Step 2: GitHub Pages を有効化

1. リポジトリの **Settings → Pages**
2. Source: `Deploy from a branch`
3. Branch: `main` / Folder: `/docs`
4. Save

→ `https://あなたのユーザー名.github.io/mashup-reporter/` で公開されます

---

## Step 3: GitHub Actions の権限設定

1. **Settings → Actions → General**
2. `Workflow permissions` → **Read and write permissions** を選択
3. Save

---

## Step 4: 初回データ生成（ローカル）

```bash
pip install -r requirements.txt
python snapshot.py --json > docs/data/latest.json
git add docs/data/latest.json
git commit -m "initial data"
git push
```

---

## Step 5: 毎朝の自動更新を確認

`.github/workflows/daily-snapshot.yml` を push すると、
翌朝 7:05 JST から自動実行されます。

**手動でテスト実行:**
GitHub の Actions タブ → `Daily ETF Snapshot` → `Run workflow`

---

## カスタムドメインの設定（任意）

`docs/CNAME` ファイルを作成し、独自ドメインを記述:
```
signal.mashup-reporter.com
```

DNS の CNAME レコードを `あなたのユーザー名.github.io` に向ける。

---

## Vercel / Netlify にデプロイする場合

### Vercel
```bash
npm i -g vercel
vercel --cwd docs
```
Build Command: （なし）
Output Directory: `docs`

### Netlify
Netlify にリポジトリ接続 → Publish directory: `docs`
Build command: （空欄）

---

## データ更新の仕組み

```
毎朝 7:05 JST
   ↓
GitHub Actions が起動
   ↓
snapshot.py が yfinance から価格取得
   ↓
docs/data/latest.json を上書きコミット
   ↓
GitHub Pages が自動反映（数分以内）
   ↓
ブラウザが fetch('data/latest.json') で最新データ表示
```

ダッシュボードを開くたびに `?t=タイムスタンプ` でキャッシュバイパスするため、
常に最新のJSONが表示されます。

---

## 投資免責事項の編集

`docs/index.html` 末尾の `.footer-note` を編集してください。
法的な観点から、免責文は必ず記載することを推奨します。
