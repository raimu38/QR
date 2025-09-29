import os
import json
import cv2
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Any

from pipeline.qr_enhancer import QREnhancer
from pipeline.qr_decode import QRCodeDecoder


class QRPipeline:
    """
    3ステップ実行に分割可能なパイプライン。

    Step1: ベクトル作成（qr_vector/*.json）
    Step2: JSON→画像再生成 ＋ デコード評価（evaluate.json）
    Step3: PDF等の外部評価は main.py 側で既存モジュールを呼ぶ
    """

    def __init__(self, tobako_dir: str, raimu_dir: str,
                 enhancer_params: dict = None,
                 vector_dir: str = "qr_vector",
                 statistics_dir: str = "qr_statistics"):
        self.tobako_dir = tobako_dir
        self.raimu_dir = raimu_dir
        self.vector_dir = vector_dir
        self.statistics_dir = statistics_dir
        self.enhancer = QREnhancer(**(enhancer_params or {}))
        self.decoder = QRCodeDecoder()
        self.module = self.enhancer.module
        self._top_row_avgs_all: list[float] = []

    # ========= Step1 =========
    def step1_make_vectors(self) -> None:
        """
        すべての入力画像を2値化→module×moduleの0/1ベクトルにし、qr_vector に JSON 保存。
        併せてトップ行セル平均を集約し、qr_statistics/sikiiti.png を1枚だけ保存。
        """
        if not os.path.exists(self.tobako_dir):
            print(f"エラー: 入力ディレクトリ '{self.tobako_dir}' が見つかりません。")
            return
        os.makedirs(self.vector_dir, exist_ok=True)
        os.makedirs(self.raimu_dir, exist_ok=True)
        os.makedirs(self.statistics_dir, exist_ok=True)

        def _key(x: str) -> int:
            stem = os.path.splitext(x)[0]
            try:
                return int(stem)
            except ValueError:
                return 10**9

        sorted_files = sorted(os.listdir(self.tobako_dir), key=_key)

        for filename in sorted_files:
            if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
                continue

            print(f"\n[Step1] ベクトル化: '{filename}'")
            in_path = os.path.join(self.tobako_dir, filename)
            binary = self.enhancer.binarize(in_path)
            if binary is None:
                print(f"  警告: 読み込みor処理失敗: {in_path}")
                continue

            h, w = binary.shape
            vector = self._binary_to_module_vector(binary)
            out_json = os.path.join(self.vector_dir, f"{os.path.splitext(filename)[0]}.json")
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "file": filename,
                        "module": self.module,
                        "width": int(w),
                        "height": int(h),
                        "vector": vector,  # 0/1
                    },
                    f, ensure_ascii=False
                )
            print(f"  保存: {out_json}")

            # トップ行平均の集約（NaN除外）
            avgs = self.enhancer.get_top_row_avgs()
            self._top_row_avgs_all.extend([float(a) for a in avgs if a == a])

        # 1枚だけ統合プロットを保存（qr_statistics）
        self._save_combined_top_row_statistics(
            out_path=os.path.join(self.statistics_dir, "sikiiti.png"),
            thresh=self.enhancer.top_row_thresh,
        )

    # ========= Step2 =========
    def step2_build_images_and_evaluate(self) -> None:
        """
        qr_vector/*.json から画像を再生成し qr_raimu/*.png へ保存。
        その後、元画像 vs 再生成画像でデコード比較し evaluate.json に保存。
        """
        if not os.path.exists(self.vector_dir):
            print(f"エラー: ベクトルディレクトリ '{self.vector_dir}' が見つかりません。まず Step1 を実行してください。")
            return
        os.makedirs(self.raimu_dir, exist_ok=True)

        def _key(x: str) -> int:
            stem = os.path.splitext(x)[0]
            try:
                return int(stem)
            except ValueError:
                return 10**9

        vector_files = sorted(
            [f for f in os.listdir(self.vector_dir) if f.lower().endswith(".json")],
            key=_key
        )

        # JSON→画像
        for vec_name in vector_files:
            vec_path = os.path.join(self.vector_dir, vec_name)
            with open(vec_path, "r", encoding="utf-8") as f:
                obj = json.load(f)

            filename = obj.get("file") or f"{os.path.splitext(vec_name)[0]}.png"
            w = int(obj["width"])
            h = int(obj["height"])
            module = int(obj["module"])
            vector = obj["vector"]

            img = self._vector_to_image(vector, width=w, height=h, module=module)
            out_img_path = os.path.join(self.raimu_dir, os.path.splitext(filename)[0] + ".png")
            cv2.imwrite(out_img_path, img)
            print(f"[Step2] 生成: {out_img_path}")

        # 評価
        print("\n[Step2] デコード評価（original vs reconstructed）")
        evaluation_results: List[Dict[str, Any]] = []

        out_images = sorted(
            [f for f in os.listdir(self.raimu_dir) if f.lower().endswith((".png", ".jpg", ".jpeg"))],
            key=_key,
        )
        for filename in out_images:
            orig_path = os.path.join(self.tobako_dir, filename)
            if not os.path.exists(orig_path):
                alt = self._find_alt_original(filename)
                orig_path = alt or orig_path

            recon_path = os.path.join(self.raimu_dir, filename)

            orig = self.decoder.decode_from_path(orig_path) if os.path.exists(orig_path) else None
            recon = self.decoder.decode_from_path(recon_path)

            match = (orig is not None) and (orig == recon)
            result = {
                "file": filename,
                "original": orig,
                "reconstructed": recon,
                "match": match,
            }
            evaluation_results.append(result)
            print(f"  {filename}: match={match} | original={orig} | reconstructed={recon}")

        with open("evaluate.json", "w", encoding="utf-8") as f:
            json.dump(evaluation_results, f, indent=4, ensure_ascii=False)
        print("完了: 評価結果を 'evaluate.json' に保存しました。")

    # ========= 元の一括 run（必要なら） =========
    def run(self) -> None:
        """従来互換: Step1→Step2 を続けて実行"""
        self.step1_make_vectors()
        self.step2_build_images_and_evaluate()

    # ========= Helpers =========

    def _binary_to_module_vector(self, binary: np.ndarray) -> List[List[int]]:
        """
        2値画像（0/255）を module x module の 0/1 ベクトルに落とす。
        1=黒(0側)、0=白(255側)
        """
        h, w = binary.shape
        module = self.module
        cell_w = w // module
        cell_h = h // module

        vec: List[List[int]] = []
        for gy in range(module):
            row: List[int] = []
            y0 = gy * cell_h
            y1 = (gy + 1) * cell_h if gy < module - 1 else h
            for gx in range(module):
                x0 = gx * cell_w
                x1 = (gx + 1) * cell_w if gx < module - 1 else w
                cell = binary[y0:y1, x0:x1]
                v = 1 if np.mean(cell) < 128 else 0  # 保険として平均で判定
                row.append(int(v))
            vec.append(row)
        return vec

    def _vector_to_image(self, vector: List[List[int]], width: int, height: int, module: int) -> np.ndarray:
        """
        module x module の 0/1 ベクトルから元サイズの2値画像(0/255)を再生成。
        1=黒 → 0, 0=白 → 255
        """
        img = np.ones((height, width), dtype=np.uint8) * 255
        cell_w = width // module
        cell_h = height // module

        for gy in range(module):
            y0 = gy * cell_h
            y1 = (gy + 1) * cell_h if gy < module - 1 else height
            for gx in range(module):
                x0 = gx * cell_w
                x1 = (gx + 1) * cell_w if gx < module - 1 else width
                val = 0 if vector[gy][gx] == 1 else 255
                img[y0:y1, x0:x1] = val
        return img

    def _find_alt_original(self, filename: str) -> str | None:
        """
        同名拡張子違い（.jpg / .jpeg / .png）で元画像を探索。
        """
        stem = os.path.splitext(filename)[0]
        for ext in (".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"):
            p = os.path.join(self.tobako_dir, stem + ext)
            if os.path.exists(p):
                return p
        return None

    def _save_combined_top_row_statistics(self, out_path: str, thresh: float):
        data = np.array(self._top_row_avgs_all, dtype=float)
        if data.size == 0:
            print("[TopRow-Combined] データがないため統計グラフを作成しません。")
            return

        fig = plt.figure(figsize=(10, 6), layout="constrained")
        ax1 = fig.add_subplot(2, 1, 1)
        ax2 = fig.add_subplot(2, 1, 2)

        ax1.plot(np.arange(data.size), data, linewidth=1, color="#377eb8", label="mean intensity")
        ax1.axhline(thresh, color="r", linestyle="--", label=f"threshold={thresh}")
        ax1.set_title("Top-row cell means (all images, concatenated)")
        ax1.set_xlabel("appearance index")
        ax1.set_ylabel("mean intensity (0-255)")
        ax1.set_ylim(0, 255)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc="best")

        ax2.hist(data, bins=40, color="#4C72B0", alpha=0.9, edgecolor="black")
        ax2.axvline(thresh, color="r", linestyle="--", label=f"threshold={thresh}")
        ax2.set_title("Distribution of top-row cell means (all images)")
        ax2.set_xlabel("mean intensity")
        ax2.set_ylabel("count")
        ax2.set_xlim(0, 255)
        ax2.grid(True, alpha=0.3)
        ax2.legend(loc="best")

        fig.suptitle("Top-row statistics (aggregated)", fontsize=14)
        fig.savefig(out_path, dpi=150)
        plt.close(fig)
        print(f"[TopRow-Combined] 統計グラフを '{out_path}' に保存しました。")
