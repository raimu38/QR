import cv2
import numpy as np


class QREnhancer:
    """
    QRコード画像を加工するクラス。
    現状は「モジュール単位の2値化」と「finder pattern の塗りつぶし」に特化。
    """

    def __init__(
        self, module: int = 33, white_thresh: int = 220, black_thresh: int = 50
    ):
        self.module = module
        self.white_thresh = white_thresh
        self.black_thresh = black_thresh

    def binarize(self, path: str) -> np.ndarray | None:
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None

        h, w = img.shape
        grid_size_x = w // self.module
        grid_size_y = h // self.module

        binary = np.ones_like(img, dtype=np.uint8) * 255  # 白で初期化

        for gy in range(self.module):
            for gx in range(self.module):
                x_start = gx * grid_size_x
                y_start = gy * grid_size_y
                x_end = (gx + 1) * grid_size_x if gx < self.module - 1 else w
                y_end = (gy + 1) * grid_size_y if gy < self.module - 1 else h

                cell = img[y_start:y_end, x_start:x_end]

                has_white = np.any(cell >= self.white_thresh)
                has_black = np.any(cell <= self.black_thresh)

                if has_white and not has_black:
                    value = 255
                elif has_black and not has_white:
                    value = 0
                elif has_white and has_black:
                    avg = np.mean(cell)
                    value = 255 if avg >= 128 else 0
                else:
                    avg = np.mean(cell)
                    value = 255 if avg >= 128 else 0

                binary[y_start:y_end, x_start:x_end] = value

        # finder pattern を強制的に黒に塗りつぶす
        binary = self._fill_finder_patterns(binary)

        return binary

    def _fill_finder_patterns(self, binary: np.ndarray) -> np.ndarray:
        """
        左上・右上・左下の finder pattern を正しい構造で塗りつぶす。
        外黒7×7 → 中白5×5 → 中央黒3×3。
        """
        h, w = binary.shape
        grid_size_x = w // self.module
        grid_size_y = h // self.module

        def draw_finder(x0, y0):
            # 7×7 黒枠
            binary[y0 : y0 + 7 * grid_size_y, x0 : x0 + 7 * grid_size_x] = 0
            # 内側 5×5 白
            binary[
                y0 + grid_size_y : y0 + 6 * grid_size_y,
                x0 + grid_size_x : x0 + 6 * grid_size_x,
            ] = 255
            # 中央 3×3 黒
            binary[
                y0 + 2 * grid_size_y : y0 + 5 * grid_size_y,
                x0 + 2 * grid_size_x : x0 + 5 * grid_size_x,
            ] = 0

        # 左上
        draw_finder(0, 0)
        # 右上
        draw_finder(w - 7 * grid_size_x, 0)
        # 左下
        draw_finder(0, h - 7 * grid_size_y)

        return binary
