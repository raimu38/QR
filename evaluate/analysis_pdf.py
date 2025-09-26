import os
import json
import cv2
import textwrap
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle
import matplotlib.patches as mpatches


class QRAnalysisReport:
    def __init__(
        self,
        json_path="evaluate.json",
        tobako_dir="qr_tobakosan",
        raimu_dir="qr_raimu",
        wrap_width: int = 40,
        bg_color: str = "#ffffff",  # 背景色（白）
        panel_color: str = "#f5f5f5",  # 情報パネル背景（薄グレー）
    ):
        self.json_path = json_path
        self.tobako_dir = tobako_dir
        self.raimu_dir = raimu_dir
        self.wrap_width = wrap_width
        self.bg_color = bg_color
        self.panel_color = panel_color

    def _wrap(self, s: str):
        if s is None:
            return "None"
        s = str(s).strip()
        # 半角スペースを削除
        s = s.replace(" ", "")

        return (
            "\n".join(textwrap.wrap(s, self.wrap_width))
            if len(s) > self.wrap_width
            else s
        )

    def _create_info_panel(self, ax, data, filename):
        """最小限に整えた情報パネル（読みやすさ重視）"""
        ax.axis("off")
        ax.set_facecolor(self.bg_color)

        # パネル領域（カード）
        margin = 0.03
        px, py = margin, margin
        pw, ph = 1 - 2 * margin, 1 - 2 * margin
        panel = Rectangle(
            (px, py),
            pw,
            ph,
            transform=ax.transAxes,
            facecolor=self.panel_color,
            edgecolor="#1a1f25",
            linewidth=1,
        )
        ax.add_patch(panel)

        # テキストカラー（ライト背景向け）
        title_color = "#111111"
        label_color = "#101824"
        value_color = "#0b0b0b"
        mono = "monospace"

        # ヘッダ: ファイル名（左上）
        file_number = os.path.splitext(filename)[0]
        ax.text(
            px + 0.03,
            py + ph - 0.06,
            f"#{file_number}.png",
            transform=ax.transAxes,
            fontsize=13,
            fontweight="bold",
            ha="left",
            color=title_color,
            bbox=dict(boxstyle="round,pad=0.1", fc="#ffffff", ec="none"),
        )

        # セクション表示（縦余白を広めに）
        start_y = py + ph - 0.14
        section_gap = 0.20

        # TOBA RESULT
        toba_text = self._wrap(data.get("toba", "None"))
        ax.text(
            px + 0.03,
            start_y,
            "TOBA RESULT",
            transform=ax.transAxes,
            fontsize=9,
            fontweight="bold",
            color=label_color,
            va="top",
        )
        ax.text(
            px + 0.03,
            start_y - 0.035,
            toba_text,
            transform=ax.transAxes,
            fontsize=9,
            color=value_color,
            va="top",
            family=mono,
        )

        # RAIMU RESULT (下へ余白をとる)
        raimu_y = start_y - section_gap
        raimu_text = self._wrap(data.get("raimu", "None"))
        ax.text(
            px + 0.03,
            raimu_y,
            "RAIMU RESULT",
            transform=ax.transAxes,
            fontsize=9,
            fontweight="bold",
            color=label_color,
            va="top",
        )
        ax.text(
            px + 0.03,
            raimu_y - 0.035,
            raimu_text,
            transform=ax.transAxes,
            fontsize=9,
            color=value_color,
            va="top",
            family=mono,
        )
        # MATCHステータスをRAIMU RESULTの下に配置
        match_flag = data.get("match", False)
        match_face = "#16a34a" if match_flag else "#ef4444"
        ax.text(
            px + 0.03,
            raimu_y - 0.08,
            f"MATCH: {match_flag}",
            transform=ax.transAxes,
            fontsize=9,
            fontweight="bold",
            color=match_face,
            va="top",
        )

        # メタデータ（任意、小さく表示）
        meta = data.get("optimal_params", {})
        if meta:
            meta_y = raimu_y - section_gap - 0.05
            ax.text(
                px + 0.03,
                meta_y,
                "OPTIMAL PARAMS",
                transform=ax.transAxes,
                fontsize=9,
                fontweight="bold",
                color=label_color,
                va="top",
            )
            # パラメータをkey: value形式で表示
            cur_y = meta_y - 0.035
            params_text = self._wrap(json.dumps(meta))
            ax.text(
                px + 0.03,
                cur_y,
                params_text,
                transform=ax.transAxes,
                fontsize=8,
                color=value_color,
                va="top",
                family=mono,
            )

    def generate_pdf(self, output_path="evaluate/analysis_repost.pdf"):
        # JSONロード
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(f"JSON file not found: {self.json_path}")

        with open(self.json_path, "r", encoding="utf-8") as f:
            evaluation_data = json.load(f)

        # 軽い（白背景）スタイル
        plt.style.use("default")

        with PdfPages(output_path) as pdf:
            for data in evaluation_data:
                filename = data.get("file")
                if not filename:
                    continue

                original_path = os.path.join(self.tobako_dir, filename)
                enhanced_path = os.path.join(self.raimu_dir, filename)

                fig = plt.figure(figsize=(12, 4), facecolor=self.bg_color)
                gs = GridSpec(1, 3, figure=fig, width_ratios=[1, 1, 0.9], wspace=0.25)

                # 左: ORIGINAL
                ax1 = fig.add_subplot(gs[0, 0])
                ax1.set_facecolor(self.bg_color)
                if os.path.exists(original_path):
                    img1 = cv2.imread(original_path)
                    if img1 is not None:
                        img1 = cv2.cvtColor(img1, cv2.COLOR_BGR2RGB)
                        ax1.imshow(img1)
                ax1.axis("off")
                ax1.set_title(
                    "ORIGINAL (Toba)", fontsize=11, fontweight="bold", color="#111111"
                )

                # 中央: ENHANCED
                ax2 = fig.add_subplot(gs[0, 1])
                ax2.set_facecolor(self.bg_color)
                if os.path.exists(enhanced_path):
                    img2 = cv2.imread(enhanced_path)
                    if img2 is not None:
                        img2 = cv2.cvtColor(img2, cv2.COLOR_BGR2RGB)
                        ax2.imshow(img2)
                ax2.axis("off")
                ax2.set_title(
                    "ENHANCED (Raimu)", fontsize=11, fontweight="bold", color="#111111"
                )

                # 右: INFO PANEL
                ax3 = fig.add_subplot(gs[0, 2])
                self._create_info_panel(ax3, data, filename)

                plt.tight_layout()
                pdf.savefig(fig, dpi=150, facecolor=fig.get_facecolor())
                plt.close(fig)

        print(f"analysis PDF saved to '{output_path}'")


def main():
    # 必要に応じてパスを調整してください
    report = QRAnalysisReport(
        json_path="evaluate.json",
        tobako_dir="qr_tobakosan",
        raimu_dir="qr_raimu",
        wrap_width=36,
        bg_color="#ffffff",
        panel_color="#fefefe",
    )
    report.generate_pdf("evaluate/analysis_report.pdf")


if __name__ == "__main__":
    main()
