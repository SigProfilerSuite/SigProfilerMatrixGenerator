# Dashboard

A local web app for running SigProfilerMatrixGenerator without the command
line, and for browsing the matrices a run produces.

```bash
./launch_web.sh        # macOS/Linux, double-click launch_web.command on macOS
launch_web.bat          # Windows
# or, once SigProfilerMatrixGenerator is installed:
sigprofilermatrixgenerator-web
```

It opens a browser at `http://127.0.0.1:<port>/`.

## What it does

**New run.** Point at a folder of VCF/MAF/Txt files (or a single file), pick
a reference genome, and set the usual matrix generation options (exome,
bed_file, tsb_stat, ID89/ID476). The input path is recognized up front, so
you see the detected format and sample count before starting anything. A
genome that is not installed yet can be installed from this tab, or
installed automatically as part of starting a run.

**Monitor.** Each run is a subprocess, so the dashboard server keeps
responding even during a long run. Progress is read from the run's own log.
Stop ends the run's process.

**Results.** Point at an output folder (the one a run just produced, or one
made earlier from the command line) to list its SBS/DBS/ID/SV/CNV matrix
files. Selecting a file lists its samples and renders the chosen one as an
interactive Plotly chart, using SigProfilerPlotting's own renderers, so the
charts match what SigProfilerPlotting itself would draw. A matrix file can
always be downloaded directly, even when SigProfilerPlotting's dashboard
support is not installed.

## Design notes

**No new dependencies for the server itself.** It is `http.server` from the
standard library. The page is plain HTML, CSS, and JavaScript with no build
step. Plotly is served from the installed `plotly` package when available,
falling back to a CDN otherwise.

**Local only.** The server binds to the loopback interface and enforces two
checks on every request: the `Host` header must name this machine, which
stops DNS rebinding, and a cross-site `Origin` is refused. There is no
authentication. Do not bind this to a public interface.

**Why paths rather than uploads.** The server runs on the same machine as
the data, so pointing at a folder costs nothing and copies nothing. Folder
and file pickers use this operating system's own native dialog.

## Options

| Option | Default | Meaning |
|---|---|---|
| `--no-launch` | off | Start the server without opening a browser tab |
| `--reinstall` | off | Force a fresh dependency install (launcher scripts only) |
| `--stop` | off | Stop the running dashboard and exit |
| `--volume` | none | Reference genome install directory (same as the CLI's `--volume`) |

## Requirements for inline chart rendering

Rendering a matrix inline in the Results tab requires SigProfilerPlotting
1.5.0 or later, the first release with its `sigProfilerPlotting.web`
dashboard module. Matrices can still be listed and downloaded with an
older version installed; the Results tab says so when that module is not
available.
