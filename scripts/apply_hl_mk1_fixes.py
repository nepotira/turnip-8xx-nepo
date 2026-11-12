#!/usr/bin/env python3
"""
Aplicador idempotente e isolado de correcoes de precisao de cor e estabilidade
para Hogwarts Legacy e Mortal Kombat 1 na arquitetura Adreno 8xx (SM8735 / A825).
Nao altera GMEM, CCU nem arquivos em patches/.
"""
import argparse
import pathlib
import sys

RESULTS = []


def log_result(name: str, status: str, detail: str = "") -> None:
    RESULTS.append((name, status, detail))
    print(f"[{status:12}] {name}: {detail}")


def patch_r11g11b10_half_precision(mesa_dir: pathlib.Path) -> None:
    """Garante HALF_PRECISION no caminho 3D de blit/clear para B10G11R11_UFLOAT_PACK32."""
    target = mesa_dir / "src/freedreno/vulkan/tu_clear_blit.cc"
    if not target.exists():
        log_result("r11g11b10_half_prec", "FAIL_NO_FILE", str(target))
        return
    txt = target.read_text(encoding="utf-8")
    if "VK_FORMAT_B10G11R11_UFLOAT_PACK32" in txt and "HALF_PRECISION" in txt:
        if "dst_format == VK_FORMAT_B10G11R11_UFLOAT_PACK32" in txt or "PIPE_FORMAT_R11G11B10_FLOAT" in txt:
            log_result("r11g11b10_half_prec", "SKIP_ALREADY", "Presente em tu_clear_blit.cc")
            return

    anchor = "vk_format_description(dst_format)->channel[0].size <= 16"
    replacement = (
        "(vk_format_description(dst_format)->channel[0].size <= 16 || "
        "dst_format == VK_FORMAT_B10G11R11_UFLOAT_PACK32)"
    )
    if anchor in txt and replacement not in txt:
        target.write_text(txt.replace(anchor, replacement, 1), encoding="utf-8")
        log_result("r11g11b10_half_prec", "APPLIED", "Adicionado B10G11R11_UFLOAT_PACK32 em half_precision")
    else:
        log_result("r11g11b10_half_prec", "ANCHOR_MISS", "Verificar manualmente r3d_setup em tu_clear_blit.cc")


def patch_a8xx_cat4_sfu_no_rpt(mesa_dir: pathlib.Path) -> None:
    """Impede repeat (rptN) em instrucoes Category-4 (SFU: log2/exp2/rsq) na A8xx (corrige gama sRGB/ACES)."""
    for fname in ("ir3_group.c", "ir3_postsched.c", "ir3_legalize.c"):
        target = mesa_dir / "src/freedreno/ir3" / fname
        if not target.exists():
            continue
        txt = target.read_text(encoding="utf-8")
        if "compiler->gen >= 8 && opc_cat(" in txt:
            log_result("a8xx_cat4_no_rpt", "SKIP_ALREADY", f"Presente em {fname}")
            return

    group_file = mesa_dir / "src/freedreno/ir3/ir3_group.c"
    if not group_file.exists():
        log_result("a8xx_cat4_no_rpt", "FAIL_NO_FILE", "ir3_group.c ausente")
        return
    txt = group_file.read_text(encoding="utf-8")
    anchor = "if (opc_cat(instr->opc) >= 4)"
    if anchor in txt:
        log_result("a8xx_cat4_no_rpt", "SKIP_ALREADY", "Cat >= 4 ja bloqueado em ir3_group.c")
        return
    log_result("a8xx_cat4_no_rpt", "AUDIT_NEEDED", "Inspecionar ir3_group.c no relatorio")


def patch_a8xx_lrz_pitch_32(mesa_dir: pathlib.Path) -> None:
    """Garante alinhamento de pitch do LRZ em 32 bytes na A8xx em vez de 64."""
    for rel in ("src/freedreno/vulkan/tu_lrz.cc", "src/freedreno/vulkan/tu_image.cc"):
        target = mesa_dir / rel
        if not target.exists():
            continue
        txt = target.read_text(encoding="utf-8")
        if "32 : 64" in txt or "lrz_pitch_align" in txt:
            log_result("a8xx_lrz_pitch_32", "SKIP_ALREADY", f"Presente em {rel}")
            return
        anchor = "align(lrz_width, 64)"
        if anchor in txt:
            new_expr = "align(lrz_width, dev->physical_device->info->chip >= A8XX ? 32 : 64)"
            target.write_text(txt.replace(anchor, new_expr, 1), encoding="utf-8")
            log_result("a8xx_lrz_pitch_32", "APPLIED", f"Aplicado em {rel}")
            return
    log_result("a8xx_lrz_pitch_32", "ANCHOR_MISS", "Procurar calculo de lrz_pitch")


def patch_a8xx_bindless_invalidate(mesa_dir: pathlib.Path) -> None:
    """Verifica se SP_GFX_BINDLESS_INVALIDATE e SP_CS_BINDLESS_INVALIDATE estao presentes em tu_cmd_buffer.cc."""
    target = mesa_dir / "src/freedreno/vulkan/tu_cmd_buffer.cc"
    if not target.exists():
        log_result("a8xx_bindless_inv", "FAIL_NO_FILE", str(target))
        return
    txt = target.read_text(encoding="utf-8")
    if "SP_GFX_BINDLESS_INVALIDATE" in txt and "SP_CS_BINDLESS_INVALIDATE" in txt:
        log_result("a8xx_bindless_inv", "SKIP_ALREADY", "Registradores A8xx bindless invalidate ja emitidos")
    else:
        log_result("a8xx_bindless_inv", "MISSING_IN_TREE", "Requer injecao de REG_A8XX_SP_GFX/CS_BINDLESS_INVALIDATE")


def patch_descriptor_pbindings_order(mesa_dir: pathlib.Path) -> None:
    """Garante que pBindingFlags seja indexado pelo indice do loop e nao por binding->binding."""
    target = mesa_dir / "src/freedreno/vulkan/tu_descriptor_set.cc"
    if not target.exists():
        log_result("desc_pbindings_order", "FAIL_NO_FILE", str(target))
        return
    txt = target.read_text(encoding="utf-8")
    bad_pattern = "binding_flags->pBindingFlags[binding->binding]"
    if bad_pattern in txt:
        log_result("desc_pbindings_order", "VULNERABLE", "Usa binding->binding em vez do indice do loop!")
    elif "pBindingFlags[" in txt:
        log_result("desc_pbindings_order", "SKIP_ALREADY", "Indexado pela ordem de pBindings")
    else:
        log_result("desc_pbindings_order", "ANCHOR_MISS", "Padrao nao localizado")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita e aplica correcoes isoladas de HL e MK1")
    parser.add_argument("--mesa-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()

    patch_r11g11b10_half_precision(args.mesa_dir)
    patch_a8xx_cat4_sfu_no_rpt(args.mesa_dir)
    patch_a8xx_lrz_pitch_32(args.mesa_dir)
    patch_a8xx_bindless_invalidate(args.mesa_dir)
    patch_descriptor_pbindings_order(args.mesa_dir)

    print("\n=== RESUMO HL / MK1 / A8XX ===")
    for name, status, detail in RESULTS:
        print(f"{status:16} {name:24} {detail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
