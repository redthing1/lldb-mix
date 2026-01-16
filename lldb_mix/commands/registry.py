from __future__ import annotations

from dataclasses import dataclass

from lldb_mix.ui.console import err


@dataclass(frozen=True)
class AliasSpec:
    name: str
    help: str | None = None


@dataclass(frozen=True)
class CommandSpec:
    name: str
    handler: str
    help: str
    aliases: tuple[AliasSpec, ...] = ()

    @property
    def module(self) -> str:
        return self.handler.rsplit(".", 1)[0]


COMMANDS: tuple[CommandSpec, ...] = (
    CommandSpec(
        name="context",
        handler="lldb_mix.commands.context.cmd_context",
        help="Render mix context view.",
        aliases=(AliasSpec("ctx", "Alias for context."),),
    ),
    CommandSpec(
        name="conf",
        handler="lldb_mix.commands.conf.cmd_conf",
        help="Show or update mix settings.",
    ),
    CommandSpec(
        name="dump",
        handler="lldb_mix.commands.dump.cmd_dump",
        help="Dump memory (hexdump).",
    ),
    CommandSpec(
        name="db",
        handler="lldb_mix.commands.dump.cmd_db",
        help="Dump memory (bytes).",
    ),
    CommandSpec(
        name="dw",
        handler="lldb_mix.commands.dump.cmd_dw",
        help="Dump memory (words).",
    ),
    CommandSpec(
        name="dd",
        handler="lldb_mix.commands.dump.cmd_dd",
        help="Dump memory (dwords).",
    ),
    CommandSpec(
        name="dq",
        handler="lldb_mix.commands.dump.cmd_dq",
        help="Dump memory (qwords).",
    ),
    CommandSpec(
        name="u",
        handler="lldb_mix.commands.disasm.cmd_u",
        help="Disassemble around an address.",
    ),
    CommandSpec(
        name="findmem",
        handler="lldb_mix.commands.search.cmd_findmem",
        help="Search memory for a pattern.",
    ),
    CommandSpec(
        name="rr",
        handler="lldb_mix.commands.run.cmd_rr",
        help="Launch target and stop at entry.",
    ),
    CommandSpec(
        name="bpm",
        handler="lldb_mix.commands.breakpoints.cmd_bpm",
        help="Breakpoint at module+offset.",
    ),
    CommandSpec(
        name="bpt",
        handler="lldb_mix.commands.breakpoints.cmd_bpt",
        help="Thread-local one-shot breakpoint.",
    ),
    CommandSpec(
        name="bpn",
        handler="lldb_mix.commands.breakpoints.cmd_bpn",
        help="Breakpoint at next instruction.",
    ),
    CommandSpec(
        name="regions",
        handler="lldb_mix.commands.regions.cmd_regions",
        help="List memory regions.",
        aliases=(AliasSpec("vmmap", "Alias for regions."),),
    ),
    CommandSpec(
        name="antidebug",
        handler="lldb_mix.commands.antidebug.cmd_antidebug",
        help="Install common anti-debug hooks.",
    ),
    CommandSpec(
        name="skip",
        handler="lldb_mix.commands.skip.cmd_skip",
        help="Advance PC by N instructions.",
    ),
    CommandSpec(
        name="watch",
        handler="lldb_mix.commands.watch.cmd_watch",
        help="Manage watch list entries.",
    ),
    CommandSpec(
        name="bp",
        handler="lldb_mix.commands.bp.cmd_bp",
        help="List/enable/disable/clear breakpoints.",
    ),
    CommandSpec(
        name="sess",
        handler="lldb_mix.commands.session.cmd_session",
        help="Save or load mix sessions.",
    ),
    CommandSpec(
        name="patch",
        handler="lldb_mix.commands.patch.cmd_patch",
        help="Patch memory bytes at an address.",
    ),
    CommandSpec(
        name="ret",
        handler="lldb_mix.commands.ret.cmd_ret",
        help="Return from the current function.",
    ),
    CommandSpec(
        name="deref",
        handler="lldb_mix.commands.deref.cmd_deref",
        help="Follow pointer chain for an address.",
    ),
)


def register_commands(debugger) -> None:
    loaded = _import_command_modules(debugger)
    for spec in COMMANDS:
        if spec.module not in loaded:
            continue
        _register_command(debugger, _command_add(spec))
        for alias in spec.aliases:
            _register_command(debugger, _command_alias(alias, spec.name))


def _import_command_modules(debugger) -> set[str]:
    try:
        import lldb
    except Exception as exc:
        err(f"failed to import lldb for command imports: {exc}")
        return set()

    loaded: set[str] = set()
    modules = {spec.module for spec in COMMANDS}
    for module in sorted(modules):
        res = lldb.SBCommandReturnObject()
        debugger.GetCommandInterpreter().HandleCommand(
            f"command script import {module}",
            res,
        )
        if res.Succeeded():
            loaded.add(module)
            continue
        error = res.GetError() or res.GetOutput() or ""
        message = error.strip() or "unknown error"
        err(f"failed to import {module}: {message}")
    return loaded


def _command_add(spec: CommandSpec) -> str:
    help_text = _escape_help(spec.help)
    if help_text:
        return (
            f'command script add -h "{help_text}" -f {spec.handler} {spec.name}'
        )
    return f"command script add -f {spec.handler} {spec.name}"


def _command_alias(alias: AliasSpec, target: str) -> str:
    help_text = _escape_help(alias.help or f"Alias for {target}.")
    return f'command alias -h "{help_text}" -- {alias.name} {target}'


def _register_command(debugger, command: str) -> None:
    try:
        import lldb
    except Exception as exc:
        err(f"failed to import lldb for command registration: {exc}")
        return

    res = lldb.SBCommandReturnObject()
    debugger.GetCommandInterpreter().HandleCommand(command, res)
    if res.Succeeded():
        return
    error = res.GetError() or ""
    if _is_duplicate_command_error(error):
        return
    if error:
        err(f"failed to register command: {command} ({error.strip()})")
        return
    err(f"failed to register command: {command}")


def _is_duplicate_command_error(error: str) -> bool:
    text = error.lower()
    return "already exists" in text or "already a command" in text


def _escape_help(text: str) -> str:
    return text.replace("\n", " ").replace('"', '\\"').strip()
