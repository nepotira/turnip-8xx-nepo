#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""A8XX: Framebuffer attachment extent guard and render area window scissor safety.

Prevents the 64.5% (~65%) black viewport cutoff in emulators (e.g. Nyushu/Yuzu/Citron)
when presenting scaled frames (e.g. 2160p / 4K) to mobile displays (e.g. 2400x1080):
1. In tu_CreateFramebuffer: expands framebuffer dimensions to match attachment image
   extents if larger than pCreateInfo (fixing emulators creating framebuffers with 720p base
   dimensions for 2400x1080 swapchain views).
2. In tu6_sysmem_render_begin: ensures the emitted hardware GRAS_SC_WINDOW_SCISSOR covers
   the full render area extent (preventing clipping of the presentation blit quad).

Run from Mesa source root. Idempotent and safe to run multiple times.
"""
import sys

NAME = "63-tu-framebuffer-attachment-extent-guard.py"
DEV_TARGET = "src/freedreno/vulkan/tu_device.cc"
CMD_TARGET = "src/freedreno/vulkan/tu_cmd_buffer.cc"

DEV_MARKER = "/* Framebuffer attachment extent guard */"
CMD_MARKER = "/* Window scissor render area guard */"

DEV_OLD = """   if (!imageless) {
      for (uint32_t i = 0; i < pCreateInfo->attachmentCount; i++) {
         VkImageView _iview = pCreateInfo->pAttachments[i];
         struct tu_image_view *iview = tu_image_view_from_handle(_iview);
         framebuffer->attachments[i] = iview;
      }
   }"""

DEV_NEW = """   if (!imageless) {
      for (uint32_t i = 0; i < pCreateInfo->attachmentCount; i++) {
         VkImageView _iview = pCreateInfo->pAttachments[i];
         struct tu_image_view *iview = tu_image_view_from_handle(_iview);
         framebuffer->attachments[i] = iview;
         /* Framebuffer attachment extent guard:
          * In emulators (e.g. Nyushu/Yuzu/Citron), the presentation blit pass creates
          * a VkFramebuffer passing the base unscaled render dimensions (1280x720) while
          * attaching a full-screen swapchain image view (e.g. 2400x1080).
          * Expanding framebuffer dimensions to the attachment extent prevents hardware
          * GRAS_SC_WINDOW_SCISSOR from clipping the presentation draw call to 1280x720,
          * which otherwise leaves 64.5% (~65%) of a 2400x1080 display pitch black.
          */
         if (iview && iview->image) {
            framebuffer->width = MAX2(framebuffer->width, iview->image->vk.extent.width);
            framebuffer->height = MAX2(framebuffer->height, iview->image->vk.extent.height);
         }
      }
   }"""

CMD_OLD = """   assert(fb->width > 0 && fb->height > 0);
   tu6_emit_window_scissor<CHIP>(cs, 0, 0, fb->width - 1, fb->height - 1);
   tu6_emit_window_offset<CHIP>(cs, 0, 0);"""

CMD_NEW = """   assert(fb->width > 0 && fb->height > 0);
   /* Window scissor render area guard:
    * In direct/sysmem rendering passes, ensure the emitted window scissor is never
    * smaller than the active render area, preventing presentation blits from clipping.
    */
   uint32_t scissor_w = fb->width;
   uint32_t scissor_h = fb->height;
   if (cmd->state.render_areas[0].offset.x + cmd->state.render_areas[0].extent.width > scissor_w)
      scissor_w = cmd->state.render_areas[0].offset.x + cmd->state.render_areas[0].extent.width;
   if (cmd->state.render_areas[0].offset.y + cmd->state.render_areas[0].extent.height > scissor_h)
      scissor_h = cmd->state.render_areas[0].offset.y + cmd->state.render_areas[0].extent.height;

   tu6_emit_window_scissor<CHIP>(cs, 0, 0, scissor_w - 1, scissor_h - 1);
   tu6_emit_window_offset<CHIP>(cs, 0, 0);"""


def main():
    # 1. Patch tu_device.cc
    try:
        dev_content = open(DEV_TARGET, "r", encoding="utf-8").read()
    except OSError as e:
        print(f"{NAME}: WARNING cannot read {DEV_TARGET}: {e}; skipped")
        return 0

    if DEV_MARKER not in dev_content:
        if DEV_OLD in dev_content:
            dev_content = dev_content.replace(DEV_OLD, DEV_NEW, 1)
            try:
                with open(DEV_TARGET, "w", encoding="utf-8", newline="\n") as f:
                    f.write(dev_content)
                print(f"{NAME}: applied attachment extent guard in {DEV_TARGET}")
            except OSError as e:
                print(f"{NAME}: ERROR cannot write {DEV_TARGET}: {e}", file=sys.stderr)
                return 1
        else:
            print(f"{NAME}: WARNING anchor not found in {DEV_TARGET}; skipped")

    # 2. Patch tu_cmd_buffer.cc
    try:
        cmd_content = open(CMD_TARGET, "r", encoding="utf-8").read()
    except OSError as e:
        print(f"{NAME}: WARNING cannot read {CMD_TARGET}: {e}; skipped")
        return 0

    if CMD_MARKER not in cmd_content:
        if CMD_OLD in cmd_content:
            cmd_content = cmd_content.replace(CMD_OLD, CMD_NEW, 1)
            try:
                with open(CMD_TARGET, "w", encoding="utf-8", newline="\n") as f:
                    f.write(cmd_content)
                print(f"{NAME}: applied window scissor guard in {CMD_TARGET}")
            except OSError as e:
                print(f"{NAME}: ERROR cannot write {CMD_TARGET}: {e}", file=sys.stderr)
                return 1
        else:
            print(f"{NAME}: WARNING anchor not found in {CMD_TARGET}; skipped")

    print(f"{NAME}: safe/applied (framebuffer extent & window scissor guard active)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
