import cv2
import numpy as np


class QREnhancer:
    """
    QRコード画像を加工するクラス。
    - 一番上の行の特別処理（グレースケール段階）
    - 通常のgrid二値化（上一行を除外）
    - finder pattern の塗りつぶし
    - 最後にトップ行の判定結果を強制反映
    """

    def __init__(
        self,
        module: int = 33,
        white_thresh: int = 220,
        black_thresh: int = 50,
        avg_thresh: int = 128,       # 通常の平均値しきい値
        top_row_thresh: int = 160,   # 上一行専用の黒寄りしきい値
        finder_size: int = 7,        # finder pattern の外枠サイズ（セル単位）
    ):
        self.module = module
        self.white_thresh = white_thresh
        self.black_thresh = black_thresh
        self.avg_thresh = avg_thresh
        self.top_row_thresh = top_row_thresh
        self.finder_size = finder_size
        self._top_row_values: list[int] | None = None   # 0/255
        self._top_row_avgs: list[float] | None = None   # 平均値(グレースケール)

    def binarize(self, path: str) -> np.ndarray | None:
        """
        QRコード画像を読み込み、鮮明化した2値画像を返す。
        """
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None

        # Step 1: 上一行を先に補正（グレースケール）
        img = self._fix_top_row(img)

        h, w = img.shape
        grid_size_x = max(1, w // self.module)
        grid_size_y = max(1, h // self.module)
        fs = self.finder_size

        binary = np.ones_like(img, dtype=np.uint8) * 255  # 白で初期化

        # Step 2: 上一行は fix_top_row の結果をそのままコピー
        y0, y1 = 0, grid_size_y
        binary[y0:y1, :] = img[y0:y1, :]

        # Step 3: 通常のgrid二値化（上一行はスキップ）
        for gy in range(1, self.module):
            for gx in range(self.module):
                x0 = gx * grid_size_x
                y0 = gy * grid_size_y
                x1 = (gx + 1) * grid_size_x if gx < self.module - 1 else w
                y1 = (gy + 1) * grid_size_y if gy < self.module - 1 else h

                if x0 >= w or y0 >= h:
                    continue

                cell = img[y0:y1, x0:x1]

                has_white = np.any(cell >= self.white_thresh)
                has_black = np.any(cell <= self.black_thresh)

                if has_white and not has_black:
                    value = 255
                elif has_black and not has_white:
                    value = 0
                else:
                    avg = np.mean(cell)
                    value = 255 if avg >= self.avg_thresh else 0

                binary[y0:y1, x0:x1] = value

        # Step 4: finder を強制塗り
        binary = self._fill_finder_patterns(binary)

        # Step 5: トップ行の判定結果を最終的に強制反映（finder列は除外）
        if self._top_row_values is not None:
            y0, y1 = 0, grid_size_y
            for gx, val in enumerate(self._top_row_values):
                if gx < fs or gx >= self.module - fs:
                    continue
                x0 = gx * grid_size_x
                x1 = (gx + 1) * grid_size_x if gx < self.module - 1 else w
                binary[y0:y1, x0:x1] = val

        return binary

    def _fill_finder_patterns(self, binary: np.ndarray) -> np.ndarray:
        """
        左上・右上・左下の finder pattern を正しい構造で塗りつぶす。
        外黒 finder_size×finder_size → 中白 (finder_size-1)枠内 → 中央 (finder_size-2)
        """
        h, w = binary.shape
        grid_size_x = max(1, w // self.module)
        grid_size_y = max(1, h // self.module)
        fs = self.finder_size

        def draw_finder(x0, y0):
            # 外側 黒
            binary[y0 : y0 + fs * grid_size_y, x0 : x0 + fs * grid_size_x] = 0
            # 内側 白
            binary[
                y0 + grid_size_y : y0 + (fs - 1) * grid_size_y,
                x0 + grid_size_x : x0 + (fs - 1) * grid_size_x,
            ] = 255
            # 中央 黒
            binary[
                y0 + 2 * grid_size_y : y0 + (fs - 2) * grid_size_y,
                x0 + 2 * grid_size_x : x0 + (fs - 2) * grid_size_x,
            ] = 0

        draw_finder(0, 0)
        draw_finder(w - fs * grid_size_x, 0)
        draw_finder(0, h - fs * grid_size_y)

        return binary

    def _fix_top_row(self, img: np.ndarray) -> np.ndarray:
        """
        グレースケール段階で QRコードの一番上の行を補正。
        併せてセルごとの平均値/最終値を保存。
        """
        h, w = img.shape
        grid_size_x = max(1, w // self.module)
        grid_size_y = max(1, h // self.module)

        y0, y1 = 0, grid_size_y
        top_vals: list[int] = []
        top_avgs: list[float] = []

        for gx in range(self.module):
            x0 = gx * grid_size_x
            x1 = (gx + 1) * grid_size_x if gx < self.module - 1 else w

            cell = img[y0:y1, x0:x1]
            if cell.size == 0:
                top_vals.append(255)
                top_avgs.append(np.nan)
                continue

            avg = float(np.mean(cell))
            value = 0 if avg < self.top_row_thresh else 255
            label = "BLACK" if value == 0 else "WHITE"

            print(f"[TopRow] gx={gx:02d}, avg={avg:.2f}, thresh={self.top_row_thresh}, -> {label}")

            img[y0:y1, x0:x1] = value
            top_vals.append(value)
            top_avgs.append(avg)

        self._top_row_values = top_vals
        self._top_row_avgs = top_avgs
        return img

    # トップ行の平均値配列を取得（コピーを返す）
    def get_top_row_avgs(self) -> list[float]:
        return list(self._top_row_avgs or [])
