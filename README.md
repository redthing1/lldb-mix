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
context theme list|<name>     # list or set theme
dump [addr|reg|sp|pc] [len]   # hexdump memory at address/register
db/dw/dd/dq [addr|reg|sp|pc] [len]  # word-sized dumps (byte/word/dword/qword)
u [addr|reg|pc] [count]       # disassemble instructions
findmem ...                   # search memory across regions
rr [args...]                  # run to entrypoint (stop at entry)
bpm <module> <offset>         # break at module base + offset
bpt <addr|expr>               # temporary breakpoint
bpn                           # temporary breakpoint at next instruction
regions                       # list process memory regions (alias: vmmap)
antidebug                     # enable anti-anti-debugging callbacks
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

### Interactive Checklist

```
lldb samples/build/sample_basic
(lldb) command script import /path/to/lldb-mix/lldb_mix_loader.py
(lldb) breakpoint set -n main
(lldb) run
(lldb) context layout regs stack code
(lldb) context theme list
(lldb) dump sp 64
(lldb) u
(lldb) findmem -s hello -c 1
```

### Manual Validation Notes

- After `run`, the context output includes `[regs]`, `[stack]`, and `[code]` headers and registers appear in multiple columns.
- `context theme list` prints available themes; `context theme base` switches without errors.
- `dump sp 64` shows a `[dump] 0x... len=64 width=16` header and four hexdump lines.
- `db pc 64`/`dw pc 64`/`dd pc 64`/`dq pc 128` show word-sized dumps with ASCII on the right.
- `u` shows a `[u] 0x... count=...` header with disassembly lines.
- `findmem -s hello -c 1` prints a match line with `base=... off=...` pointing into the sample binary.
- `antidebug` prints an enable summary on macOS; on other platforms it may report failure to set breakpoints.
