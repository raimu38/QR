import sys
import os

from pipeline.pipeline import QRPipeline
import evaluate.evaluate_pdf as evaluate_pdf
import evaluate.overlay_pdf as overlay_pdf
import evaluate.analysis_pdf as analysis_pdf

# main.py（抜粋）
from pipeline.pipeline import QRPipeline
# ...

def build_pipeline() -> QRPipeline:
    tobako_dir = "qr_tobakosan"
    raimu_dir = "qr_raimu"
    vector_dir = "qr_vector"
    statistics_dir = "qr_statistics" 

    params = {
        "module": 33,
        "white_thresh": 220,
        "black_thresh": 50,
        "avg_thresh": 128,
        "top_row_thresh": 160,
        "finder_size": 7,
    }

    return QRPipeline(
        tobako_dir=tobako_dir,
        raimu_dir=raimu_dir,
        vector_dir=vector_dir,
        statistics_dir=statistics_dir,  
        enhancer_params=params,
    )


def run_step1_vectors():
    """
    Step1: ベクトル作成（qr_vector/*.json）＋ sikiiti.png の作成
    """
    pipeline = build_pipeline()
    pipeline.step1_make_vectors()


def run_step2_reconstruct_and_evaluate():
    """
    Step2: JSONから画像再生成（qr_raimu/*.png）＋ デコード評価（evaluate.json）
    """
    pipeline = build_pipeline()
    pipeline.step2_build_images_and_evaluate()


def run_step3_reports():
    """
    Step3: 評価レポート生成（PDF出力）: 既存の evaluate/* モジュールを実行
    """
    try:
        print("\n--- 評価レポートの生成を開始します ---")
        evaluate_pdf.main()
        overlay_pdf.main()
        analysis_pdf.main()
        print("--- 評価レポートの生成が完了しました ---")
    except FileNotFoundError:
        print("\nエラー: 評価に必要なファイルが見つかりません。")
        print("Step1 と Step2 を実行してデータを生成してください。")


if __name__ == "__main__":
    print("\n--- QRコード評価システム ---")
    print("実行したい処理を選択してください:")
    print("1: Step1 ベクトル作成（qr_vector/*.json を生成）")
    print("2: Step2 画像再生成＋評価（raimu画像と evaluate.json を生成）")
    print("3: Step3 評価レポートの生成（PDF出力）")
    print("それ以外: 終了")

    user_input = input("選択肢の番号を入力してください: ").strip()

    if user_input == "1":
        run_step1_vectors()
    elif user_input == "2":
        run_step2_reconstruct_and_evaluate()
    elif user_input == "3":
        run_step3_reports()
    else:
        print("システムを終了します。")
        sys.exit()
