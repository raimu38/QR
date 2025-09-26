import sys
from pipeline.pipeline import QRPipeline
import evaluate.evaluate_pdf as evaluate_pdf
import evaluate.overlay_pdf as overlay_pdf
import evaluate.analysis_pdf as analysis_pdf


def run_pipeline():
    """
    QRコードの鮮明化とデコードのパイプラインを実行する関数。
    """
    tobako_dir = "qr_tobakosan"
    raimu_dir = "qr_raimu"

    params = {
        "module": 33,
        "white_thresh": 220,
        "black_thresh": 50,
    }

    pipeline_runner = QRPipeline(tobako_dir, raimu_dir, enhancer_params=params)
    pipeline_runner.run()


def run_evaluation():
    """
    評価レポート生成プロセスを実行する関数。
    """
    try:
        print("\n--- 評価レポートの生成を開始します ---")
        evaluate_pdf.main()
        overlay_pdf.main()
        analysis_pdf.main()
        print("--- 評価レポートの生成が完了しました ---")
    except FileNotFoundError:
        print("\nエラー: 評価に必要なファイルが見つかりません。")
        print("パイプラインを実行して、まずデータを生成してください。")


if __name__ == "__main__":
    print("\n--- QRコード評価システム ---")
    print("実行したい処理を選択してください:")
    print("1: QRコード鮮明化パイプラインの実行（データ生成）")
    print("2: 評価レポートの生成（PDF出力）")
    print("それ以外: 終了")

    user_input = input("選択肢の番号を入力してください: ")

    if user_input == "1":
        run_pipeline()
    elif user_input == "2":
        run_evaluation()
    else:
        print("システムを終了します。")
        sys.exit()
