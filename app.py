import streamlit as st
import random
import pandas as pd
import plotly.express as px
from datetime import datetime


# --- 核心模拟逻辑类 ---
class BaccaratWebSimulator:
    def __init__(self, target_pattern, bet_sequence, unit_bet, initial_capital):
        points = [1, 2, 3, 4, 5, 6, 7, 8, 9, 0, 0, 0, 0]
        self.cards_vals = points * 4 * 8
        self.target_pattern = target_pattern
        self.bet_sequence = [b * unit_bet for b in bet_sequence]
        self.origin_base_cap = initial_capital
        self.current_capital = initial_capital
        self.total_recharge = initial_capital
        self.total_withdrawn = 0.0

        self.peak_profit = 0.0
        self.min_balance = 0.0
        self.total_bets = 0
        self.total_wins = 0
        self.bankrupt_count = 0
        self.balance_history = []  # 记录资金曲线
        self.bet_idx = 0

    def play_shoe(self):
        shoe = list(self.cards_vals)
        random.shuffle(shoe)
        shoe = shoe[:-random.randint(20, 40)]
        res = []
        while len(shoe) >= 6:
            p_h, b_h = [shoe.pop(), shoe.pop()], [shoe.pop(), shoe.pop()]
            ps, bs = sum(p_h) % 10, sum(b_h) % 10
            if ps < 8 and bs < 8:
                pt = -1
                if ps <= 5: pt = shoe.pop(); ps = (ps + pt) % 10
                if pt == -1:
                    if bs <= 5: bs = (bs + shoe.pop()) % 10
                else:
                    if bs <= 2 or (bs == 3 and pt != 8) or (bs == 4 and 2 <= pt <= 7) or (bs == 5 and 4 <= pt <= 7) or (
                            bs == 6 and 6 <= pt <= 7):
                        bs = (bs + shoe.pop()) % 10
            r = 'P' if ps > bs else 'B' if bs > ps else 'T'
            if r != 'T': res.append(r)
        return res

    def run_simulation(self, total_shoes):
        p_len = len(self.target_pattern)
        for s_idx in range(1, total_shoes + 1):
            res = self.play_shoe()
            colors, lengths = self.get_blocks(res)

            win_limit = self.current_capital * 0.10
            loss_limit = self.current_capital * -0.20
            shoe_profit = 0.0
            shoe_finished = False

            for i in range(len(lengths) - p_len + 1):
                if shoe_finished: break
                match = True
                for k in range(p_len - 1):
                    if lengths[i + k] < self.target_pattern[k]: match = False; break
                if match and lengths[i + p_len - 1] < self.target_pattern[-1]: match = False

                if match:
                    self.total_bets += 1
                    target_color = colors[i + p_len - 1]
                    amt = self.bet_sequence[self.bet_idx]

                    if lengths[i + p_len - 1] == self.target_pattern[-1]:  # 赢
                        p = (amt if target_color == 'B' else amt * 0.95)
                        self.total_wins += 1
                        self.current_capital += p;
                        shoe_profit += p
                        self.bet_idx = (self.bet_idx + 1) % len(self.bet_sequence)
                    else:  # 输
                        self.current_capital -= amt;
                        shoe_profit -= amt
                        self.bet_idx = 0

                    # 全局统计
                    current_net = (self.current_capital + self.total_withdrawn) - self.total_recharge
                    self.peak_profit = max(self.peak_profit, current_net)
                    self.min_balance = min(self.min_balance, current_net)
                    self.balance_history.append(current_net)

                    if self.current_capital <= 0:
                        self.bankrupt_count += 1
                        self.total_recharge += self.origin_base_cap
                        self.current_capital = self.origin_base_cap
                        self.bet_idx = 0
                        shoe_finished = True;
                        break

                    if self.current_capital >= self.origin_base_cap * 3:
                        self.current_capital -= self.origin_base_cap
                        self.total_withdrawn += self.origin_base_cap

                    if shoe_profit >= win_limit or shoe_profit <= loss_limit:
                        shoe_finished = True
            self.current_capital += shoe_profit

    def get_blocks(self, res):
        colors, lengths = [], []
        if not res: return colors, lengths
        curr_c, curr_l = res[0], 0
        for r in res:
            if r == curr_c:
                curr_l += 1
            else:
                colors.append(curr_c);
                lengths.append(curr_l)
                curr_c, curr_l = r, 1
        colors.append(curr_c);
        lengths.append(curr_l)
        return colors, lengths


# --- Streamlit 界面 ---
st.set_page_config(page_title="百家乐策略回测系统", layout="wide")
st.title("🎰 百家乐策略专家回测系统")

# 侧边栏：输入参数
with st.sidebar:
    st.header("⚙️ 参数设置")
    shoes = st.number_input("模拟靴数", value=1000, step=100)
    capital = st.number_input("起始本金", value=3000)
    unit = st.number_input("基码大小", value=50)
    pattern_str = st.text_input("匹配模式 (空格分隔)", value="2 4 4 1")
    bets_str = st.text_input("胜进注码序列 (空格分隔)", value="1 3 2 4")

    run_btn = st.button("🚀 开始测算", use_container_width=True)

# 历史记录逻辑
if 'history' not in st.session_state:
    st.session_state.history = []

if run_btn:
    pattern = [int(x) for x in pattern_str.split()]
    bets = [float(x) for x in bets_str.split()]

    sim = BaccaratWebSimulator(pattern, bets, unit, capital)

    with st.spinner('大数据模拟中...'):
        sim.run_simulation(shoes)

    # --- 显示结果卡片 ---
    col1, col2, col3, col4 = st.columns(4)
    final_net = (sim.current_capital + sim.total_withdrawn) - sim.total_recharge
    col1.metric("最终总净利", f"{final_net:.2f}", delta=f"{final_net / capital * 100:.1f}%")
    col2.metric("最高盈利峰值", f"+{sim.peak_profit:.2f}")
    col3.metric("破产次数", f"{sim.bankrupt_count}")
    col4.metric("最终胜率", f"{(sim.total_wins / sim.total_bets * 100 if sim.total_bets > 0 else 0):.2f}%")

    # --- 资金曲线图 ---
    st.subheader("📈 资金净值波动曲线")
    if sim.balance_history:
        df = pd.DataFrame(sim.balance_history, columns=["Net Profit"])
        fig = px.line(df, y="Net Profit", labels={'index': '下注次数', 'Net Profit': '净利润'})
        st.plotly_chart(fig, use_container_width=True)

    # 保存至历s史记录
    st.session_state.history.append({
        "时间": datetime.now().strftime("%H:%M:%S"),
        "模式": pattern_str,
        "最终净利": final_net,
        "破产次": sim.bankrupt_count,
        "总下注": sim.total_bets
    })

# 显示历史记录表格
if st.session_state.history:
    st.subheader("📜 本次运行历史记录")
    st.table(pd.DataFrame(st.session_state.history).tail(5))
