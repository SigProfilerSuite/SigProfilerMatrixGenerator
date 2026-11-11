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

!!! tip "Try an example first"
    Two examples that ship with SigProfilerMatrixGenerator can be filled in
    with one click. Each writes to its own folder under
    `~/SigProfilerMatrixGenerator_example/`.

    | Example | Input | Genome |
    |---|---|---|
    | **GRCh38 test set** | 9,631 simulated substitutions in one genome (VCF) | GRCh38 |
    | **BRCA example** | Simple text calls for four breast cancer genomes | GRCh37 |

    The GRCh38 test set doubles as a check of your installation: its SBS96
    matrix should match, channel for channel, the expected matrix that ships
    with the package (`scripts/Benchmark/GRCh38_bench_orig_96.txt`). Tick
    **PDF plots** to see SigProfilerPlotting's figures for it too. An example
    whose genome is not installed yet installs it first (see
    [Reference genome](#3-reference-genome)).

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

Either way, each type of mutation found gets its own subfolder (`SBS/`,
`DBS/`, `ID/`), with run logs in `logs/` and, when **PDF plots** is ticked,
SigProfilerPlotting's figures in `plots/`. SigProfilerMatrixGenerator also keeps a copy of the
input files it read, in an `input/` folder: inside the input folder by
default, or inside the output folder when one is set.

### 3. Reference genome

Choose the assembly your variants were called against. The card says whether
it is installed:

- **Install it now** starts the download in the background. The genome is
  large (about 3 GB for a human assembly) and is downloaded once.
- With **If it is not installed yet, install it when the run starts** ticked
  (the default), a run installs a missing genome as its first step.

Getting the genome right matters. Every mutation is checked against the
genome's reference base, so calls made on GRCh37 and run against
GRCh38 or CHM13-T2T mostly fail that check, and the run stops once more than
30% of mutations are skipped. When the calls name their assembly (a VCF's
`##reference` or `##assembly` header, the genome column of simple text, or a
MAF's `NCBI_Build`), the card warns if a different genome is chosen and
offers to switch. The BRCA example, for instance, names GRCh37. Calls that
do not name an assembly are not checked.

Installed genomes are also listed in the sidebar; clicking one selects it.
The status describes the genome install folder the run will use: the one set
under **Advanced** in the Matrices card if there is one, otherwise the folder
the app was started with. Changing that field (press Enter, or use Browse)
updates the status straight away.

!!! note
    The genome card only checks that each of the genome's files is present.
    A run checks the files against their expected checksums before it starts.
    If they do not match, the run downloads the genome again when automatic
    install is ticked; otherwise it stops and says the files do not match.

### 4. Matrices

SigProfilerMatrixGenerator writes the standard matrices for each type of
mutation present in your calls: SBS for single base substitutions, DBS for
doublet base substitutions and ID for small insertions and deletions. A cohort
with no doublet substitutions, for example, gets no DBS matrices. The options
add to the standard set:

| Option | What it does | Python / CLI equivalent |
|---|---|---|
| PDF plots | SigProfilerPlotting draws every SBS, DBS and ID matrix the run writes, one page per sample, into `plots/`. Adds time for large cohorts | `plot=True` / `--plot` |
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

SigProfilerMatrixGenerator skips mutations it cannot place (a reference base
that does not match the genome, a position past the end of a chromosome, and
so on) and lists each one in its own log, in the output folder's `logs/`, not
in the log shown here. When a run skipped any, the Monitor tab counts them by
reason and names that log file.

Each run is a separate process, so a long run never slows the page, and runs
started here keep their records after the app is restarted. Every run, past
and present, is listed in the sidebar under **Runs**; the Monitor tab shows a
count of the ones still in progress.

## Exploring results

Open a finished run from the Monitor tab, or click **Open a results folder**
in the sidebar and choose the folder a run wrote its matrices into (the one
holding the `SBS`, `DBS` and `ID` subfolders). That includes folders written
earlier by the Python function or the command line. It only reads the folder.

This is not the **Output folder** field of a new run, which sets where a run
will write.

On a narrow screen, such as a phone, the sidebar moves below the main area,
so its runs list and genome list are further down the page. The Results tab
then shows its own **Open a results folder** button.

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
- **PDF plots:** the figures SigProfilerPlotting drew, when the run had
  **PDF plots** ticked. **Open** shows a PDF in a new browser tab;
  **Download** saves it.
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
this machine (`127.0.0.1`) and has no login, so it protects itself in other
ways:

- It answers only requests addressed to this machine by name (`127.0.0.1` or
  `localhost`), which stops a website from reaching it through DNS tricks.
- Anything that acts (starting or stopping a run, installing a genome,
  opening a file picker, quitting) must come from the app's own page: from
  exactly its address and port, and carrying a secret written into that page
  when the app starts. A website, or a page served by another program on this
  computer, can send requests to the app but cannot read its page, so it
  cannot supply the secret.
- Every other request only reads (the page itself, run progress, matrix
  files), and your browser does not let other websites see the replies.

The app can read any folder you can, and starts processes on your behalf, so
do not expose it on a network.

## Troubleshooting

**The genome shows as not installed.**
Install it from the genome card, or from a terminal:
`SigProfilerMatrixGenerator install GRCh38`. If your genomes live elsewhere,
set the genome install folder under Advanced and press Enter, or start the
app with `--volume`. If the `SIGPROFILERMATRIXGENERATOR_VOLUME` environment
variable is set, it takes precedence over both.

**The run failed: "More than 30% of mutations were skipped".**
Look at the reasons the Monitor tab lists. If most are "The reference base
does not match the reference genome", the calls were made against a different
genome from the one chosen: choose the genome they were called against and run
again.

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
