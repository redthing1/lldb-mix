# lldb-mix

Clean, modular LLDB context UI focused on binary-first debugging.

## install

```sh
./scripts/install.py
```

## quick start

```
lldb /path/to/bin
(lldb) context
```

## Usage

```
context                       # show context once
conf list                     # list settings
conf get <key>                # show a setting
conf set <key> <value...>     # update a setting
conf set abi auto|sysv|win64|aapcs64  # override ABI selection (applies per-arch)
conf default                 # reset settings to defaults (not persisted)
conf save                     # persist settings (OS-specific config path)
conf load                     # load settings (OS-specific config path)
dump [addr|reg|sp|pc] [len]   # hexdump memory at address/register
db/dw/dd/dq [addr|reg|sp|pc] [len]  # word-sized dumps (byte/word/dword/qword)
u [addr|reg|pc] [count]       # disassemble instructions
findmem ...                   # search memory across regions
rr [args...]                  # run to entrypoint (stop at entry)
skip [count]                  # skip N instructions (default 1)
deref [addr|reg|expr] [-d n]  # explain an address via deref chain
patch ...                     # patch memory (write/nop/int3/null/restore/list)
ret [value]                   # return from current frame
watch add <expr> [label]      # add watch expression
watch list|del|clear          # manage watches
bp list|enable|disable|clear  # breakpoint management
sess save|load|list           # persist or restore watches/breakpoints
bpm <module> <offset>         # break at module base + offset
bpt <addr|expr>               # temporary breakpoint
bpn                           # temporary breakpoint at next instruction
regions                       # list process memory regions (alias: vmmap)
antidebug                     # enable anti-anti-debugging callbacks
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
(lldb) conf set layout regs args stack watch code
(lldb) conf list
(lldb) deref $sp
(lldb) watch add $sp stack
(lldb) sess save
(lldb) dump sp 64
(lldb) u
(lldb) skip
(lldb) patch nop $pc 1
(lldb) patch list
(lldb) patch restore $pc
(lldb) sess load
(lldb) findmem -s hello -c 1
(lldb) ret 0
```

### Manual Validation Notes

- After `run`, the context output includes a `[lldb-mix]` header framed by separator lines, plus `[regs]`, `[args]`, `[stack]`, and `[code]` sections; registers appear in multiple columns.
- On wider terminals, panes pack into two columns (for example, regs on the left and args+stack on the right) while the code pane stays full-width.
- `conf set abi aapcs64` (or `sysv`/`win64` on x86_64) updates the args pane title to show the active ABI.
- `conf list` prints available settings; `conf set theme base` switches without errors.
- `conf set clear_screen on` clears the terminal before each context output.
- `dump sp 64` shows a `[dump] 0x... len=64 width=16` header and four hexdump lines.
- `skip` prints a `[lldb-mix] skip 1 -> 0x...` line and updates the PC.
- `deref $sp` prints a `[deref]` header with region, symbol, and deref chain info.
- After `watch add $sp`, the `[watch]` pane shows the watch entry when the layout includes `watch` (the pane hides when there are no watches).
- `sess save` writes a session file and `sess load` restores watches and breakpoints.
- `patch nop $pc 1` reports the patched address and `patch restore $pc` restores the original bytes.
- `ret 0` returns from the current frame and prints a confirmation line.
- `db pc 64`/`dw pc 64`/`dd pc 64`/`dq pc 128` show word-sized dumps with ASCII on the right.
- `u` shows a `[u] 0x... count=...` header with disassembly lines.
- `findmem -s hello -c 1` prints a match line with `base=... off=...` pointing into the sample binary.
- `antidebug` prints an enable summary on macOS; on other platforms it may report failure to set breakpoints.
