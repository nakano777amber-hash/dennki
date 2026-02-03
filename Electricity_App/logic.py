"""
電気料金計算ロジックモジュール
電気料金の計算とプラン比較機能を提供
"""
import pandas as pd
import io
from typing import Dict, List, Optional
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment


class ElectricityCalculator:
    """
    電気料金計算クラス
    
    Attributes:
        master_df (pd.DataFrame): 料金プランマスターデータ
    """
    
    def __init__(self, master_df: pd.DataFrame = None):
        """
        初期化
        
        Args:
            master_df (pd.DataFrame): 料金プランマスターデータ (オプション)
        """
        self.master_df = master_df
    
    def calculate_cost(
        self,
        company_name: str,
        contract_type: str,
        capacity: float,
        monthly_usage: List[float],
        power_factor: Optional[float] = None
    ) -> Dict:
        """
        電気料金を計算
        
        Args:
            company_name (str): 電力会社名
            contract_type (str): 契約種別 (Low Voltage / High Voltage)
            capacity (float): 契約容量 (kVA/kW)
            monthly_usage (List[float]): 月別使用量 (12ヶ月分)
            power_factor (Optional[float]): 力率 (高圧契約の場合のみ必要)
            
        Returns:
            Dict: 計算結果
                - monthly_costs (List[float]): 月別料金
                - annual_cost (float): 年間料金
                - monthly_base_charges (List[float]): 月別基本料金
                - monthly_energy_charges (List[float]): 月別電力量料金
                - incentive_shot (float): 初回インセンティブ
                - incentive_running (float): 継続インセンティブ(年間)
        """
        # 該当する料金プランを取得
        plan = self.master_df[
            (self.master_df['company_name'] == company_name) &
            (self.master_df['contract_type'] == contract_type)
        ]
        
        if plan.empty:
            raise ValueError(f"該当するプランが見つかりません: {company_name} - {contract_type}")
        
        plan = plan.iloc[0]
        
        # 基本料金の計算
        base_unit_price = plan['base_unit_price']
        energy_unit_price = plan['energy_unit_price']
        incentive_shot = plan['incentive_shot']
        incentive_running = plan['incentive_running']
        
        monthly_base_charges = []
        monthly_energy_charges = []
        monthly_costs = []
        
        for usage in monthly_usage:
            # 基本料金の計算
            if contract_type == "High Voltage":
                # 高圧契約の場合: 力率調整を適用
                if power_factor is None:
                    raise ValueError("高圧契約の場合、力率の入力が必要です")
                
                # 力率調整式: 基本料金単価 × 容量 × (185 - 力率) / 100
                base_charge = base_unit_price * capacity * (185 - power_factor) / 100
            else:
                # 低圧契約の場合: 基本料金単価 × 容量
                base_charge = base_unit_price * capacity
            
            # 電力量料金の計算
            energy_charge = energy_unit_price * usage
            
            # 月額料金
            monthly_cost = base_charge + energy_charge
            
            monthly_base_charges.append(base_charge)
            monthly_energy_charges.append(energy_charge)
            monthly_costs.append(monthly_cost)
        
        # 年間料金の計算
        annual_cost = sum(monthly_costs)
        
        # 継続インセンティブは年間で計算
        annual_running_incentive = incentive_running * 12
        
        return {
            'monthly_costs': monthly_costs,
            'annual_cost': annual_cost,
            'monthly_base_charges': monthly_base_charges,
            'monthly_energy_charges': monthly_energy_charges,
            'incentive_shot': incentive_shot,
            'incentive_running': annual_running_incentive,
            'net_annual_cost': annual_cost - incentive_shot - annual_running_incentive
        }
    
    def get_comparison(
        self,
        contract_type: str,
        capacity: float,
        monthly_usage: List[float],
        power_factor: Optional[float] = None
    ) -> List[Dict]:
        """
        選択された契約種別で利用可能な全プランの比較を取得
        
        Args:
            contract_type (str): 契約種別 (Low Voltage / High Voltage)
            capacity (float): 契約容量 (kVA/kW)
            monthly_usage (List[float]): 月別使用量 (12ヶ月分)
            power_factor (Optional[float]): 力率 (高圧契約の場合のみ必要)
            
        Returns:
            List[Dict]: 各プランの計算結果リスト (削減額順にソート)
        """
        # 該当する契約種別のプランを取得
        available_plans = self.master_df[
            self.master_df['contract_type'] == contract_type
        ]
        
        comparison_results = []
        
        for _, plan in available_plans.iterrows():
            try:
                result = self.calculate_cost(
                    company_name=plan['company_name'],
                    contract_type=contract_type,
                    capacity=capacity,
                    monthly_usage=monthly_usage,
                    power_factor=power_factor
                )
                
                comparison_results.append({
                    'company_name': plan['company_name'],
                    'annual_cost': result['annual_cost'],
                    'net_annual_cost': result['net_annual_cost'],
                    'incentive_shot': result['incentive_shot'],
                    'incentive_running': result['incentive_running'],
                    'monthly_costs': result['monthly_costs'],
                    'monthly_base_charges': result['monthly_base_charges'],
                    'monthly_energy_charges': result['monthly_energy_charges']
                })
            except Exception as e:
                print(f"計算エラー ({plan['company_name']}): {e}")
                continue
        
        # 正味年間コスト(net_annual_cost)の昇順でソート
        comparison_results.sort(key=lambda x: x['net_annual_cost'])
        
        return comparison_results
    
    @staticmethod
    def calculate_plan_costs(total_actual_cost: float, plan_rate: float, calc_months: int) -> Dict:
        """
        プラン別のコスト計算（簡易版）
        
        Args:
            total_actual_cost (float): 現在の総コスト
            plan_rate (float): プランの削減率 (0.0-1.0)
            calc_months (int): 計算対象月数
            
        Returns:
            Dict: 計算結果
                - proposed_cost (int): 提案後のコスト
                - reduction_amount (int): 削減額
                - reduction_pct (float): 削減率(%)
                - avg_reduction (int): 月平均削減額
        """
        proposed_cost = int(total_actual_cost * plan_rate)
        reduction_amount = int(total_actual_cost - proposed_cost)
        reduction_pct = (reduction_amount / total_actual_cost) * 100 if total_actual_cost > 0 else 0
        avg_reduction = int(reduction_amount / calc_months) if calc_months > 0 else 0
        
        return {
            'proposed_cost': proposed_cost,
            'reduction_amount': reduction_amount,
            'reduction_pct': reduction_pct,
            'avg_reduction': avg_reduction
        }
    
    @staticmethod
    def calculate_item_breakdown(billing_items: List[Dict], base_monthly_cost: float, 
                                 total_actual_cost: float, plan_rate: float) -> List[Dict]:
        """
        項目別内訳の計算
        
        Args:
            billing_items (List[Dict]): 請求項目リスト
            base_monthly_cost (float): 基準月の合計コスト
            total_actual_cost (float): 全期間の総コスト
            plan_rate (float): プランの削減率
            
        Returns:
            List[Dict]: 項目別内訳データ
        """
        rows = []
        for item in billing_items:
            # 構成比率計算 (項目金額 / 基準月合計) * 全期間合計
            item_total_current = int((item["val"] / base_monthly_cost) * total_actual_cost) if base_monthly_cost > 0 else 0
            item_total_new = int(item_total_current * plan_rate)
            rows.append({
                "項目": item["name"],
                "現状": f"¥{item_total_current:,}",
                "提案後": f"¥{item_total_new:,}",
                "差額": f"¥{item_total_current - item_total_new:,}"
            })
        return rows
    
    @staticmethod
    def generate_excel_report(selected_plans: List[Dict], month_records: List[Dict], 
                             billing_items: List[Dict], base_monthly_cost: float, 
                             total_actual_cost: float, area: str) -> io.BytesIO:
        """
        詳細比較Excelレポートを生成
        
        Args:
            selected_plans (List[Dict]): 選択されたプランリスト
            month_records (List[Dict]): 月別レコード
            billing_items (List[Dict]): 請求項目リスト
            base_monthly_cost (float): 基準月合計
            total_actual_cost (float): 総コスト
            area (str): エリア名
            
        Returns:
            io.BytesIO: Excelファイルのバイナリデータ
        """
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for plan in selected_plans:
                # Sheet1: 月別推移データ
                df_month = pd.DataFrame(month_records)
                df_month["提案金額"] = (df_month["請求金額"] * plan["rate"]).astype(int)
                df_month["削減額"] = df_month["請求金額"] - df_month["提案金額"]
                
                # 合計行の作成
                sum_row = pd.DataFrame([{
                    "年": "合計", "月": "", 
                    "使用量(kWh)": df_month["使用量(kWh)"].sum(),
                    "請求金額": df_month["請求金額"].sum(),
                    "提案金額": df_month["提案金額"].sum(),
                    "削減額": df_month["削減額"].sum(),
                    "入力タイプ": "-"
                }])
                pd.concat([df_month, sum_row]).to_excel(writer, index=False, sheet_name=f"{plan['p'][:15]}_月別")

                # Sheet2: 項目別内訳（概算）
                items_data = []
                for item in billing_items:
                    current_val = int((item["val"] / base_monthly_cost) * total_actual_cost) if base_monthly_cost > 0 else 0
                    new_val = int(current_val * plan["rate"])
                    items_data.append({
                        "明細項目": item["name"],
                        "現状(全期間)": current_val,
                        "提案後(全期間)": new_val,
                        "削減額": current_val - new_val
                    })
                pd.DataFrame(items_data).to_excel(writer, index=False, sheet_name=f"{plan['p'][:15]}_内訳")
        
        output.seek(0)
        return output
