import os
import json
import cv2
import numpy as np
from fpdf import FPDF
import tempfile


class Evaluator:
    def __init__(self, json_path: str, tobako_dir: str, raimu_dir: str):
        self.json_path = json_path
        self.tobako_dir = tobako_dir
        self.raimu_dir = raimu_dir
        self.japanese_font_path = "ipaexg.ttf"

    def _overlay_images(self, path1, path2):
        """QRの黒部分をグラデーションで色付けして重ね合わせる"""
        img1 = cv2.imread(path1, cv2.IMREAD_GRAYSCALE)
        img2 = cv2.imread(path2, cv2.IMREAD_GRAYSCALE)

        if img1 is None or img2 is None:
            return None

        # サイズを合わせる
        h = min(img1.shape[0], img2.shape[0])
        w = min(img1.shape[1], img2.shape[1])
        img1 = cv2.resize(img1, (w, h))
        img2 = cv2.resize(img2, (w, h))

        # 背景除去: 白(>=250)は透明扱い
        mask1 = img1 < 250
        mask2 = img2 < 250

        # toba (黄色系に着色) → 明るい部分は薄く、暗い部分は濃く
        toba_color = np.zeros((h, w, 3), dtype=np.uint8)
        toba_color[..., 0] = 0  # B
        toba_color[..., 1] = img1  # G (元の濃さを反映)
        toba_color[..., 2] = img1 // 2  # R (少し抑える)
        toba_color[~mask1] = (255, 255, 255)  # 背景は白

        # raimu (青系に着色)
        raimu_color = np.zeros((h, w, 3), dtype=np.uint8)
        raimu_color[..., 0] = img2  # B
        raimu_color[..., 1] = img2 // 2  # G
        raimu_color[..., 2] = 0  # R
        raimu_color[~mask2] = (255, 255, 255)

        # 半透明で重ねる
        overlay = cv2.addWeighted(toba_color, 0.5, raimu_color, 0.5, 0)

        return overlay

    def _create_pdf_report(self, evaluation_data: list):
        pdf = FPDF(orientation="P", unit="mm", format="A4")

        try:
            pdf.add_font("IPAexGothic", "", self.japanese_font_path, uni=True)
            pdf.set_font("IPAexGothic", "", 10)
        except Exception:
            pdf.set_font("helvetica", "", 10)

        pdf.add_page()

        pairs_per_row = 2
        img_w = 60
        img_h = 60
        margin_x = 15
        margin_y = 15
        pair_spacing_x = 90
        pair_spacing_y = 80

        max_rows_per_page = int((297 - margin_y * 2) // pair_spacing_y)

        for idx, data in enumerate(evaluation_data):
            page_index = idx // (pairs_per_row * max_rows_per_page)
            pos_in_page = idx % (pairs_per_row * max_rows_per_page)

            row = pos_in_page // pairs_per_row
            col = pos_in_page % pairs_per_row

            if pos_in_page == 0 and idx > 0:
                pdf.add_page()

            x = margin_x + col * pair_spacing_x
            y = margin_y + row * pair_spacing_y

            filename = data["file"]
            file_number = os.path.splitext(filename)[0]

            original_path = os.path.join(self.tobako_dir, filename)
            enhanced_path = os.path.join(self.raimu_dir, filename)

            overlay = self._overlay_images(original_path, enhanced_path)
            if overlay is not None:
                with tempfile.NamedTemporaryFile(
                    suffix=".png", delete=False
                ) as tmpfile:
                    tmp_path = tmpfile.name
                    cv2.imwrite(tmp_path, overlay)
                    pdf.image(tmp_path, x=x, y=y, w=img_w, h=img_h)
                    os.remove(tmp_path)

            decode_text = data.get("raimu", "") or data.get("toba", "")
            text = f"No.{file_number} de.{decode_text}"

            pdf.set_xy(x, y + img_h + 2)
            pdf.cell(img_w, 8, text, align="C")

        pdf.output("evaluate/overlay_report.pdf")
        print(
            "オーバーレイ評価レポートが 'evaluate/overlay_report.pdf' に保存されました。"
        )

    def run(self):
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                evaluation_data = json.load(f)
        except FileNotFoundError:
            print(f"エラー: '{self.json_path}' が見つかりません。")
            return

        self._create_pdf_report(evaluation_data)


def main():
    evaluator = Evaluator(
        json_path="evaluate.json",
        tobako_dir="qr_tobakosan",
        raimu_dir="qr_raimu",
    )
    evaluator.run()


if __name__ == "__main__":
    main()
