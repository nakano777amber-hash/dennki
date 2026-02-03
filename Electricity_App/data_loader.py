"""
データローダーモジュール
CSVファイルからマスターデータを読み込む機能を提供
"""
import pandas as pd
from pathlib import Path


def load_master_prices(csv_path: str = "data/master_prices.csv") -> pd.DataFrame:
    """
    料金プランマスターCSVを読み込む
    
    Args:
        csv_path (str): CSVファイルのパス
        
    Returns:
        pd.DataFrame: 料金プランのマスターデータ
        
    Raises:
        FileNotFoundError: CSVファイルが見つからない場合
    """
    try:
        # ファイルパスの存在確認
        file_path = Path(csv_path)
        if not file_path.exists():
            raise FileNotFoundError(f"データファイルが見つかりません: {csv_path}")
        
        # CSVを読み込み
        df = pd.read_csv(csv_path)
        
        # 必須カラムの確認
        required_columns = [
            'company_name', 
            'contract_type', 
            'base_unit_price', 
            'energy_unit_price',
            'incentive_shot',
            'incentive_running'
        ]
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"必須カラムが不足しています: {missing_columns}")
        
        return df
        
    except FileNotFoundError as e:
        print(f"エラー: {e}")
        raise
    except Exception as e:
        print(f"データ読み込み中にエラーが発生しました: {e}")
        raise
