import { state, assets, el, button, error, toast } from "../store.js";
import { api } from "../api.js";
import { modal, field, confirmAction } from "../core/modal.js";

export async function settingsDialog(refresh) {
  const settings = await api("get_settings");
  const m = modal("设置");
  const mac = settings.platform === "darwin";
  const path = field(m.content, "Photoshop 程序路径", settings.photoshop || "");
  path.placeholder = mac
    ? "例如 /Applications/Adobe Photoshop 2026/Adobe Photoshop 2026.app"
    : "例如 C:\\Program Files\\Adobe\\…\\Photoshop.exe";
  m.content.append(
    button(
      mac ? "选择 Photoshop.app" : "选择 Photoshop.exe",
      async () => {
        try {
          const p = await api("choose_photoshop");
          if (p) path.value = p;
        } catch (e) {
          m.err.textContent = e.message;
        }
      },
      "outline",
    ),
  );
  m.content.append(
    el("p", "", "可手动填写自定义位置；打开照片后仍需手动标记已修。"),
  );
  m.content.append(
    el(
      "div",
      "notice",
      "照片库：" +
        (settings.library || "尚未选择") +
        "\n照片保存在你选择的文件夹中；设置与缩略图缓存保存在本机" +
        (mac ? "应用数据目录。" : "AppData。"),
    ),
  );
  m.content.append(
    button(
      "重试未完成的文件恢复",
      async () => {
        try {
          m.dialog.close();
          await refresh("recover_pending");
        } catch (e) {
          error(e);
        }
      },
      "outline",
    ),
  );
  m.submit("保存", async () => {
    state.settings = await api("save_settings", {
      photoshop: path.value.trim(),
    });
    toast("设置已保存");
  });
}
