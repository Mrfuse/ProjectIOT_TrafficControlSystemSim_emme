import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 1. ตั้งค่าหน้าเว็บแบบเต็มจอ
st.set_page_config(
    page_title="Smart Traffic AIoT Control Center",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. ตั้งค่าการรีเฟรชหน้าจออัตโนมัติทุกๆ 1 วินาทีเพื่อให้นาฬิกาวิ่งแบบเรียลไทม์
st_autorefresh(interval=1000, limit=None, key="realtime_clock")

# 3. ตกแต่ง UI ด้วย Custom CSS (ฟอนต์ Prompt + การ์ดเรืองแสงสไตล์ศูนย์ควบคุม)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Prompt', sans-serif;
    }
    
    /* ตกแต่งการ์ด Metric */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #161b26, #1e2536);
        border: 1px solid #2e3b52;
        border-left: 5px solid #00d4ff;
        padding: 16px 20px;
        border-radius: 12px;
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.35);
    }
    
    /* ปรับแต่งหัวข้อแบนเนอร์ด้านบน */
    .main-banner {
        background: linear-gradient(90deg, #0f2027, #203a43, #2c5364);
        padding: 20px 28px;
        border-radius: 14px;
        border: 1px solid #3a6073;
        margin-bottom: 20px;
    }
    .main-banner h1 {
        color: #ffffff;
        margin: 0;
        font-size: 1.9rem;
        font-weight: 600;
    }
    .main-banner p {
        color: #b0c4de;
        margin: 5px 0 0 0;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 4. ระบบจัดการ MQTT เบื้องหลัง (Singleton Background Worker)
# ---------------------------------------------------------------------------
@st.cache_resource
def init_mqtt_store():
    store = {
        "connected": False,
        "ai_data": None,
        "closed_loop_data": None,
        "event_log": []
    }

    def on_connect(client, userdata, flags, rc, *args):
        store["connected"] = True
        client.subscribe("traffic/dashboard_ui")
        client.subscribe("traffic/closed_loop_report")

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            if msg.topic == "traffic/dashboard_ui":
                store["ai_data"] = payload
                store["closed_loop_data"] = None
                store["event_log"].insert(0, {
                    "เวลา": payload["timestamp"],
                    "เวลากักไฟ (s)": payload["tp"],
                    "รถสะสมรวม (คัน)": payload["physics"]["q_accumulated"],
                    "แผน AI (C1,C2,C3)": f"{payload['plan'][0]}s, {payload['plan'][1]}s, {payload['plan'][2]}s",
                    "ลดความล่าช้า (%)": payload["physics"]["pct_saved"]
                })
            elif msg.topic == "traffic/closed_loop_report":
                store["closed_loop_data"] = payload
        except Exception:
            pass

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    except AttributeError:
        client = mqtt.Client()

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("broker.hivemq.com", 1883, 60)
    client.loop_start()
    return store

store = init_mqtt_store()

# ---------------------------------------------------------------------------
# 5. แถบเมนูด้านซ้าย (Sidebar Status & Real-Time Clock)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⏰ เวลาปัจจุบัน (Real-Time)")
    current_time_live = time.strftime("%H:%M:%S")
    st.markdown(f"<h2 style='text-align: center; color: #00d4ff; margin: 0;'>{current_time_live}</h2>", unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("## 🛠️ สถานะระบบ (System Status)")
    if store["connected"]:
        st.success("🟢 **MQTT Broker:** ออนไลน์\n(`broker.hivemq.com`)")
    else:
        st.warning("🟡 **MQTT Broker:** กำลังเชื่อมต่อ...")

    if store["ai_data"]:
        r2 = store["ai_data"].get("r2_score", 0.985)
        st.info(f"🧠 **Cloud AI (Colab):** พร้อมทำงาน\nความแม่นยำ $R^2$ = `{r2}`")
    else:
        st.info("🧠 **Cloud AI (Colab):** รอรับข้อมูลแรก")

    if store["closed_loop_data"]:
        if store["closed_loop_data"].get("early_cut"):
            saved_s = store["closed_loop_data"].get("time_saved_sec", 0)
            st.warning(f"⚡ **Closed-Loop:** ตัดจบอัตโนมัติ!\n(ประหยัดเวลาไฟเขียว `{saved_s}` วินาที)")
        else:
            st.success("🔄 **Closed-Loop:** รันครบ 3 รอบสมบูรณ์")
    elif store["ai_data"]:
        st.warning("⏳ **ESP32 State:** กำลังฟื้นฟูไฟจราจร 3 รอบ...")
    else:
        st.info("📡 **ESP32 State:** ไฟจราจรปกติ (`NORMAL`)")

    st.divider()
    st.markdown("### 📌 ข้อมูลสถาปัตยกรรม")
    st.caption(
        "• **Edge Node:** ESP32 + Median Filter + Edge AI Fallback\n"
        "• **Cloud Brain:** Stochastic Multi-Output Random Forest\n"
        "• **Control Loop:** Closed-Loop Feedback & Early Termination"
    )
    if st.button("🗑️ ล้างประวัติเหตุการณ์", use_container_width=True):
        store["event_log"].clear()
        st.rerun()

# ---------------------------------------------------------------------------
# 6. แบนเนอร์หัวข้อหลัก (Main Header Banner)
# ---------------------------------------------------------------------------
st.markdown("""
<div class="main-banner">
    <h1>🚦 ศูนย์ควบคุมและฟื้นฟูสัญญาณไฟจราจรอัจฉริยะ (AIoT Digital Twin)</h1>
    <p>ระบบสมองกล AI เกลี่ยสัญญาณไฟ 3 รอบหลังเหตุการณ์รถฉุกเฉิน แบบวงจรปิด (Closed-Loop Multi-Cycle Recovery)</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 7. ส่วนแสดงผลหลัก (Main Dashboard Content)
# ---------------------------------------------------------------------------
if store["ai_data"] is None:
    st.info("💡 **ระบบพร้อมรับข้อมูลแล้ว!** กดปุ่มสีแดง (`btn_emg`) ในวงจร Wokwi เพื่อเริ่มจำลองเหตุการณ์รถพยาบาลวิ่งผ่านได้เลย")
else:
    data = store["ai_data"]
    phys = data["physics"]
    plan = data["plan"]
    cl_data = store["closed_loop_data"]

    if data.get("sensor_fault"):
        st.error("⚠️ **แจ้งเตือนฮาร์ดแวร์:** ตรวจพบความผิดปกติของเซนเซอร์ Ultrasonic (`HC-SR04`) ระบบสลับไปใช้ค่าสถิติสำรองอัตโนมัติ")

    # แถวที่ 1: การ์ดตัวเลข KPI 4 ใบ
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        label="🚑 เวลากักไฟรถฉุกเฉิน (Preempt)",
        value=f"{data['tp']} วินาที",
        delta=f"รถสายหลัก {data['qm']:.0f} คัน/นาที",
        delta_color="off"
    )
    m2.metric(
        label="🚗 รถสะสมรวม (Accumulated Queue)",
        value=f"{phys['q_accumulated']} คัน",
        delta=f"รถตั้งต้น {data['q0']:.0f} คัน + ไหลเข้าใหม่",
        delta_color="inverse"
    )
    m3.metric(
        label="🟢 เวลาไฟเขียวฟื้นฟูรวม 3 รอบ",
        value=f"{sum(plan)} วินาที",
        delta=f"C1: {plan[0]}s | C2: {plan[1]}s | C3: {plan[2]}s"
    )
    m4.metric(
        label="📉 ลดความล่าช้าสะสม (Delay Saved)",
        value=f"{phys['pct_saved']}%",
        delta=f"ระบายรถออกได้ {phys['cleared_cars']} คัน",
        delta_color="normal"
    )

    st.write("")

    # แถวที่ 2: กราฟ 3 ส่วน (Line Chart + Bar Chart + Gauge Meter)
    c_line, c_bar, c_gauge = st.columns([2.2, 1.3, 1.3])
    stages = ["หลังรถพยาบาลผ่าน", "จบรอบ 1 (C1)", "จบรอบ 2 (C2)", "จบรอบ 3 (C3)"]

    with c_line:
        st.markdown("##### 📈 การสลายตัวของแถวคอย (Queue Dissipation)")
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=stages, y=phys["conv_curve"],
            mode='lines+markers', name='ไฟปกติ (ไม่มี AI)',
            line=dict(color='#ff4b4b', width=3, dash='dash'),
            marker=dict(size=8, symbol='square')
        ))
        fig_line.add_trace(go.Scatter(
            x=stages, y=phys["ai_curve"],
            mode='lines+markers', name=f'แผน AI ({plan[0]}s,{plan[1]}s,{plan[2]}s)',
            line=dict(color='#00d4ff', width=4),
            marker=dict(size=10, symbol='circle')
        ))
        if cl_data and "actual_q_history" in cl_data:
            actual_q = cl_data["actual_q_history"]
            fig_line.add_trace(go.Scatter(
                x=stages[:len(actual_q)], y=actual_q,
                mode='lines+markers', name='เซนเซอร์จริง (Closed-Loop)',
                line=dict(color='#00e676', width=4, dash='dot'),
                marker=dict(size=11, symbol='triangle-up')
            ))
        fig_line.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(22,27,38,0.6)",
            yaxis_title="จำนวนรถสะสม (คัน)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=10, r=10, t=30, b=10),
            height=330
        )
        st.plotly_chart(fig_line, use_container_width=True)

    with c_bar:
        st.markdown("##### 📊 ความล่าช้าสะสม (Delay)")
        fig_bar = go.Figure(data=[
            go.Bar(
                x=["ระบบเดิม", "ระบบ AI"],
                y=[phys["delay_snapback"], phys["delay_ai"]],
                text=[f"{phys['delay_snapback']} s", f"{phys['delay_ai']} s"],
                textposition='auto',
                marker_color=['#ff9f43', '#00e676'],
                width=0.45
            )
        ])
        fig_bar.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(22,27,38,0.6)",
            yaxis_title="ดัชนีความล่าช้า (วินาที-คัน)",
            margin=dict(l=10, r=10, t=30, b=10),
            height=330
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with c_gauge:
        st.markdown("##### 🎯 ประสิทธิภาพการลดรถติด")
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=phys["pct_saved"],
            domain={'x': [0.05, 0.95], 'y': [0.15, 0.90]},
            number={'suffix': "%", 'font': {'size': 38, 'color': '#00e676'}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1},
                'bar': {'color': "#00d4ff"},
                'steps': [
                    {'range': [0, 40], 'color': "rgba(255, 75, 75, 0.25)"},
                    {'range': [40, 70], 'color': "rgba(255, 165, 0, 0.25)"},
                    {'range': [70, 100], 'color': "rgba(0, 230, 118, 0.25)"}
                ]
            }
        ))
        fig_gauge.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=30, r=35, t=10, b=10),
            height=330
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    # แถวที่ 3: ตารางแผนฟื้นฟูแบบมี Progress Bar และประวัติการทำงาน
    tab_col1, tab_col2 = st.columns([3, 2])

    with tab_col1:
        st.markdown("##### 📋 ตารางแผนการฟื้นฟู 3 รอบสัญญาณไฟ (AI Multi-Cycle Plan)")
        actual_c = cl_data["actual_q_history"][1:] if (cl_data and "actual_q_history" in cl_data) else ["รอผล...", "รอผล...", "รอผล..."]
        while len(actual_c) < 3:
            actual_c.append(0)

        df_plan = pd.DataFrame({
            "รอบสัญญาณไฟ": ["รอบที่ 1 (C1)", "รอบที่ 2 (C2)", "รอบที่ 3 (C3)"],
            "เวลาไฟเขียว (วินาที)": [plan[0], plan[1], plan[2]],
            "แถวคอยคาดการณ์ (AI)": [f"{phys['ai_curve'][1]} คัน", f"{phys['ai_curve'][2]} คัน", f"{phys['ai_curve'][3]} คัน"],
            "แถวคอยจริง (Sensor)": [
                f"{actual_c[0]} คัน" if isinstance(actual_c[0], (int, float)) else actual_c[0],
                f"{actual_c[1]} คัน" if isinstance(actual_c[1], (int, float)) else actual_c[1],
                f"{actual_c[2]} คัน" if isinstance(actual_c[2], (int, float)) else actual_c[2]
            ],
            "เป้าหมายเชิงวิศวกรรม": ["ตัดยอดวิกฤต (Peak Shaving)", "ปรับเกลี่ยสมดุล (Dynamic Balance)", "เก็บตกและซิงค์ไฟ (Resync)"]
        })
        st.dataframe(
            df_plan,
            use_container_width=True,
            hide_index=True,
            column_config={
                "เวลาไฟเขียว (วินาที)": st.column_config.ProgressColumn(
                    "ไฟเขียวฝั่งตัดขวาง (s)",
                    format="%d วินาที",
                    min_value=0,
                    max_value=16
                )
            }
        )

    with tab_col2:
        st.markdown("##### 🕒 ประวัติการเกิดเหตุฉุกเฉิน (Event Log)")
        if store["event_log"]:
            st.dataframe(
                pd.DataFrame(store["event_log"]),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ลดความล่าช้า (%)": st.column_config.ProgressColumn(
                        "ลดความล่าช้า (%)",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100
                    )
                }
            )
