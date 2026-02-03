"""
電力料金比較シミュレーションアプリケーション
Streamlitを使用したメインUIモジュール
"""
import streamlit as st
import pandas as pd
from logic import ElectricityCalculator

# ---------------------------------------------------------
# 1. アプリ設定 & デザイン (CSS)
# ---------------------------------------------------------
st.set_page_config(page_title="電力料金比較シミュレーター", layout="wide")
st.markdown('<html lang="ja"></html>', unsafe_allow_html=True)

st.markdown("""
    <style>
    /* 全体のフォント調整 */
    body { font-family: "Helvetica Neue", Arial, "Hiragino Kaku Gothic ProN", "Hiragino Sans", Meiryo, sans-serif; }
    
    /* 金額表示の強調 */
    .total-cost-amount { font-size: 55px !important; font-weight: bold; color: #1E90FF; line-height: 1.2; }
    
    /* 削減額の強調（赤枠付き） */
    .save-label { 
        font-size: 32px !important; font-weight: bold; color: #d32f2f; 
        background-color: #ffebee; padding: 10px 20px; border-radius: 8px; 
        border: 2px solid #d32f2f; display: inline-block; margin-top: 5px;
    }
    
    /* サブ情報の文字スタイル */
    .avg-label { font-size: 18px !important; font-weight: bold; color: #555; }
    .incentive-tag { background-color: #fff176; color: #000; padding: 4px 12px; border-radius: 4px; font-size: 16px; font-weight: bold; }
    
    /* ステータスボックス（青い帯） */
    .status-box { 
        background-color: #e3f2fd; padding: 15px; border-radius: 8px; 
        border-left: 6px solid #2196f3; margin-bottom: 20px; font-size: 16px;
    }
    
    /* 高圧注意書き */
    .high-voltage-note { 
        font-size: 14px; color: #d32f2f; background-color: #fff3e0; 
        padding: 10px; border-radius: 4px; border: 1px solid #ffcc80; margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("⚡ 電力料金比較シミュレーター")

# 計算エンジンの初期化
calculator = ElectricityCalculator()

# ---------------------------------------------------------
# 2. サイドバー：入力エリア
# ---------------------------------------------------------
st.sidebar.header("📋 基本契約情報の入力")

# (1) エリア選択
area = st.sidebar.selectbox("電力使用エリア", ["北海道", "東北", "東京", "中部", "北陸", "関西", "中国", "四国", "九州", "沖縄"])

# (2) 契約区分
category = st.sidebar.selectbox("区分", ["低圧（従量）", "低圧（動力）", "高圧"])

# (3) 契約詳細設定（エリアごとの単位ロジック）
unit_label = "kW"
is_capacity_disabled = False
initial_capacity = 10.0
power_factor_msg = ""

if category == "低圧（従量）":
    # 関西・中国・四国エリアの特殊ルール
    if area in ["関西", "中国", "四国"]:
        options = ["従量電灯A（最低料金制）", "従量電灯B（基本料金制）"]
        contract_detail = st.sidebar.selectbox("契約種別", options)
        if "従量電灯A" in contract_detail:
            unit_label = "1契約（固定）"
            initial_capacity = 1.0
            is_capacity_disabled = True # Aは容量入力不可
        else:
            unit_label = "kVA"
            initial_capacity = 6.0
    # その他エリア
    else:
        options = ["従量電灯B（アンペア制）", "従量電灯C（kVA制）"]
        contract_detail = st.sidebar.selectbox("契約種別", options)
        if "従量電灯B" in contract_detail:
            unit_label = "A"
            initial_capacity = 30.0
        else:
            unit_label = "kVA"
            initial_capacity = 10.0

elif category == "低圧（動力）":
    contract_detail = "低圧電力（動力）"
    pf = st.sidebar.slider("力率 (%)", 0, 100, 85)
    power_factor_msg = f"※力率割引/割増: {(1.85 - pf/100):.2f}倍"

else: # 高圧
    # 高圧のA/B判定ガイド
    st.sidebar.markdown("""
    <div style="background:#eee; padding:5px; border-radius:4px; font-size:0.9em;">
    <b>🏢 高圧判定ガイド</b><br>
    ・500kW未満 → <b>高圧A</b><br>
    ・500kW以上 → <b>高圧B</b>
    </div>
    """, unsafe_allow_html=True)
    contract_detail = st.sidebar.selectbox("高圧種別", ["高圧電力A (50kW以上500kW未満)", "高圧電力B (500kW以上2000kW未満)"])
    pf = st.sidebar.slider("力率 (%)", 0, 100, 85)
    power_factor_msg = f"※力率割引/割増適用"

# 契約容量入力
capacity = st.sidebar.number_input(
    f"契約容量 ({unit_label})", 
    min_value=0.0, 
    value=float(initial_capacity), 
    disabled=is_capacity_disabled
)
if power_factor_msg:
    st.sidebar.caption(power_factor_msg)

# (4) 基準単価（明細）の入力
st.sidebar.divider()
st.sidebar.subheader("📝 現在の料金明細（基準月）")
st.sidebar.caption("直近の検針票の項目と金額を入力してください。")

if 'billing_items' not in st.session_state:
    st.session_state['billing_items'] = [
        {"name": "基本料金", "val": 5000},
        {"name": "電力量料金", "val": 12000},
        {"name": "燃料費調整額", "val": 2000},
        {"name": "再エネ賦課金", "val": 1000}
    ]

if st.sidebar.button("➕ 項目を追加する"):
    st.session_state['billing_items'].append({"name": "その他項目", "val": 0})
    st.rerun()

# 項目入力フォーム
updated_items = []
base_monthly_cost = 0 # 基準月の合計
for i, item in enumerate(st.session_state['billing_items']):
    c1, c2 = st.sidebar.columns([6, 4])
    with c1: n = st.text_input(f"項目名{i+1}", value=item["name"], key=f"n_{i}", label_visibility="collapsed")
    with c2: v = st.number_input(f"金額{i+1}", value=item["val"], step=100, key=f"v_{i}", label_visibility="collapsed")
    updated_items.append({"name": n, "val": v})
    base_monthly_cost += v
st.session_state['billing_items'] = updated_items
st.sidebar.markdown(f"**基準月合計: ¥{base_monthly_cost:,}**")

# (5) 3年分データ入力（ハイブリッド入力）
st.sidebar.divider()
st.sidebar.subheader("🗓️ 月別使用量・金額 (任意)")
st.sidebar.caption("入力がない月は、上記の『基準月金額』で計算します。")

month_records = []
total_usage_kwh = 0
total_actual_cost = 0

for year in [2024, 2025, 2026]:
    with st.sidebar.expander(f"📅 {year}年のデータ", expanded=(year == 2026)):
        for month in range(1, 13):
            # 2列レイアウト
            c_use, c_cost = st.columns(2)
            with c_use: 
                u = st.number_input(f"{month}月 使用量(kWh)", min_value=0, key=f"u_{year}_{month}")
            with c_cost: 
                p = st.number_input(f"{month}月 請求額(円)", min_value=0, key=f"p_{year}_{month}", help="空欄(0)の場合は基準月合計が適用されます")
            
            # データ入力がある場合のみリストに追加
            if u > 0 or p > 0:
                # 金額が0なら基準月合計を採用
                cost_for_month = p if p > 0 else base_monthly_cost
                total_usage_kwh += u
                total_actual_cost += cost_for_month
                month_records.append({
                    "年": year, 
                    "月": month, 
                    "使用量(kWh)": u, 
                    "請求金額": cost_for_month,
                    "入力タイプ": "実数" if p > 0 else "基準値推計"
                })

# 計算対象期間
calc_months = len(month_records)
# 全く入力がない場合は「1ヶ月分（基準月）」として計算
if calc_months == 0:
    calc_months = 1
    total_actual_cost = base_monthly_cost
    # レポート用に1行ダミーデータを作成
    month_records.append({"年": "-", "月": "基準月", "使用量(kWh)": 0, "請求金額": base_monthly_cost, "入力タイプ": "基準値"})

# ---------------------------------------------------------
# 3. 内部設定（プラン & インセンティブ）
# ---------------------------------------------------------
with st.sidebar.expander("🛠️ 内部設定（管理者用）"):
    sales_mode = st.checkbox("インセンティブ情報を表示", value=False)
    
    # カテゴリ別プラン定義
    if category == "高圧":
        plans = [
            {"p": "最適でんき (高圧)", "rate": 0.80, "shot": 18000, "run": 600},
            {"p": "U-POWER (高圧)", "rate": 0.85, "shot": 16000, "run": 500},
            {"p": "ハルエネ (高圧)", "rate": 0.83, "shot": 15000, "run": 400},
        ]
    else:
        plans = [
            {"p": "Looopでんき", "rate": 0.75, "shot": 20000, "run": 800},
            {"p": "U-POWERでんき", "rate": 0.80, "shot": 15000, "run": 500},
            {"p": "Elenovaでんき", "rate": 0.82, "shot": 10000, "run": 300},
            {"p": "オフィスでんき", "rate": 0.83, "shot": 8000, "run": 200},
            {"p": "パルパワー", "rate": 0.84, "shot": 5000, "run": 100},
        ]
    
    # プラン選択
    selected_plans = [p for p in plans if st.checkbox(p["p"], value=True, key=f"sel_{p['p']}")]

# ---------------------------------------------------------
# 4. メイン画面：診断結果
# ---------------------------------------------------------
st.subheader(f"📊 診断結果: {area} / {contract_detail}")

# 入力状況サマリー
avg_unit_price = total_actual_cost / total_usage_kwh if total_usage_kwh > 0 else 0
st.markdown(f"""
<div class='status-box'>
    <strong>💡 現在の契約状況サマリー</strong><br>
    ・対象期間: <b>{calc_months}ヶ月分</b><br>
    ・合計使用量: <b>{total_usage_kwh:,} kWh</b><br>
    ・現状のお支払い総額: <b style="font-size:1.2em;">¥{int(total_actual_cost):,}</b> 
    <span style="color:#666; font-size:0.9em;">(平均単価: ¥{avg_unit_price:.1f}/kWh)</span>
</div>
""", unsafe_allow_html=True)

# プラン別比較カード
if not selected_plans:
    st.warning("比較するプランが選択されていません。サイドバーの設定を確認してください。")

for plan in selected_plans:
    # 削減額計算（logic.pyの関数を使用）
    cost_result = calculator.calculate_plan_costs(total_actual_cost, plan["rate"], calc_months)
    
    proposed_cost = cost_result['proposed_cost']
    reduction_amount = cost_result['reduction_amount']
    reduction_pct = cost_result['reduction_pct']
    avg_reduction = cost_result['avg_reduction']

    with st.container(border=True):
        # ヘッダー（プラン名 ＋ インセンティブ）
        c_head1, c_head2 = st.columns([1, 1])
        with c_head1: 
            st.markdown(f"### {plan['p']}")
        with c_head2:
            if sales_mode:
                st.markdown(f"<div style='text-align:right;'><span class='incentive-tag'>💰 Shot: ¥{plan['shot']:,} / Run: ¥{plan.get('run',0):,}</span></div>", unsafe_allow_html=True)

        # メイン数値（コスト・削減額）
        c_main, c_sub = st.columns([3, 1])
        with c_main:
            st.markdown("<div>切り替え後の予想支払額</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='total-cost-amount'>¥{proposed_cost:,} <span style='font-size:20px; color:#666; font-weight:normal'>(税込)</span></div>", unsafe_allow_html=True)
            
            st.markdown(f"<div class='save-label'>削減額：¥{reduction_amount:,} ！！！</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='avg-label'>（月平均 ¥{avg_reduction:,} お得）</div>", unsafe_allow_html=True)
        
        with c_sub:
            st.metric("削減率", f"{reduction_pct:.1f}%", delta=f"-{reduction_pct:.1f}%", delta_color="inverse")

        # 詳細内訳（アコーディオン）
        with st.expander("📄 詳細な明細比較（内訳）を見る"):
            # 項目別内訳計算（logic.pyの関数を使用）
            breakdown_rows = calculator.calculate_item_breakdown(
                st.session_state['billing_items'], 
                base_monthly_cost, 
                total_actual_cost, 
                plan["rate"]
            )
            st.table(pd.DataFrame(breakdown_rows))

# ---------------------------------------------------------
# 5. Excel出力機能
# ---------------------------------------------------------
st.sidebar.divider()
st.sidebar.markdown("### 📥 提案書作成")

if st.sidebar.button("詳細比較Excelをダウンロード"):
    # Excel生成（logic.pyの関数を使用）
    excel_output = calculator.generate_excel_report(
        selected_plans, 
        month_records, 
        st.session_state['billing_items'], 
        base_monthly_cost, 
        total_actual_cost, 
        area
    )
    
    st.download_button(
        label="Excelファイルを保存",
        data=excel_output.getvalue(),
        file_name=f"電力削減診断_{area}_{pd.Timestamp.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )