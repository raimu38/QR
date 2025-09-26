import os
import json
from fpdf import FPDF


class Evaluator:
    def __init__(self, json_path: str, tobako_dir: str, raimu_dir: str):
        self.json_path = json_path
        self.tobako_dir = tobako_dir
        self.raimu_dir = raimu_dir
        self.japanese_font_path = "ipaexg.ttf"

    def _create_pdf_report(self, evaluation_data: list):
        pdf = FPDF(orientation="P", unit="mm", format="A4")

        try:
            pdf.add_font("IPAexGothic", "", self.japanese_font_path, uni=True)
            pdf.set_font("IPAexGothic", "", 10)
        except Exception:
            pdf.set_font("helvetica", "", 10)

        pdf.add_page()

        # レイアウト設定
        pairs_per_row = 2
        img_w = 40
        img_h = 40
        margin_x = 15
        margin_y = 15
        pair_spacing_x = 90
        pair_spacing_y = 65
        gap_between_imgs = 5

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

            if os.path.exists(original_path):
                pdf.image(original_path, x=x, y=y, w=img_w, h=img_h)
            if os.path.exists(enhanced_path):
                pdf.image(
                    enhanced_path, x=x + img_w + gap_between_imgs, y=y, w=img_w, h=img_h
                )

            decode_text = data.get("raimu", "") or data.get("toba", "")
            decode_text = " ".join(decode_text.split())
            text = f"No.{file_number} De.{decode_text}"

            pdf.set_xy(x, y + img_h + 5)
            pdf.cell(img_w * 2 + gap_between_imgs, 8, text, align="C")

        pdf.output("evaluate/evaluation_report.pdf")
        print("評価レポートが 'evaluate/evaluation_report.pdf' に保存されました。")

    def run(self):
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                evaluation_data = json.load(f)
        except FileNotFoundError:
            print(f"エラー: '{self.json_path}' が見つかりません。")
            return

        self._create_pdf_report(evaluation_data)


# --- ここを追加 ---
def main():
    evaluator = Evaluator(
        json_path="evaluate.json",
        tobako_dir="qr_tobakosan",
        raimu_dir="qr_raimu",
    )
    evaluator.run()


if __name__ == "__main__":
    main()
