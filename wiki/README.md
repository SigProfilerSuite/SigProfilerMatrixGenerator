# GitHub Wiki Migration Files

This folder contains documentation migrated from the OSF wiki (https://osf.io/s93d5/wiki) for SigProfilerMatrixGenerator.

## How to Set Up GitHub Wiki

### Step 1: Enable Wiki in Repository Settings
1. Go to the repository on GitHub
2. Click **Settings** → scroll to **Features**
3. Check **Wikis** to enable

### Step 2: Clone the Wiki Repository
GitHub Wikis are stored as separate Git repositories:

```bash
git clone https://github.com/AlexandrovLab/SigProfilerMatrixGenerator.wiki.git
```

### Step 3: Copy Wiki Files
Copy all `.md` files from this `wiki/` folder to the cloned wiki repository:

```bash
cp wiki/*.md SigProfilerMatrixGenerator.wiki/
```

### Step 4: Push to GitHub
```bash
cd SigProfilerMatrixGenerator.wiki
git add .
git commit -m "Migrate wiki from OSF"
git push
```

## File Structure

| File | Description |
|------|-------------|
| `Home.md` | Wiki homepage |
| `_Sidebar.md` | Navigation sidebar |
| `Installation-Python.md` | Python installation guide |
| `Installation-R.md` | R wrapper installation guide |
| `Quick-Start-Example.md` | Quick start tutorial |
| `Currently-Supported-Genomes.md` | List of supported genomes |
| `Using-the-Tool-*.md` | Usage documentation |
| `Output-*.md` | Output file descriptions |

## Notes

- The `_Sidebar.md` file will automatically create a navigation sidebar on GitHub Wiki
- `Home.md` will be the wiki homepage
- Internal links use the format `[Link Text](Page-Name)` (without `.md` extension)
