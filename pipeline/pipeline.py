import os
import json
import cv2
from pipeline.qr_enhancer import QREnhancer
from pipeline.qr_decode import QRCodeDecoder


class QRPipeline:
    def __init__(self, tobako_dir: str, raimu_dir: str, enhancer_params: dict = None):
        self.tobako_dir = tobako_dir
        self.raimu_dir = raimu_dir
        # enhancer_params を受け取れるように
        self.enhancer = QREnhancer(**(enhancer_params or {}))
        self.decoder = QRCodeDecoder()

    def run(self):
        evaluation_results = []
        if not os.path.exists(self.tobako_dir):
            print(
                f"エラー: 元の画像ディレクトリ '{self.tobako_dir}' が見つかりません。"
            )
            return
        if not os.path.exists(self.raimu_dir):
            os.makedirs(self.raimu_dir)
            print(f"新しいディレクトリ '{self.raimu_dir}' を作成しました。")

        # ファイル名をソートして処理順を保証
        sorted_files = sorted(
            os.listdir(self.tobako_dir), key=lambda x: int(os.path.splitext(x)[0])
        )

        for filename in sorted_files:
            if filename.endswith((".png", ".jpg", ".jpeg")):
                print(f"\n--- ファイル '{filename}' の処理を開始 ---")
                original_path = os.path.join(self.tobako_dir, filename)
                enhanced_path = os.path.join(self.raimu_dir, filename)

                # enhancer を適用
                enhanced_image = self.enhancer.binarize(original_path)
                if enhanced_image is not None:
                    cv2.imwrite(enhanced_path, enhanced_image)
                    print(f"鮮明化された画像を '{enhanced_path}' に保存しました。")
                else:
                    print(f"警告: '{original_path}' の処理に失敗しました。")
                    continue

                # デコード
                original_decode = self.decoder.decode_from_path(original_path)
                enhanced_decode = self.decoder.decode_from_path(enhanced_path)

                match = (original_decode is not None) and (
                    original_decode == enhanced_decode
                )

                result = {
                    "file": filename,
                    "toba": original_decode,
                    "raimu": enhanced_decode,
                    "match": match,
                }
                evaluation_results.append(result)
                print(f"デコード結果: {result}")

        # 結果をJSON保存
        evaluate_file_path = "evaluate.json"
        with open(evaluate_file_path, "w", encoding="utf-8") as f:
            json.dump(evaluation_results, f, indent=4, ensure_ascii=False)
        print(
            f"\nすべての処理が完了しました。評価結果は '{evaluate_file_path}' に保存されました。"
        )
