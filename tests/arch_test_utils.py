from __future__ import annotations

from lldb_mix.arch.info import ArchInfo
from lldb_mix.arch.reginfo import RegInfo
from lldb_mix.arch.view import ArchView


def make_arch_view(
    profile,
    gpr_names: tuple[str, ...] | None = None,
    ptr_size: int | None = None,
    pc_value: int | None = None,
    sp_value: int | None = None,
) -> ArchView:
    regs = gpr_names or getattr(profile, "gpr_names", ())
    reg_sets = {
        "General Purpose Registers": [
            RegInfo(name=reg, byte_size=ptr_size or getattr(profile, "ptr_size", 0))
            for reg in regs
        ]
    }
    info = ArchInfo.from_register_sets(
        triple=getattr(profile, "name", ""),
        arch_name=getattr(profile, "name", ""),
        ptr_size=ptr_size or getattr(profile, "ptr_size", 0),
        reg_sets=reg_sets,
        pc_value=pc_value,
        sp_value=sp_value,
    )
    return ArchView(info=info, profile=profile)
