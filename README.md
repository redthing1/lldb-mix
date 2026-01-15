# lldb-mix

Clean, modular LLDB context UI focused on binary-first debugging.

## Quick Start

```
command script import /path/to/lldb-mix/lldb_mix_loader.py
context
```

## Usage

```
context                       # show context once
context auto on|off|status    # toggle stop-hook printing
context layout regs code      # set pane order
dump [addr|reg|sp|pc] [len]   # hexdump memory at address/register
context save                  # persist settings to ~/.lldb-mix/config.json
context load                  # load settings from ~/.lldb-mix/config.json
```

## Samples

Build the sample binaries:

```
cmake -S samples -B samples/build
cmake --build samples/build --target sample_basic sample_branch
```

Run LLDB against a sample:

```
lldb samples/build/sample_basic
(lldb) command script import /path/to/lldb-mix/lldb_mix_loader.py
(lldb) breakpoint set -n main
(lldb) run
```

## Dev

Run unit tests and integration tests:

```
python3 -m unittest discover -s tests
```

The integration test builds samples via CMake and runs LLDB in batch mode.
