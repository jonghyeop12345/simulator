import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import random

# 한글 폰트 및 마이너스 깨짐 방지 설정
plt.rcParams['axes.unicode_minus'] = False
st.set_page_config(layout="wide", page_title="전술 탄도 미사일 시뮬레이션 게임")

# =========================================================
# 1. 원본 물리 엔진 그대로 이식
# =========================================================
def calculate_advanced_physics(m_total, m_fuel, launch_angle, env_g, wind_speed, v_exhaust, burn_rate):
    m_dry = m_total - m_fuel
    dt = 0.2  # 고해상도 연산 타임스텝
    
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
            
        # 가속도 계산
        if is_burning:
            ax = (thrust * np.cos(theta)) / m_current
            ay = ((thrust * np.sin(theta)) / m_current) - env_g
        else:
            ax = 0.0
            ay = -env_g
            
        vx += ax * dt
        vy += ay * dt
        
        # 외부 대기 풍속 벡터 수평 결합
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
# 2. 게임 세션 및 상태 초기화
# =========================================================
if 'target_dist' not in st.session_state:
    st.session_state.target_dist = round(random.uniform(150.0, 850.0), 1)
    st.session_state.env_g = round(random.uniform(3.5, 11.0), 2)       
    st.session_state.wind = round(random.uniform(-50.0, 50.0), 1)      
    st.session_state.burn_rate = round(random.uniform(200.0, 550.0), 1)
    st.session_state.attempts_count = 0 
    st.session_state.total_damage_accumulated = 0.0
    st.session_state.game_over = False
    st.session_state.score_report = ""

st.title("🚀 TACTICAL MISSILE INTERCEPT SIMULATOR")
st.markdown("---")

col1, col2 = st.columns([1, 2])

# =========================================================
# 3. 좌측 제어판 (Tkinter 슬라이더 & 무작위 환경 구현)
# =========================================================
with col1:
    st.subheader("⚙️ TACTICAL CONTROL PANEL")
    
    # 4대 조절 변수 슬라이더
    m_total = st.slider("변수 1. 초기 총 질량 (M0 : kg)", 40000, 150000, 90000)
    v_exhaust = st.slider("변수 2. 가스 분출 속도 (V_e : m/s)", 1800, 3800, 3000)
    m_fuel = st.slider("변수 3. 탑재 연료 질량 (m_fuel : kg)", 10000, 80000, 50000)
    angle = st.slider("변수 4. 발사 초기 각도 (θ : deg)", 15, 85, 45)
    
    st.markdown("### 📡 [현장 기상 및 제한 스펙]")
    st.metric(label="🎯 임무 표적 사거리", value=f"{st.session_state.target_dist} km")
    
    wind_txt = f"순풍 (+){st.session_state.wind} m/s" if st.session_state.wind >= 0 else f"역풍 ({st.session_state.wind}) m/s"
    
    st.info(f"🪐 **작전구역 중력 (g) :** {st.session_state.env_g} m/s²  \n"
            f"💨 **상층부 국지 풍속 :** {wind_txt}  \n"
            f"🔥 **엔진 연료 소모율 :** {st.session_state.burn_rate} kg/s")
    
    # 물리 계산 예외 예방
    if m_fuel >= m_total:
        st.error("경고: 연료 질량이 초기 총 질량보다 많거나 같을 수 없습니다.")
        launch_disabled = True
    else:
        launch_disabled = False

    # 컨트롤 시스템 동작 버튼들
    btn_launch = st.button("🔥 미사일 발사 (ENGAGE)", use_container_width=True, disabled=launch_disabled)
    btn_reset = st.button("🔄 다음 턴 / 환경 재배정", use_container_width=True)

if btn_reset:
    # 모든 세션 초기화 후 리런
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# =========================================================
# 4. 우측 디스플레이 및 실시간 물리 가이드라인 모니터
# =========================================================
with col2:
    st.subheader("🖥️ 전술 관제 가이드라인 및 역학 실시간 분석기")
    
    if not launch_disabled:
        m0 = m_total
        m_dry = m0 - m_fuel
        delta_v = v_exhaust * np.log(m0 / m_dry)
        burn_time = m_fuel / st.session_state.burn_rate
        
        # 실시간 상황 맞춤형 역학 가이드라인 생성 로직
        if burn_time < 3.0:
            guide_text = "[물리 가이드]: 소모율 대비 연료량이 너무 적어 추진 가속 시간이 극도로 짧습니다. 질량비(M0/M)를 높이도록 연료를 증강하십시오."
            guide_color = "red"
        elif st.session_state.env_g > 9.0 and angle < 30:
            guide_text = f"[물리 가이드]: 현재 행성 중력({st.session_state.env_g} G)이 강한 상태에서 발사각이 너무 낮으면, 수직 운동량이 부족해 조기 추락합니다. 각도를 올리십시오."
            guide_color = "red"
        elif st.session_state.wind < -30 and delta_v < 1500:
            guide_text = "[물리 가이드]: 강한 상층부 역풍이 감지되었습니다. 수평 바람 저항에너지를 돌파하려면 가스 분출 속도(V_e)나 질량비를 높여 큰 Δv를 유도해야 합니다."
            guide_color = "yellow"
        elif angle > 75:
            guide_text = "[물리 가이드]: 발사 각도가 지나치게 고각입니다. 추진 에너지가 대부분 고도(수직) 성분으로 낭비되어 사거리가 급격히 감소할 수 있습니다."
            guide_color = "yellow"
        else:
            guide_text = "[물리 가이드]: 현재 설정된 추진제 질량비, 엔진 스펙, 벡터각은 안정적인 초기 탄도를 형성합니다. 목표 사거리를 예측하여 발사하십시오."
            guide_color = "green"
            
        st.code(f"▶ Δv = V_e × ln(M0 / M)  →  {v_exhaust:.0f} × ln({m0:.0f} / {m_dry:.0f}) = {delta_v:.1f} m/s\n"
                f"엔진 가속 제원 -> 추진제 연소(가속) 시간: {burn_time:.1f} 초", language="text")
        
        if guide_color == "red":
            st.error(guide_text)
        elif guide_color == "yellow":
            st.warning(guide_text)
        else:
            st.success(guide_text)

    # 발사 버튼을 눌렀을 때의 연산 및 드로잉
    if btn_launch and not launch_disabled:
        st.session_state.attempts_count += 1
        
        sim_data, max_v = calculate_advanced_physics(
            m_total, m_fuel, angle, st.session_state.env_g, 
            st.session_state.wind, v_exhaust, st.session_state.burn_rate
        )
        
        final_range = sim_data[-1]['Range']
        error = final_range - st.session_state.target_dist
        abs_error = abs(error)
        
        # 데미지 산출
        damage = int(100 * np.exp(-(abs_error / 65.0)**2))
        if damage < 0: damage = 0
        st.session_state.total_damage_accumulated += damage
        avg_damage = st.session_state.total_damage_accumulated / st.session_state.attempts_count
        
        # -------------------------------------------------
        # 레이더 추적 & 연료 차트 드로잉 (Tkinter 다크스타일 이식)
        # -------------------------------------------------
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8))
        fig.patch.set_facecolor('#0f172a')
        
        # 1) 레이더 고속 추적 스크린
        ax1.set_facecolor('#0f172a')
        ranges = [d['Range'] for d in sim_data]
        alts = [d['Altitude'] for d in sim_data]
        burn_mask = [d['Burning'] for d in sim_data]
        
        pow_r, pow_a = [], []
        coast_r, coast_a = [], []
        for r, a, b in zip(ranges, alts, burn_mask):
            if b:
                pow_r.append(r)
                pow_a.append(a)
            else:
                coast_r.append(r)
                coast_a.append(a)
                
        # 타겟 그리기
        ax1.plot(st.session_state.target_dist, 0, marker='o', markersize=14, color='#ef4444', label="목표 표적")
        
        # 궤적 그리기 (연소구간 / 관성구간 분리 표기)
        if pow_r:
            ax1.plot(pow_r, pow_a, color='#fb923c', lw=3.5, label="추진 가속 구간")
        if coast_r:
            if pow_r:
                coast_r.insert(0, pow_r[-1])
                coast_a.insert(0, pow_a[-1])
            ax1.plot(coast_r, coast_a, color='#38bdf8', lw=2.5, linestyle='--', label="관성 비행 구간")
            ax1.plot(ranges[-1], alts[-1], marker='^', markersize=13, color='#38bdf8')
        elif pow_r:
            ax1.plot(ranges[-1], alts[-1], marker='^', markersize=13, color='#fb923c')
            
        # 최고 고도 지점 마크
        max_alt_d = max(sim_data, key=lambda x: x['Altitude'])
        mx, my = max_alt_d['Range'], max_alt_d['Altitude']
        ax1.vlines(x=mx, ymin=0, ymax=my, colors='#cbd5e1', linestyles=':', lw=1.2, alpha=0.6)
        ax1.plot(mx, my, marker='*', markersize=12, color='#fde047')
        ax1.text(mx, my + (max(alts)*0.03 if max(alts) > 0 else 5), f"최고고도: {my:.1f}km", color='#fde047', ha='center', fontsize=9)
        
        ax1.set_title("레이더 추적 스크린 (Trajectory)", color='#00ffcc', fontsize=11, pad=12, weight='bold')
        ax1.set_xlabel("DISTANCE (km)", color='white')
        ax1.set_ylabel("ALTITUDE (km)", color='white')
        ax1.tick_params(colors='white')
        ax1.grid(True, color='#047857', linestyle='--', alpha=0.3)
        ax1.legend(facecolor='#0f172a', edgecolor='#334155', labelcolor='white')
        
        # 2) 선형 연료 소모 차트
        ax2.set_facecolor('#0f172a')
        times = [d['Time'] for d in sim_data]
        fuels = [d['Fuel'] for d in sim_data]
        ax2.plot(times, fuels, color='#34d399', lw=2)
        ax2.fill_between(times, fuels, 0, color='#10b981', alpha=0.25)
        
        ax2.set_title("실시간 선형 연료 소모 차트 (Cumulative Area)", color='#34d399', fontsize=11, pad=12, weight='bold')
        ax2.set_xlabel("TIME (sec)", color='white')
        ax2.set_ylabel("연료 잔량 (%)", color='#34d399')
        ax2.tick_params(colors='white')
        ax2.grid(True, linestyle=':', alpha=0.3)
        
        st.pyplot(fig)
        
        # 종합 성과 판단 결과 도출
        st.info(f"⚡ **격돌 직전 최고 비행 속도:** {max_v:.1f} m/s (낙하지점: {final_range:.1f} km)")
        
        if damage >= 95:
            attempt_score = max(0, 100 - (st.session_state.attempts_count - 1) * 10)
            final_score = int((attempt_score * 0.5) + (avg_damage * 0.5))
            
            st.balloons()
            st.success(f"🎯 **정밀 요격 성공! (이번 턴 피해율: {damage}%, 오차 범위: {error:+.1f} km)**")
            st.session_state.score_report = (
                f"### 🏆 최종 작전 성과 보고서\n"
                f"- **요격 시도 횟수:** {st.session_state.attempts_count}회 만에 요격\n"
                f"- **요격기 평균 피해율:** {avg_damage:.1f}%\n"
                f"- **🎖️ 최종 작전 평가 점수:** **{final_score} / 100 점**"
            )
            st.session_state.game_over = True
        else:
            if error > 0:
                st.error(f"❌ **요격 실패! 오차 {error:.1f}km 초과 (현재 {st.session_state.attempts_count}회차 시도)**")
                st.warning(f"**[관제소 가이드]** 추진 에너지가 과도합니다. 연료량을 감축하거나 발사각을 올리십시오.")
            else:
                st.error(f"❌ **요격 실패! 오차 {error:.1f}km 미달 (현재 {st.session_state.attempts_count}회차 시도)**")
                st.warning(f"**[관제소 가이드]** 추진 에너지가 행성 중력이나 역풍에 상쇄되었습니다. 추진력을 상향하십시오.")
            st.info(f"이번 발사 표적 피해율: **{damage}%** | 누적 평균 피해율: **{avg_damage:.1f}%**")
            
    if st.session_state.game_over:
        st.markdown("---")
        st.markdown(st.session_state.score_report)
        st.info("💡 위의 '다음 턴 / 환경 재배정' 버튼을 누르면 새로운 미션을 시작할 수 있습니다!")
