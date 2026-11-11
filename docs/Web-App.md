# Web App

The SigProfilerMatrixGenerator Workbench is a local web app for generating
mutational matrices without writing code. Choose a folder of variant calls and
a reference genome, start the run, follow its progress, and plot the resulting
matrices sample by sample. Everything runs on your own computer: the app is a
small server on this machine, and your browser is its window.

It runs the same matrix generation as the Python function and the command
line, so a run started here writes exactly the files described in
[Output Overview](Using-the-Tool-Output.md).

## Starting the app

### From a copy of the repository

Use the launcher for your system, in the top folder of the repository:

| System | Launcher |
|---|---|
| macOS | Double-click `launch_web.command`, or run `./launch_web.sh` in Terminal |
| Linux | `./launch_web.sh` |
| Windows | Double-click `launch_web.bat` |

The first launch creates a private Python environment, `.venv-dashboard`, next
to the launcher and installs SigProfilerMatrixGenerator into it. Later launches
reuse it and skip the install, unless `setup.py` or `pyproject.toml` has
changed (for example after updating the repository).

### From an installed package

If SigProfilerMatrixGenerator is already installed with pip, either command
starts the app:

```bash
SigProfilerMatrixGenerator web
sigprofilermatrixgenerator-web
```

### What happens next

The app opens a browser tab at `http://127.0.0.1:<port>/`. A free port is picked
on every launch, so the address changes from one launch to the next; the
terminal prints the current one. Starting the app while it is already running
does not start a second copy: it prints the address of the running one.

### Launch options

| Option | Meaning |
|---|---|
| `--no-launch` | Start the server without opening a browser tab |
| `--stop` | Stop the running app, and any run it started, then exit |
| `--volume PATH` | Folder where reference genomes are installed (same as the CLI's `--volume`) |
| `--reinstall` | Force a fresh install into `.venv-dashboard` (launcher scripts only) |

```bash
./launch_web.sh --no-launch          # start without opening a tab
./launch_web.sh --stop               # stop it from another terminal
SigProfilerMatrixGenerator web --volume /data/genomes
```

## Generating matrices

The **New run** tab is four numbered cards. Each number turns green once its
card is complete.

!!! tip "Try the example first"
    **Try the example** fills in the BRCA example that ships with
    SigProfilerMatrixGenerator: simple text calls for four breast cancer
    genomes, against GRCh37. Its output goes to
    `~/SigProfilerMatrixGenerator_example`. GRCh37 must be installed, or the
    run installs it first (see [Reference genome](#3-reference-genome)).

### 1. Input

Click **Choose the input folder**, or paste a folder path and press Enter.
Every file in the folder is read, so keep one cohort, in one format, per
folder.

| Extension | Format | Samples |
|---|---|---|
| `.vcf` | VCF 4.x | One file per sample, named after the file |
| `.maf` | MAF | From the `Tumor_Sample_Barcode` column; one file can hold many samples |
| `.txt` | SigProfiler simple text | From the second column; one file can hold many samples |

As soon as a folder is chosen, the app reads it and reports the format, the
number of samples, the number of mutation calls and the number of files,
before anything runs. It also catches the usual mistakes:

- **A single file instead of a folder.** SigProfilerMatrixGenerator reads
  whole folders, so the app names the folder to choose instead.
- **Mixed formats.** A folder holding both `.vcf` and `.maf` files is refused.
  Put each format in its own folder.
- **Other files.** Files that are not mutation calls (a `README`, say) are
  listed with a warning, since the run would try to read them too.

Files starting with `__` or `.DS` are skipped, as SigProfilerMatrixGenerator
itself skips them. A
folder that holds no files but has an `input/` subfolder, the layout of older
projects, is read from `input/`.

### 2. Project

The **project name** becomes part of every file name, as in
`BRCA.SBS96.all`. It is filled in from the input folder's name until you type
your own.

The **output folder** is where the matrices go:

- Left blank, they go to an `output` folder inside the input folder.
- Set, they go straight into that folder.

Either way, the matrices are written to `SBS/`, `DBS/` and `ID/` subfolders,
with run logs in `logs/`. SigProfilerMatrixGenerator also keeps a copy of the
input files it read, in an `input/` folder: inside the input folder by
default, or inside the output folder when one is set.

### 3. Reference genome

Choose the assembly your variants were called against. The card says whether
it is installed:

- **Install it now** starts the download in the background. The genome is
  large (about 3 GB for a human assembly) and is downloaded once.
- With **If it is not installed yet, install it when the run starts** ticked
  (the default), a run installs a missing genome as its first step.

Installed genomes are also listed in the sidebar; clicking one selects it.

!!! note
    The genome card only checks that each of the genome's files is present.
    A run checks the files against their expected checksums before it starts.
    If they do not match, the run downloads the genome again when automatic
    install is ticked; otherwise it stops and says the files do not match.

### 4. Matrices

SBS, DBS and ID matrices are always written. The options add to them:

| Option | What it does | Python / CLI equivalent |
|---|---|---|
| Exome only | Keeps mutations inside the exome (with a 100 bp cushion). Files end in `.exome` | `exome=True` / `--exome` |
| Strand bias test | Tests transcriptional strand bias for SBS24, SBS384 and SBS6144; results go to `TSB/` | `tsb_stat=True` / `--tsb_stat` |
| ID89, ID476 | Adds the Koh et al. (2025) indel matrices; ID83 is unchanged | `indel_contexts=["89", "476"]` / `--indel_contexts 89 476` |
| Region BED file (Advanced) | Keeps only these regions; the file needs a header line. Files end in `.region` | `bed_file=` / `--bed_file` |
| Genome install folder (Advanced) | Where reference genomes are installed | `volume=` / `--volume` |

See [ID89 and ID476](ID89-ID476.md) for the indel classifications, and
[Output Overview](Using-the-Tool-Output.md) for every file a run writes.

Click **Start run**. The summary beside the button shows the project, the
number of samples and the genome the run will use.

## Following a run

Starting a run opens the **Monitor** tab:

- **Progress** in three steps: checking the reference genome (and installing
  it if needed), generating the matrices, and writing the summary. A genome
  install shows as a single step.
- **Details:** project, genome, input folder, output folder and start time.
- **Log:** the run's own output as it is written. Untick **follow** to scroll
  back while it runs.
- **Stop** ends the run. Files already written stay where they are.

When the run finishes, **Open results** shows its matrices. If it fails, the
reason is shown above the log, and the full traceback is in the log.

Each run is a separate process, so a long run never slows the page, and runs
started here keep their records after the app is restarted. Every run, past
and present, is listed in the sidebar under **Runs**; the Monitor tab shows a
count of the ones still in progress.

## Exploring results

Open a finished run from the Monitor tab, or choose any output folder in the
sidebar under **Open results**. That includes folders written earlier by the
Python function or the command line.

The **Results** tab shows:

- **Tiles:** the number of contexts and matrix files, the number of samples,
  and the project.
- **Matrices:** one button per context found (SBS96, DBS78, ID83, and so on),
  grouped into SBS, DBS and ID.
- **The profile** of the selected context, for one sample at a time:
    - choose the **sample** from the list;
    - switch between **Counts**, **Percent** and **Proportion**. Percent and
      proportion rescale each sample to its own total, which makes samples with
      different mutation burdens comparable;
    - the **?** button explains what the chart shows and how to read it;
    - **Download** saves the matrix file;
    - the camera button above the chart saves the figure as SVG, named after
      the project, context and sample.
- **Matrix files:** every matrix in the folder, with its size and a download
  link.

Charts are drawn by SigProfilerPlotting's own renderers, the same ones its
dashboard uses.

!!! note "Requirements for charts"
    Charts need SigProfilerPlotting 1.5.0 or later. With an older version the
    Results tab still lists the matrices and lets you download them, and says
    why the charts are missing. To upgrade:

    ```bash
    pip install --upgrade sigProfilerPlotting
    ```

SBS1536 and SBS4608 use a multi-panel layout that the Results tab does not
draw. Download the matrix and open it in the SigProfilerPlotting dashboard to
view it.

## Themes

The menu in the top bar switches between four themes: **UC San Diego**,
**UAlbany** and **SigProfilerSuite** are light, **Night** is dark. The choice
is remembered by your browser. Until one is chosen, the app follows your
system's light or dark setting. Charts stay on a white panel in every theme,
so the standard SigProfiler colours read the same everywhere.

## Stopping the app

Any of these stops the app, together with any run still in progress:

- the **Quit** button in the top bar, which asks you to confirm and says if a
  run is still in progress;
- `./launch_web.sh --stop` (or `launch_web.bat --stop`, or
  `SigProfilerMatrixGenerator web --stop`) from another terminal;
- Ctrl+C in the terminal the app was started from.

Matrices already written stay where they are.

## Security

The app is meant for one person on their own computer. It listens only on
this machine (`127.0.0.1`) and has no login. It rejects requests addressed to
any other host name, and requests sent by pages from other websites, so a web
page cannot drive it from your browser. It can read any folder you can, and
starts processes on your behalf, so do not expose it on a network.

## Troubleshooting

**The genome shows as not installed.**
Install it from the genome card, or from a terminal:
`SigProfilerMatrixGenerator install GRCh38`. If your genomes live elsewhere,
set the genome install folder (Advanced), or start the app with `--volume`.

**The folder picker does not open (Linux).**
The picker needs `zenity`, `kdialog` or a Python with Tkinter. Without them,
paste the path into the box under the button instead.

**The page stopped responding after a relaunch.**
Each launch uses a new address. Use the address the launcher printed, or run
the launcher again: if the app is already running, it prints that address.

**Charts are missing on the Results tab.**
Upgrade SigProfilerPlotting to 1.5.0 or later (see above).

**Where are the run records?**
In `~/.cache/sigprofilermatrixgenerator/jobs` on macOS and Linux, and
`%LOCALAPPDATA%\SigProfilerMatrixGenerator\jobs` on Windows. Each run's folder
holds its settings, its log and its result. The matrices themselves are only
in the run's output folder.
