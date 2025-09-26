import cv2
from pyzbar.pyzbar import decode


class QRCodeDecoder:
    """
    QRコード画像のデコードを扱うクラス。
    """

    def decode_from_path(self, qr_path: str) -> str or None:
        """
        指定された画像パスからQRコードを読み取り、デコードした文字列を返す。

        Args:
            qr_path (str): QRコード画像のパス。

        Returns:
            str or None: デコードされた文字列。読み取りに失敗した場合はNone。
        """
        # 画像を読み込む
        img = cv2.imread(qr_path)
        if img is None:
            print(f"エラー: 画像ファイル '{qr_path}' を読み込めません。")
            return None

        # QRコードをデコード
        decoded_objects = decode(img)

        # 検出されたオブジェクトがあれば、最初のものを返す
        if decoded_objects:
            # デコードされたデータはバイト形式なので、文字列に変換
            return decoded_objects[0].data.decode("utf-8")

        # 検出されたオブジェクトがなければNoneを返す
        return None

    def decode_from_path_from_image(self, img_data) -> str or None:
        """
        画像データ（numpy.ndarray）から直接QRコードをデコードする。
        """
        if img_data is None or img_data.size == 0:
            return None

        decoded_objects = decode(img_data)

        if decoded_objects:
            return decoded_objects[0].data.decode("utf-8")

        return None
