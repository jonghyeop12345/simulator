import sys
import subprocess
import random
import os

# 필수 라이브러리 자동 설치
try:
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "matplotlib", "numpy", "-q"])
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

# 한글 깨짐 방지 설정
import matplotlib
import platform

os_name = platform.system()
if os_name == 'Darwin':  # Mac
    matplotlib.rc('font', family='AppleGothic')
elif os_name == 'Windows':
    matplotlib.rc('font', family='Malgun Gothic')
else:
    matplotlib.rc('font', family='NanumGothic')
matplotlib.rcParams['axes.unicode_minus'] = False


# =========================================================
# 1. 교과서 방정식 기반 실시간 물리 역학 엔진
# =========================================================
def calculate_advanced_physics(m_total, m_fuel, launch_angle, env_g, wind_speed, v_exhaust, burn_rate):
    m_dry = m_total - m_fuel
    dt = 0.2  # 고해상도 연산을 위해 타임스텝 단축
    
    t, x, y = 0.0, 0.0, 0.0
    vx, vy = 0.0, 0.0
    m_current = m_total
    theta = np.radians(launch_angle)
    
    trajectory_data = []
    max_v = 0.0
    
    while y >= 0:
        if m_current > m_dry:
            # 추진력(Thrust) 연산: F = V * (dM/dt)
            thrust = v_exhaust * burn_rate
            m_current -= burn_rate * dt
            fuel_pct = ((m_current - m_dry) / m_fuel) * 100.0
            is_burning = True
        else:
            thrust = 0.0
            m_current = m_dry
            fuel_pct = 0.0
            is_burning = False
            
        # 가속도 계산: 질량이 실시간으로 감소하는 계의 운동 방정식 적용
        if is_burning:
            ax = (thrust * np.cos(theta)) / m_current
            ay = ((thrust * np.sin(theta)) / m_current) - env_g
        else:
            ax = 0.0
            ay = -env_g
            
        vx += ax * dt
        vy += ay * dt
        
        # 외부 대기 풍속 벡터 수평 결합 (바람 저항 모사)
        x += (vx + wind_speed) * dt
        y += vy * dt
        t += dt
        
        v_current = np.sqrt(vx**2 + vy**2)
        if v_current > max_v:
            max_v = v_current
            
        trajectory_data.append({
            'Time': t, 'Range': x / 1000.0, 'Altitude': y / 1000.0, 
            'Fuel': fuel_pct, 'Velocity': v_current, 'Burning': is_burning
        })
        
        if t > 1500 or x > 20000000:
            break
            
    return trajectory_data, max_v


# =========================================================
# 2. 전술 시뮬레이션 UI 및 동적 제어 시스템
# =========================================================
class TextbookPhysicsSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("전술 탄도 미사일 시뮬레이션 게임")
        self.root.geometry("1500x850")
        self.root.state('zoomed')
        
        self.sim_data = []
        self.current_idx = 0
        self.is_paused = False
        self.is_running = False
        self.attempts_count = 0  
        self.total_damage_accumulated = 0.0  # 평균 피해율을 위한 누적 데이터
        
        self.target_dist = 0.0
        self.env_g = 9.81
        self.wind = 0.0
        self.burn_rate = 350.0
        
        plt.style.use('dark_background')
        self.setup_ui()
        self.generate_next_mission_environment()
        
    def setup_ui(self):
        # 좌측 패널
        self.left_panel = ttk.Frame(self.root, padding=15)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y)
        
        # 우측 패널
        self.right_panel = ttk.Frame(self.root, padding=10)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        ttk.Label(self.left_panel, text="TACTICAL CONTROL PANEL", font=('Malgun Gothic', 11, 'bold'), foreground='#34d399').pack(anchor=tk.W, pady=5)
        
        # 4대 조절 변수 슬라이더
        self.m_total = self.add_control("변수 1. 초기 총 질량 (M0 : kg)", 40000, 150000, 90000, color='#fca5a5') 
        self.v_exhaust_slider = self.add_control("변수 2. 가스 분출 속도 (V_e : m/s)", 1800, 3800, 3000, color='#fde047') 
        self.m_fuel = self.add_control("변수 3. 탑재 연료 질량 (m_fuel : kg)", 10000, 80000, 50000, color='#86efac') 
        self.angle = self.add_control("변수 4. 발사 초기 각도 (θ : deg)", 15, 85, 45, color='#93c5fd') 
        
        # 무작위 환경 브리핑 전광판
        self.env_frame = tk.Frame(self.left_panel, bg='#1e293b', bd=2, relief=tk.SOLID, padx=12, pady=12)
        self.env_frame.pack(fill=tk.X, pady=15)
        
        self.lbl_target_display = tk.Label(self.env_frame, text="[임무 표적 사거리]", font=('Malgun Gothic', 10, 'bold'), bg='#1e293b', fg='#94a3b8', anchor='w')
        self.lbl_target_display.pack(fill=tk.X)
        self.lbl_target_val = tk.Label(self.env_frame, text="0.0 km", font=('Malgun Gothic', 15, 'bold'), bg='#1e293b', fg='#ef4444', anchor='w')
        self.lbl_target_val.pack(fill=tk.X, pady=2)
        
        self.lbl_env_brief = tk.Label(self.env_frame, text="[현장 기상 및 제한 스펙]", font=('Malgun Gothic', 10, 'bold'), bg='#1e293b', fg='#94a3b8', anchor='w')
        self.lbl_env_brief.pack(fill=tk.X, pady=(10, 2))
        
        self.lbl_env_desc = tk.Label(self.env_frame, text="중력가속도:\n풍속:\n연료소모율:", font=('Malgun Gothic', 10), bg='#1e293b', fg='#e2e8f0', justify='left', anchor='w')
        self.lbl_env_desc.pack(fill=tk.X, pady=2)
        
        # 제어 시스템 버튼
        self.btn_launch = tk.Button(self.left_panel, text="미사일 발사 (ENGAGE)", font=('Malgun Gothic', 11, 'bold'), bg='#059669', fg='white', command=self.start_sim)
        self.btn_launch.pack(fill=tk.X, pady=5)
        
        self.btn_pause = tk.Button(self.left_panel, text="정지 (HOLD)", font=('Malgun Gothic', 11, 'bold'), bg='#d97706', fg='white', command=self.toggle_hold, state=tk.DISABLED)
        self.btn_pause.pack(fill=tk.X, pady=5)
        
        self.btn_abort = tk.Button(self.left_panel, text="다음 턴 / 환경 재배정", font=('Malgun Gothic', 11, 'bold'), bg='#dc2626', fg='white', command=self.abort_sim)
        self.btn_abort.pack(fill=tk.X, pady=5)
        
        # HUD 전술 가이드라인 모니터
        self.hud_frame = tk.LabelFrame(self.right_panel, text="전술 관제 가이드라인 및 역학 실시간 분석기", font=('Malgun Gothic', 11, 'bold'), bg='#0f172a', fg='#94a3b8', padx=12, pady=12)
        self.hud_frame.pack(fill=tk.X, side=tk.TOP, pady=5)
        
        self.lbl_predict = tk.Label(self.hud_frame, text="현황: 데이터 대기 중...", font=('Malgun Gothic', 12, 'bold'), bg='#0f172a', fg='#38bdf8', anchor='w')
        self.lbl_predict.pack(fill=tk.X, pady=2)

        self.lbl_formula = tk.Label(self.hud_frame, text="▶ Δv = V_e × ln(M0 / M) 대기 중...", font=('Malgun Gothic', 12, 'bold'), bg='#0f172a', fg='#fde047', anchor='w')
        self.lbl_formula.pack(fill=tk.X, pady=3)
        
        self.lbl_velocity = tk.Label(self.hud_frame, text="이론적 가속 변량: 계산 중...", font=('Malgun Gothic', 11, 'bold'), bg='#0f172a', fg='#a78bfa', anchor='w')
        self.lbl_velocity.pack(fill=tk.X, pady=2)
        
        self.lbl_guide = tk.Label(self.hud_frame, text="실시간 상황 맞춤형 역학 가이드가 여기에 출력됩니다.", font=('Malgun Gothic', 10), bg='#0f172a', fg='#cbd5e1', anchor='w', justify='left')
        self.lbl_guide.pack(fill=tk.X, pady=2)

        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(11, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_panel)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def add_control(self, title, f, t, val, color='#cbd5e1'):
        frame = ttk.Frame(self.left_panel)
        frame.pack(fill=tk.X, pady=5)
        ttk.Label(frame, text=title, font=('Malgun Gothic', 11, 'bold'), foreground=color).pack(anchor=tk.W)
        var = tk.DoubleVar(value=val)
        scale = tk.Scale(frame, from_=f, to=t, variable=var, orient=tk.HORIZONTAL, bg='#1e293b', fg='white', command=lambda e: self.update_physics_hints())
        scale.pack(fill=tk.X)
        return var

    def generate_next_mission_environment(self):
        self.target_dist = round(random.uniform(150.0, 850.0), 1)
        self.env_g = round(random.uniform(3.5, 11.0), 2)       
        self.wind = round(random.uniform(-50.0, 50.0), 1)      
        self.burn_rate = round(random.uniform(200.0, 550.0), 1)
        
        self.attempts_count = 0 
        self.total_damage_accumulated = 0.0  # 새 미션 시작 시 누적 데미지 초기화
        
        self.lbl_target_val.config(text=f"{self.target_dist} km")
        
        wind_txt = f"순풍 (+){self.wind} m/s" if self.wind >= 0 else f"역풍 ({self.wind}) m/s"
        self.lbl_env_desc.config(
            text=f"- 작전구역 중력 (g) : {self.env_g} m/s²\n"
                 f"- 상층부 국지 풍속  : {wind_txt}\n"
                 f"- 엔진 연료 소모율  : {self.burn_rate} kg/s"
        )
        self.update_physics_hints()

    def update_physics_hints(self):
        if self.is_running: return
        if self.m_fuel.get() >= self.m_total.get():
            self.lbl_velocity.config(text="경고: 연료 질량이 초기 총 질량보다 많거나 같을 수 없습니다.", fg='#ef4444')
            return
            
        m0 = self.m_total.get()
        m_dry = m0 - self.m_fuel.get()
        v_exhaust_val = self.v_exhaust_slider.get()
        
        delta_v = v_exhaust_val * np.log(m0 / m_dry)
        burn_time = self.m_fuel.get() / self.burn_rate
        
        self.lbl_predict.config(text=f"현황: [ {self.attempts_count + 1}회차 작전 분석 중 ] 제공된 데이터 지표를 계산하여 임무를 수행하십시오.", fg='#38bdf8')
        
        self.lbl_formula.config(text=f"▶ Δv = V_e × ln(M0 / M)  →  {v_exhaust_val:.0f} × ln({m0:.0f} / {m_dry:.0f}) = {delta_v:.1f} m/s")
        
        self.lbl_velocity.config(
            text=f"엔진 가속 제원 -> 추진제 연소(가속) 시간: {burn_time:.1f} 초"
        )
        
        guide_text = ""
        if burn_time < 3.0:
            guide_text = "[물리 가이드]: 소모율 대비 연료량이 너무 적어 추진 가속 시간이 극도로 짧습니다. 질량비(M0/M)를 높이도록 연료를 증강하십시오."
        elif self.env_g > 9.0 and self.angle.get() < 30:
            guide_text = f"[물리 가이드]: 현재 행성 중력({self.env_g} G)이 강한 상태에서 발사각이 너무 낮으면, 수직 운동량이 부족해 조기 추락합니다. 각도를 올리십시오."
        elif self.wind < -30 and delta_v < 1500:
            guide_text = "[물리 가이드]: 강한 상층부 역풍이 감지되었습니다. 수평 바람 저항에너지를 돌파하려면 가스 분출 속도(V_e)나 질량비를 높여 큰 Δv를 유도해야 합니다."
        elif self.angle.get() > 75:
            guide_text = "[물리 가이드]: 발사 각도가 지나치게 고각입니다. 추진 에너지가 대부분 고도(수직) 성분으로 낭비되어 사거리가 급격히 감소할 수 있습니다."
        else:
            guide_text = "[물리 가이드]: 현재 설정된 추진제 질량비, 엔진 스펙, 벡터각은 안정적인 초기 탄도를 형성합니다. 목표 사거리를 예측하여 발사하십시오."
            
        self.lbl_guide.config(text=guide_text, fg='#e2e8f0')
        
        self.ax1.clear()
        self.ax2.clear()
        
        self.ax1.plot(self.target_dist, 0, marker='o', markersize=14, color='#ef4444', label="목표 표적")
        self.ax1.set_title("레이더 고속 추적 스크린 (Trajectory)", color='#00ffcc', fontsize=11, pad=12, weight='bold')
        self.ax1.set_xlim(0, max(self.target_dist * 1.3, 300))
        self.ax1.set_ylim(0, max(self.target_dist * 0.4, 100))
        self.ax1.set_xlabel("DISTANCE (km)")
        self.ax1.set_ylabel("ALTITUDE (km)")
        self.ax1.grid(True, color='#047857', linestyle='--', alpha=0.2)
        self.ax1.legend(loc='upper right', fontsize=9, facecolor='#0f172a', edgecolor='#334155', labelcolor='white')
        
        self.ax2.set_title("실시간 선형 연료 소모 차트 (Cumulative Area)", color='#34d399', fontsize=11, pad=12, weight='bold')
        self.ax2.grid(True, linestyle=':', alpha=0.2)
        
        self.canvas.draw()

    def start_sim(self):
        if self.m_fuel.get() >= self.m_total.get():
            messagebox.showerror("설정 오류", "연료 질량이 총 질량보다 크거나 같을 수 없습니다!")
            return
            
        self.attempts_count += 1
            
        self.sim_data, self.final_max_v = calculate_advanced_physics(
            self.m_total.get(), self.m_fuel.get(), self.angle.get(), 
            self.env_g, self.wind, self.v_exhaust_slider.get(), self.burn_rate
        )
        
        self.lbl_predict.config(text="[비행 중] 탄도 미사일이 가속 기동 중입니다. 레이더 스크린 실시간 동기화 중...", fg='#eab308')
        
        ranges = [d['Range'] for d in self.sim_data]
        alts = [d['Altitude'] for d in self.sim_data]
        self.lim_x = max(max(ranges), self.target_dist) * 1.15
        self.lim_y = max(alts) * 1.15
        self.lim_t = max([d['Time'] for d in self.sim_data])
        
        self.current_idx = 0
        self.is_running = True
        self.is_paused = False
        
        self.btn_launch.config(state=tk.DISABLED, bg='#334155')
        self.btn_pause.config(state=tk.NORMAL, bg='#d97706')
        
        self.fast_animate_radar()

    def toggle_hold(self):
        if not self.is_running: return
        if self.is_paused:
            self.is_paused = False
            self.btn_pause.config(text="정지 (HOLD)", bg='#d97706')
            self.fast_animate_radar()
        else:
            self.is_paused = True
            self.btn_pause.config(text="재개 (RESUME)", bg='#059669')

    def abort_sim(self):
        self.is_running = False
        self.is_paused = False
        self.btn_launch.config(state=tk.NORMAL, bg='#059669')
        self.btn_pause.config(state=tk.DISABLED, bg='#475569')
        self.generate_next_mission_environment()

    def give_post_simulation_guidance(self, final_range):
        target = self.target_dist
        error = final_range - target
        abs_error = abs(error)
        
        # 데미지 산출 및 누적 (스코어 계산용)
        damage = int(100 * np.exp(-(abs_error / 65.0)**2))
        if damage < 0: damage = 0
        self.total_damage_accumulated += damage
        avg_damage = self.total_damage_accumulated / self.attempts_count
        
        self.lbl_predict.config(text=f"[요격 분석 보고서] 이번 턴 피해율: {damage}% (오차 범위: {error:+.1f} km)", fg='#67e8f9')
        self.lbl_velocity.config(text=f"격돌 직전 최고 비행 속도: {self.final_max_v:.1f} m/s (낙하지점: {final_range:.1f} km)")
        
        if damage >= 95:
            # 100점 만점 평가 점수 산출
            # 1) 시도 횟수 점수: 원샷원킬 시 100점, 추가 시도 1회당 10점씩 감점
            attempt_score = max(0, 100 - (self.attempts_count - 1) * 10)
            # 2) 종합 산출: 시도 횟수(50%) + 평균 피해율(50%) 반영
            final_score = int((attempt_score * 0.5) + (avg_damage * 0.5))
            
            self.lbl_guide.config(text=f"[역학 마스터] 요격 성공! 종합 평가 {final_score}점 획득! 물리 수식 연산으로 변수를 완벽히 극복했습니다!", fg='#34d399')
            
            result_msg = (
                f"🎯 정밀 요격 성공!\n\n"
                f"최종 표적 피해율: {damage}%\n"
                f"요격 시도 횟수: {self.attempts_count}회\n"
                f"요격기 평균 피해율: {avg_damage:.1f}%\n"
                f"================================\n"
                f"★ 최종 작전 평가: {final_score} / 100 점 ★\n"
                f"================================\n\n"
                f"확인을 누르면 다음 턴 환경으로 재배정됩니다."
            )
            messagebox.showinfo("미션 성과 보고서", result_msg)
            return True
        elif error > 0:
            self.lbl_guide.config(text=f"[관제소 가이드]: {self.attempts_count}회차 시도 실패 (평균 피해율: {avg_damage:.1f}%). 오차 {error:.1f}km 초과. 추진 에너지가 너무 높습니다. 설정을 감축하거나 각도를 올리십시오.", fg='#f87171')
            return False
        else:
            self.lbl_guide.config(text=f"[관제소 가이드]: {self.attempts_count}회차 시도 실패 (평균 피해율: {avg_damage:.1f}%). 오차 {error:.1f}km 미달. 행성 중력이나 역풍에 에너지가 상쇄되었습니다. 추진 에너지를 상향하십시오.", fg='#fbbf24')
            return False

    def fast_animate_radar(self):
        if not self.is_running or self.is_paused: return
        
        step = max(1, int(len(self.sim_data) / 30)) 
        
        if self.current_idx >= len(self.sim_data):
            final_range = self.sim_data[-1]['Range']
            is_success = self.give_post_simulation_guidance(final_range)
            
            if is_success:
                self.abort_sim()
            else:
                self.btn_launch.config(state=tk.NORMAL, bg='#059669')
                self.btn_pause.config(state=tk.DISABLED, bg='#475569')
                self.is_running = False
            return
            
        sub = self.sim_data[:self.current_idx + 1]
        
        sub_t = [d['Time'] for d in sub]
        sub_r = [d['Range'] for d in sub]
        sub_a = [d['Altitude'] for d in sub]
        sub_f = [d['Fuel'] for d in sub]
        sub_b = [d['Burning'] for d in sub]
        
        pow_r, pow_a = [], []
        coast_r, coast_a = [], []
        for r, a, b in zip(sub_r, sub_a, sub_b):
            if b:
                pow_r.append(r)
                pow_a.append(a)
            else:
                coast_r.append(r)
                coast_a.append(a)
        
        self.ax1.clear()
        self.ax1.plot(self.target_dist, 0, marker='o', markersize=14, color='#ef4444', label="목표 표적")
        
        if pow_r:
            self.ax1.plot(pow_r, pow_a, color='#fb923c', lw=3.5, label="추진 가속 구간")
        if coast_r:
            if pow_r:
                coast_r.insert(0, pow_r[-1])
                coast_a.insert(0, pow_a[-1])
            self.ax1.plot(coast_r, coast_a, color='#38bdf8', lw=2.5, linestyle='--', label="관성 비행 구간")
            self.ax1.plot(sub_r[-1], sub_a[-1], marker='^', markersize=13, color='#38bdf8')
        elif pow_r:
            self.ax1.plot(sub_r[-1], sub_a[-1], marker='^', markersize=13, color='#fb923c')

        max_alt_d = max(self.sim_data, key=lambda x: x['Altitude'])
        max_idx = self.sim_data.index(max_alt_d)
        if self.current_idx >= max_idx and max_alt_d['Altitude'] > 0:
            mx, my = max_alt_d['Range'], max_alt_d['Altitude']
            self.ax1.vlines(x=mx, ymin=0, ymax=my, colors='#cbd5e1', linestyles=':', lw=1.2, alpha=0.6)
            self.ax1.plot(mx, my, marker='*', markersize=12, color='#fde047')
            self.ax1.text(mx, my + (self.lim_y * 0.03), f"최고고도: {my:.1f}km", color='#fde047', ha='center', fontsize=9)
        
        self.ax1.set_title("레이더 고속 추적 스크린 (Trajectory)", color='#00ffcc', fontsize=11, pad=12, weight='bold')
        self.ax1.set_xlim(0, self.lim_x)
        self.ax1.set_ylim(0, self.lim_y)
        self.ax1.set_xlabel("DISTANCE (km)")
        self.ax1.set_ylabel("ALTITUDE (km)")
        self.ax1.grid(True, color='#047857', linestyle='--', alpha=0.3)
        self.ax1.legend(loc='upper right', fontsize=9, facecolor='#0f172a', edgecolor='#334155', labelcolor='white')

        self.ax2.clear()
        self.ax2.plot(sub_t, sub_f, color='#34d399', lw=2)
        self.ax2.fill_between(sub_t, sub_f, 0, color='#10b981', alpha=0.25)
        
        self.ax2.set_title("실시간 선형 연료 소모 차트 (Cumulative Area)", color='#34d399', fontsize=11, pad=12, weight='bold')
        self.ax2.set_xlabel("TIME (sec)")
        self.ax2.set_ylabel("연료 잔량 (%)", color='#34d399')
        self.ax2.set_xlim(0, self.lim_t)
        self.ax2.set_ylim(-5, 105)
        self.ax2.grid(True, linestyle=':', alpha=0.3)

        self.canvas.draw()
        
        self.current_idx += step
        self.root.after(30, self.fast_animate_radar)

if __name__ == "__main__":
    root = tk.Tk()
    app = TextbookPhysicsSimulator(root)
    root.mainloop()
