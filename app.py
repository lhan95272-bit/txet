import streamlit as st
import random
import pandas as pd
import plotly.express as px
from datetime import datetime

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
        
        # --- 新增统计项 ---
        self.peak_profit = 0.0
        self.max_drawdown = 0.0  # 最大回撤
        self.max_win_streak = 0  # 最大连胜
        self.max_loss_streak = 0 # 最大连输
        self.curr_win_streak = 0
        self.curr_loss_streak = 0
        # ----------------
        
        self.total_bets = 0
        self.total_wins = 0
        self.bankrupt_count = 0
        self.balance_history = [0.0]
        self.bet_idx = 0

    def play_shoe(self):
        shoe = list(self.cards_vals)
        random.shuffle(shoe)
        shoe = shoe[:-random.randint(20, 40)]
        res = []
        while len(shoe) >= 6:
            p_h, b_h = [shoe.pop(), shoe.pop()], [shoe.pop(), shoe.pop()]
            ps, bs = sum(p_h)%10, sum(b_h)%10
            if ps < 8 and bs < 8:
                pt = -1
                if ps <= 5: pt = shoe.pop(); ps = (ps + pt) % 10
                if pt == -1:
                    if bs <= 5: bs = (bs + shoe.pop()) % 10
                else:
                    if bs <= 2 or (bs==3 and pt!=8) or (bs==4 and 2<=pt<=7) or (bs==5 and 4<=pt<=7) or (bs==6 and 6<=pt<=7):
                        bs = (bs + shoe.pop()) % 10
            r = 'P' if ps > bs else 'B' if bs > ps else 'T'
            if r != 'T': res.append(r)
        return res

    def run_simulation(self, total_shoes):
        p_len = len(self.target_pattern)
        for s_idx in range(1, total_shoes + 1):
            res = self.play_shoe()
            colors, lengths = self.get_blocks(res)
            win_limit, loss_limit = self.current_capital * 0.10, self.current_capital * -0.20
            shoe_profit = 0.0
            shoe_finished = False

            for i in range(len(lengths) - p_len + 1):
                if shoe_finished: break
                match = True
                for k in range(p_len - 1):
                    if lengths[i+k] < self.target_pattern[k]: match = False; break
                if match and lengths[i+p_len-1] < self.target_pattern[-1]: match = False
                
                if match:
                    self.total_bets += 1
                    target_color = colors[i+p_len-1]
                    amt = self.bet_sequence[self.bet_idx]
                    
                    is_win = (lengths[i+p_len-1] == self.target_pattern[-1])
                    if is_win:
                        p = (amt if target_color == 'B' else amt * 0.95)
                        self.total_wins += 1; self.current_capital += p; shoe_profit += p
                        self.bet_idx = (self.bet_idx + 1) % len(self.bet_sequence)
                        # 连胜统计
                        self.curr_win_streak += 1; self.curr_loss_streak = 0
                        self.max_win_streak = max(self.max_win_streak, self.curr_win_streak)
                    else:
                        self.current_capital -= amt; shoe_profit -= amt
                        self.bet_idx = 0
                        # 连输统计
                        self.curr_loss_streak += 1; self.curr_win_streak = 0
                        self.max_loss_streak = max(self.max_loss_streak, self.curr_loss_streak)
                    
                    current_net = (self.current_capital + self.total_withdrawn) - self.total_recharge
                    self.balance_history.append(current_net)
                    
                    # 峰值与回撤计算
                    self.peak_profit = max(self.peak_profit, current_net)
                    drawdown = self.peak_profit - current_net
                    self.max_drawdown = max(self.max_drawdown, drawdown)

                    if self.current_capital <= 0:
                        self.bankrupt_count += 1; self.total_recharge += self.origin_base_cap
                        self.current_capital = self.origin_base_cap; self.bet_idx = 0
                        shoe_finished = True; break

                    if self.current_capital >= self.origin_base_cap * 3:
                        self.total_withdrawn += self.origin_base_cap; self.current_capital -= self.origin_base_cap

            self.current_capital += shoe_profit

    def get_blocks(self, res):
        colors, lengths = [], []
        if not res: return colors, lengths
        curr_c, curr_l = res[0], 0
        for r in res:
            if r == curr_c: curr_l += 1
            else:
                colors.append(curr_c); lengths.append(curr_l); curr_c, curr_l = r, 1
        colors.append(curr_c); lengths.append(curr_l)
        return colors, lengths

# --- Streamlit 界面更新 ---
st.set_page_config(page_title="策略回测系统", layout="wide")
st.title("🎰 策略深度回测报告")

with st.sidebar:
    st.header("⚙️ 参数设置")
    shoes = st.number_input("模拟靴数", value=1000)
    capital = st.number_input("起始本金", value=3000)
    unit = st.number_input("基码大小", value=50)
    pattern_str = st.text_input("匹配模式", value="2 4 4 1")
    bets_str = st.text_input("注码序列", value="1 3 2 4")
    run_btn = st.button("🚀 开始测算", use_container_width=True)

if run_btn:
    pattern = [int(x) for x in pattern_str.split()]
    bets = [float(x) for x in bets_str.split()]
    sim = BaccaratWebSimulator(pattern, bets, unit, capital)
    with st.spinner('计算中...'): sim.run_simulation(shoes)
    
    # 第一排指标
    c1, c2, c3, c4 = st.columns(4)
    final_net = (sim.current_capital + sim.total_withdrawn) - sim.total_recharge
    c1.metric("最终总净利", f"{final_net:.2f}")
    c2.metric("最大回撤(亏损)", f"-{sim.max_drawdown:.2f}")
    c3.metric("最大连胜", f"{sim.max_win_streak} 次")
    c4.metric("最大连输", f"{sim.max_loss_streak} 次")

    # 绘制曲线
    st.plotly_chart(px.line(sim.balance_history, title="资金净值波动"), use_container_width=True)
    
    # 第二排次要指标
    st.write(f"📊 **统计细节**: 总下注 {sim.total_bets} 次 | 破产 {sim.bankrupt_count} 次 | 胜率 {(sim.total_wins/sim.total_bets*100 if sim.total_bets>0 else 0):.2f}%")
