import streamlit as st
import streamlit.components.v1 as components
import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime, timezone, timedelta
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 1. กำหนดโซนเวลาประเทศไทย (UTC+7)
TH_TIMEZONE = timezone(timedelta(hours=7))

# 2. ตั้งค่าหน้าเว็บและชื่อโปรเจกต์ตามที่กำหนด
st.set_page_config(
    page_title="แบบจำลองระบบควบคุมและปรับสมดุลแถวคอยจราจรอัจฉริยะหลังการแทรกสัญญาณไฟของรถฉุกเฉิน",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 3. รีเฟรชอัตโนมัติทุก 1 วินาที
st_autorefresh(interval=1000, limit=None, key="traffic_os_autorefresh")

# 4. ตกแต่ง UX/UI โฉมใหม่ (Carbon Obsidian & Amber/Emerald Bento Grid)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

    :root {
        --bg-obsidian: #090A0F;
        --bg-surface: #12141D;
        --bg-elevated: #181B26;
        --border-subtle: #262A3B;
        --accent-amber: #F59E0B;
        --accent-emerald: #10B981;
        --accent-indigo: #6366F1;
        --accent-rose: #F43F5E;
        --text-primary: #F8FAFC;
        --text-muted: #94A3B8;
    }

    .stApp {
        background-color: var(--bg-obsidian);
        background-image: 
            radial-gradient(at 0% 0%, rgba(245, 158, 11, 0.07) 0px, transparent 45%),
            radial-gradient(at 100% 0%, rgba(16, 185, 129, 0.06) 0px, transparent 45%);
        color: var(--text-primary);
        font-family: 'Plus Jakarta Sans', 'IBM Plex Sans Thai', sans-serif;
    }

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', 'IBM Plex Sans Thai', sans-serif !important;
    }

    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
        max-width: 1440px !important;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Top Project Header Bar */
    .os-navbar {
        background: linear-gradient(135deg, rgba(18, 20, 29, 0.95) 0%, rgba(24, 27, 38, 0.92) 100%);
        backdrop-filter: blur(16px);
        border: 1px solid var(--border-subtle);
        border-left: 5px solid var(--accent-amber);
        border-radius: 18px;
        padding: 18px 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
        margin-bottom: 16px;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
    }

    .os-brand {
        display: flex;
        align-items: center;
        gap: 16px;
        flex: 1;
        min-width: 300px;
    }

    .os-logo-badge {
        width: 52px;
        height: 52px;
        border-radius: 14px;
        background: linear-gradient(135deg, #F59E0B 0%, #EA580C 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.6rem;
        flex-shrink: 0;
        box-shadow: 0 0 20px rgba(245, 158, 11, 0.35);
    }

    .os-title-group h1 {
        font-size: 1.25rem;
        font-weight: 700;
        color: #FFFFFF;
        margin: 0;
        line-height: 1.35;
    }

    .os-title-group p {
        font-size: 0.84rem;
        color: #FBBF24;
        margin: 4px 0 0 0;
        font-weight: 500;
        letter-spacing: 0.01em;
    }

    .os-telemetry-pills {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
    }

    .t-pill {
        background: var(--bg-elevated);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 8px 13px;
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.78rem;
        font-weight: 600;
        color: #E2E8F0;
    }

    .t-pill .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
    }

    .dot-online { background: #10B981; box-shadow: 0 0 8px #10B981; }
    .dot-warn { background: #F59E0B; box-shadow: 0 0 8px #F59E0B; }
    .dot-danger { background: #F43F5E; box-shadow: 0 0 8px #F43F5E; }

    .clock-pill {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1rem;
        font-weight: 700;
        color: #F59E0B;
        background: rgba(245, 158, 11, 0.12);
        border: 1px solid rgba(245, 158, 11, 0.4);
        padding: 8px 15px;
        border-radius: 12px;
    }

    /* Bento KPI Cards */
    .bento-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 14px;
        margin: 14px 0 20px 0;
    }

    .bento-card {
        background: linear-gradient(160deg, #131620 0%, #0E1017 100%);
        border: 1px solid var(--border-subtle);
        border-radius: 16px;
        padding: 18px 20px;
        position: relative;
        overflow: hidden;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    }

    .bento-card::before {
        content: "";
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
    }

    .bento-amber::before { background: linear-gradient(90deg, #F59E0B, #FBBF24); }
    .bento-rose::before { background: linear-gradient(90deg, #F43F5E, #FB7185); }
    .bento-emerald::before { background: linear-gradient(90deg, #10B981, #34D399); }
    .bento-indigo::before { background: linear-gradient(90deg, #6366F1, #818CF8); }

    .bento-label {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--text-muted);
        margin-bottom: 8px;
    }

    .bento-value {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.85rem;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1.15;
    }

    .bento-sub {
        margin-top: 8px;
        font-size: 0.78rem;
        color: #CBD5E1;
        display: inline-block;
        padding: 3px 9px;
        border-radius: 6px;
        background: rgba(255, 255, 255, 0.05);
    }

    .section-header {
        font-size: 0.98rem;
        font-weight: 600;
        color: #F8FAFC;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .panel-box {
        background: var(--bg-surface);
        border: 1px solid var(--border-subtle);
        border-radius: 16px;
        padding: 14px 18px;
        margin-bottom: 14px;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 5. ระบบจัดการ MQTT เบื้องหลังแบบ Triple-Topic Sync (เชื่อม Wokwi + Colab + Streamlit)
# ---------------------------------------------------------------------------
def compute_fallback_physics(tp, q0, qm, plan):
    lambda_s = 0.25
    s = 0.65
    q_acc = round(q0 + (lambda_s * tp), 2)
    q_ai_c1 = round(max(0.0, q_acc - (plan[0] * s)), 2)
    q_ai_c2 = round(max(0.0, q_ai_c1 - (plan[1] * s)), 2)
    q_ai_c3 = round(max(0.0, q_ai_c2 - (plan[2] * s)), 2)

    q_conv_c1 = round(max(0.0, q_acc - (2.0 * s) + (lambda_s * 3.0)), 2)
    q_conv_c2 = round(max(0.0, q_conv_c1 - (2.0 * s) + (lambda_s * 3.0)), 2)
    q_conv_c3 = round(max(0.0, q_conv_c2 - (2.0 * s) + (lambda_s * 3.0)), 2)

    cleared_cars = round(q_acc - q_ai_c3, 2)
    delay_snapback = round(((q_acc ** 2) / 16.0) + (tp * 10.5), 2)
    delay_ai = round(((q_ai_c3 ** 2) / 8.0) + (qm * 1.0) + (sum(plan) * 0.8), 2)
    pct_saved = round(max(0.0, ((delay_snapback - delay_ai) / delay_snapback) * 100.0), 1)

    return {
        "q_accumulated": q_acc,
        "ai_curve": [q_acc, q_ai_c1, q_ai_c2, q_ai_c3],
        "conv_curve": [q_acc, q_conv_c1, q_conv_c2, q_conv_c3],
        "cleared_cars": cleared_cars,
        "delay_snapback": delay_snapback,
        "delay_ai": delay_ai,
        "pct_saved": pct_saved
    }

@st.cache_resource
def init_mqtt_store():
    store = {
        "connected": False,
        "ai_data": None,
        "closed_loop_data": None,
        "event_log": [],
        "event_seq": 0,
        "source_mode": "Standby"
    }

    def on_connect(client, userdata, flags, rc, *args):
        store["connected"] = True
        # ดักฟังครบทั้ง 3 หัวข้อเพื่อให้ซิงค์กับทั้ง Wokwi และ Colab แบบไร้รอยต่อ
        client.subscribe("traffic/preempt_data")
        client.subscribe("traffic/dashboard_ui")
        client.subscribe("traffic/closed_loop_report")

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            current_th_time = datetime.now(TH_TIMEZONE).strftime("%H:%M:%S")

            # กรณีที่ 1: รับค่าจาก Google Colab (Cloud AI ประมวลผลเสร็จ)
            if msg.topic == "traffic/dashboard_ui":
                store["ai_data"] = payload
                store["closed_loop_data"] = None
                store["event_seq"] += 1
                store["source_mode"] = "Cloud AI (Colab)"
                store["event_log"].insert(0, {
                    "เวลา (UTC+7)": current_th_time,
                    "โหมดประมวลผล": "Cloud AI (Colab)",
                    "กักไฟ (s)": payload["tp"],
                    "คิวสะสม (คัน)": payload["physics"]["q_accumulated"],
                    "แผน AI 4-Phase": f"{payload['plan'][0]}s / {payload['plan'][1]}s / {payload['plan'][2]}s",
                    "ลดความล่าช้า (%)": payload["physics"]["pct_saved"]
                })

            # กรณีที่ 2: รับค่าตรงจากบอร์ด Wokwi ทันทีที่กดปุ่มฉุกเฉิน (ซิงค์ทันทีแม้ Colab ยังไม่ตอบกลับ)
            elif msg.topic == "traffic/preempt_data":
                tp = round(float(payload.get("preempt_duration", 6.0)), 1)
                q0 = round(float(payload.get("side_queue", 6.0)), 1)
                qm = round(float(payload.get("main_flow", 28.0)), 1)
                sf = bool(payload.get("sensor_fault", False))
                if sf:
                    q0 = 8.0
                q_total = q0 + (0.25 * tp)
                phi = max(0.45, min(1.0, 1.0 - (qm / 120.0)))
                g1 = max(4, min(16, int(round((q_total * 1.6) * 0.50 * phi))))
                g2 = max(3, min(10, int(round((q_total * 1.6) * 0.32 * phi))))
                g3 = max(2, min(6, int(round((q_total * 1.6) * 0.18 * phi))))
                plan = [g1, g2, g3]
                phys = compute_fallback_physics(tp, q0, qm, plan)

                # หากยังไม่มีข้อมูลจาก Colab ในรอบวินาทีเดียวกัน ให้อัปเดตแสดงผลทันที
                store["ai_data"] = {
                    "timestamp": current_th_time,
                    "tp": tp,
                    "q0": q0,
                    "qm": qm,
                    "sensor_fault": sf,
                    "plan": plan,
                    "r2_score": 0.9629,
                    "physics": phys
                }
                store["closed_loop_data"] = None
                store["event_seq"] += 1
                store["source_mode"] = "Wokwi Edge -> AI"

            # กรณีที่ 3: รับรายงานผล Closed-Loop จริงจากบอร์ด Wokwi หลังจบ 3 รอบ
            elif msg.topic == "traffic/closed_loop_report":
                store["closed_loop_data"] = payload
                if payload.get("used_edge_ai"):
                    store["source_mode"] = "Edge AI (ESP32)"
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
# 6. ฟังก์ชันสร้าง HTML5 Canvas Animation (Zero-Collision & Non-Intersecting 4-Phase)
# ---------------------------------------------------------------------------
def build_4phase_animation_html(ai_data, cl_data, event_seq):
    tp_val = float(ai_data["tp"]) if ai_data else 6.0
    q0_val = float(ai_data["q0"]) if ai_data else 6.0
    qm_val = float(ai_data["qm"]) if ai_data else 28.0
    plan_val = ai_data["plan"] if ai_data else [7, 5, 3]

    phys_default = compute_fallback_physics(tp_val, q0_val, qm_val, plan_val)

    sim_config = {
        "has_event": ai_data is not None,
        "event_seq": event_seq,
        "tp": tp_val,
        "q0": q0_val,
        "qm": qm_val,
        "sensor_fault": bool(ai_data.get("sensor_fault", False)) if ai_data else False,
        "plan": plan_val,
        "r2_score": float(ai_data.get("r2_score", 0.9629)) if ai_data else 0.9629,
        "q_accumulated": float(ai_data["physics"]["q_accumulated"]) if ai_data else phys_default["q_accumulated"],
        "ai_curve": ai_data["physics"]["ai_curve"] if ai_data else phys_default["ai_curve"],
        "conv_curve": ai_data["physics"]["conv_curve"] if ai_data else phys_default["conv_curve"],
        "pct_saved": float(ai_data["physics"]["pct_saved"]) if ai_data else phys_default["pct_saved"],
        "cl_active": cl_data is not None,
        "actual_q_history": cl_data.get("actual_q_history", []) if cl_data else [],
        "early_cut": bool(cl_data.get("early_cut", False)) if cl_data else False,
        "used_edge_ai": bool(cl_data.get("used_edge_ai", False)) if cl_data else False,
        "time_saved_sec": int(cl_data.get("time_saved_sec", 0)) if cl_data else 0,
    }
    config_json = json.dumps(sim_config)

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&family=Plus+Jakarta+Sans:wght@600;700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
        body {
            background: transparent;
            font-family: 'Plus Jakarta Sans', 'IBM Plex Sans Thai', sans-serif;
            color: #F8FAFC;
            overflow: hidden;
            padding: 2px;
        }
        .cockpit-shell {
            background: #12141D;
            border: 1px solid #262A3B;
            border-radius: 18px;
            padding: 14px 18px 16px 18px;
            box-shadow: 0 14px 36px rgba(0, 0, 0, 0.55);
        }
        .cockpit-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 1px solid #222636;
        }
        .cockpit-title {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.94rem;
            font-weight: 700;
            color: #F8FAFC;
            flex-wrap: wrap;
        }
        .phase-tag {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            padding: 4px 12px;
            border-radius: 8px;
            background: rgba(245, 158, 11, 0.14);
            border: 1px solid #F59E0B;
            color: #FBBF24;
            font-weight: 600;
        }
        .ctrl-group {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .ctrl-btn {
            background: #1A1D2B;
            color: #E2E8F0;
            border: 1px solid #2E3348;
            padding: 6px 13px;
            border-radius: 9px;
            font-family: 'IBM Plex Sans Thai', sans-serif;
            font-size: 0.78rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.18s ease;
        }
        .ctrl-btn:hover {
            background: #252A3D;
            border-color: #F59E0B;
            color: #FFFFFF;
        }
        .viewport-frame {
            position: relative;
            width: 100%;
            height: 410px;
            background: #0D0F17;
            border-radius: 14px;
            overflow: hidden;
            border: 1px solid #25293A;
        }
        canvas {
            width: 100%;
            height: 100%;
            display: block;
        }
        /* แถบอธิบายสถานะแยกออกมาด้านล่าง Canvas เพื่อไม่ให้บังถนนแนวตั้ง */
        .telemetry-status-strip {
            margin-top: 10px;
            background: #171A26;
            border: 1px solid #2B3044;
            border-left: 4px solid #F59E0B;
            border-radius: 10px;
            padding: 8px 14px;
            font-size: 0.8rem;
            font-weight: 500;
            color: #F8FAFC;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
        }
        .scrubber-bar {
            margin-top: 10px;
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 8px;
        }
        .step-node {
            text-align: center;
            padding: 9px 6px;
            border-radius: 10px;
            background: #171A26;
            border: 1px solid #262B3D;
            color: #94A3B8;
            font-size: 0.76rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .step-node:hover {
            border-color: #6366F1;
            color: #FFFFFF;
        }
        .step-node.active-rec {
            background: rgba(16, 185, 129, 0.18);
            border: 1.5px solid #10B981;
            color: #FFFFFF;
            box-shadow: 0 0 14px rgba(16, 185, 129, 0.3);
        }
        .step-node.active-emg {
            background: rgba(244, 63, 94, 0.22);
            border: 1.5px solid #F43F5E;
            color: #FFFFFF;
            box-shadow: 0 0 14px rgba(244, 63, 94, 0.35);
        }
        .step-node.active-norm {
            background: rgba(245, 158, 11, 0.2);
            border: 1.5px solid #F59E0B;
            color: #FFFFFF;
            box-shadow: 0 0 12px rgba(245, 158, 11, 0.28);
        }
    </style>
    </head>
    <body>
    <div class="cockpit-shell">
        <div class="cockpit-header">
            <div class="cockpit-title">
                <span>⚡ DIGITAL TWIN: 4-PHASE SMART INTERSECTION (ทางตรง + เลี้ยวขวาแยกอิสระ 12 LEDs)</span>
                <span id="phaseBadge" class="phase-tag">INITIALIZING...</span>
            </div>
            <div class="ctrl-group">
                <button class="ctrl-btn" onclick="startLiveSync()">📡 ซิงค์เวลาจริงกับ Wokwi</button>
                <button class="ctrl-btn" onclick="startFullReplay()">🎬 เล่นซ้ำตั้งแต่รถพยาบาลแทรกไฟ</button>
                <button class="ctrl-btn" onclick="togglePause()">⏯️ หยุด / เล่นต่อ</button>
            </div>
        </div>

        <div class="viewport-frame">
            <canvas id="simCanvas" width="1180" height="410"></canvas>
        </div>

        <div class="telemetry-status-strip">
            <span id="statusDescText">⚡ กำลังซิงค์สถานะวงจรไฟจราจร 4 เฟส...</span>
            <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #FBBF24;">Zero-Conflict 4-Phase State Machine</span>
        </div>

        <div class="scrubber-bar">
            <div class="step-node" id="node_PREEMPT" onclick="jumpToStage('PREEMPT')">🚑 1. รถพยาบาลแทรกไฟ (Preempt)</div>
            <div class="step-node" id="node_OPT" onclick="jumpToStage('OPT')">🧠 2. Cloud AI ประมวลผล</div>
            <div class="step-node" id="node_C1" onclick="jumpToStage('C1')">🟢 3. ฟื้นฟูรอบ C1 (Peak Shaving)</div>
            <div class="step-node" id="node_C2" onclick="jumpToStage('C2')">🟢 4. ฟื้นฟูรอบ C2 (Balance)</div>
            <div class="step-node" id="node_C3" onclick="jumpToStage('C3')">🟢 5. ฟื้นฟูรอบ C3 (Resync)</div>
            <div class="step-node" id="node_NORMAL" onclick="jumpToStage('NORMAL')">🔄 6. วงจรปกติ 4 เฟส (Normal)</div>
        </div>
    </div>

    <script>
    const CFG = __CONFIG_JSON__;
    const canvas = document.getElementById('simCanvas');
    const ctx = canvas.getContext('2d');

    const plan = CFG.plan || [7, 5, 3];
    const tp = CFG.tp || 6.0;
    const q0 = CFG.q0 || 6.0;
    const qm = CFG.qm || 28.0;
    const qAcc = CFG.q_accumulated;
    const aiCurve = CFG.ai_curve;
    const convCurve = CFG.conv_curve;

    // -----------------------------------------------------------------------
    // 1. สร้างตารางเวลา 4 เฟส ซิงค์ตรงกับโค้ด main.py บน Wokwi 100%
    // -----------------------------------------------------------------------
    function build4PhaseTimeline() {
        const segs = [];
        let t = 0;
        function addSeg(id, group, dur, mStr, mTrn, sStr, sTrn, qStart, qEnd, convS, convE, lcd0, lcd1, desc) {
            segs.push({
                id, group, start: t, end: t + dur, dur,
                lights: { mStr, mTrn, sStr, sTrn },
                qStart, qEnd, convS, convE, lcd0, lcd1, desc
            });
            t += dur;
        }

        // 1. PREEMPT
        addSeg('PREEMPT', 'PREEMPT', tp, 'G', 'R', 'R', 'R', q0, qAcc, q0, qAcc,
               'EMERGENCY WAVE!', 'Main Straight Go',
               `[Phase: PREEMPT] กักไฟเขียวสายหลักทางตรงให้รถพยาบาลผ่าน (${tp.toFixed(1)}s) | ถนนสายรองสะสมแถวคอยเพิ่มเป็น ${qAcc.toFixed(2)} คัน`);

        // 2. AI OPTIMIZING
        const optLcd0 = CFG.used_edge_ai ? 'Edge AI Active!' : 'AI Optimizing...';
        const optLcd1 = CFG.used_edge_ai ? `Plan:[${plan.join(',')}]` : `Q:${Math.round(q0)} Flw:${Math.round(qm)}`;
        addSeg('OPT', 'OPT', 1.5, 'G', 'R', 'R', 'R', qAcc, qAcc, qAcc, qAcc,
               optLcd0, optLcd1,
               `[MQTT Telemetry] ส่งข้อมูลจาก Wokwi ➔ Colab AI คำนวณเวลาไฟเขียวฟื้นฟู 3 รอบ: C1=${plan[0]}s, C2=${plan[1]}s, C3=${plan[2]}s`);

        // 3. MULTI_RECOVERY 3 รอบ (ครบ 4 เฟสต่อรอบตาม Wokwi)
        for (let i = 0; i < 3; i++) {
            const cNum = i + 1;
            const gTime = plan[i];
            const qS = (CFG.cl_active && CFG.actual_q_history.length > i) ? CFG.actual_q_history[i] : aiCurve[i];
            const qE = (CFG.cl_active && CFG.actual_q_history.length > i+1) ? CFG.actual_q_history[i+1] : aiCurve[i+1];
            const cS = convCurve[i];
            const cE = convCurve[i+1];

            if (i > 0 && ((CFG.cl_active && CFG.early_cut && qS === 0) || (!CFG.cl_active && qS <= 0.01 && CFG.early_cut))) {
                addSeg('EARLY_CUT', `C${cNum}`, 1.8, 'G', 'R', 'R', 'R', 0, 0, cS, cE,
                       'ClosedLoop: Q=0!', 'Early Cut->Sync',
                       `⚡ [Closed-Loop Early Cut] เซนเซอร์ HC-SR04 ตรวจพบรถสายรองหมดแล้ว (Q=0) ตัดจบอัตโนมัติและคืนซิงค์ไฟปกติ!`);
                break;
            }

            // เฟส 1: สายรอง วิ่งตรง (AI Plan)
            addSeg(`C${cNum}_S_STR`, `C${cNum}`, gTime, 'R', 'R', 'G', 'R', qS, qE, cS, cE,
                   `Rec C${cNum}/3 Q:{LIVE_Q}`, `Side Str Grn:{SEC}s`,
                   `รอบ C${cNum} (เฟส 1/4 สายรองตรง ${gTime}s): ระบายแถวคอยสะสมจาก ${qS.toFixed(2)} ➔ ${qE.toFixed(2)} คัน`);
            addSeg(`C${cNum}_S_STR_Y`, `C${cNum}`, 1.0, 'R', 'R', 'Y', 'R', qE, qE, cE, cE,
                   `Rec C${cNum}/3 Q:{LIVE_Q}`, `Side Str Yellow `,
                   `รอบ C${cNum}: ไฟเหลืองสายรองทางตรง (เคลียร์รถออกจากกลางแยก)`);

            // เฟส 2: สายรอง เลี้ยวขวา (2s)
            addSeg(`C${cNum}_S_TRN`, `C${cNum}`, 2.0, 'R', 'R', 'R', 'G', qE, qE, cE, cE,
                   `Recovery C${cNum}/3`, `Side Turn Grn..`,
                   `รอบ C${cNum} (เฟส 2/4 สายรองเลี้ยวขวา 2s): รถเลี้ยวขวาจากสายรองทั้ง 2 ฝั่งเลี้ยวขนานกันโดยไม่ตัดหน้า`);
            addSeg(`C${cNum}_S_TRN_Y`, `C${cNum}`, 1.0, 'R', 'R', 'R', 'Y', qE, qE, cE, cE,
                   `Recovery C${cNum}/3`, `Side Turn Ylw..`,
                   `รอบ C${cNum}: ไฟเหลืองเลี้ยวขวาสายรอง`);

            // เฟส 3: สายหลัก วิ่งตรง (3s)
            addSeg(`C${cNum}_M_STR`, `C${cNum}`, 3.0, 'G', 'R', 'R', 'R', qE, qE, cE, cE,
                   `Recovery C${cNum}/3`, `Main Str Grn..`,
                   `รอบ C${cNum} (เฟส 3/4 สายหลักตรง 3s): คืนไฟเขียวให้สายหลัก (${qm.toFixed(0)} คัน/นาที) ป้องกันรถติดสะสม`);
            addSeg(`C${cNum}_M_STR_Y`, `C${cNum}`, 1.0, 'Y', 'R', 'R', 'R', qE, qE, cE, cE,
                   `Recovery C${cNum}/3`, `Main Str Ylw..`,
                   `รอบ C${cNum}: ไฟเหลืองสายหลักทางตรง (เคลียร์สี่แยก)`);

            // เฟส 4: สายหลัก เลี้ยวขวา (2s)
            addSeg(`C${cNum}_M_TRN`, `C${cNum}`, 2.0, 'R', 'G', 'R', 'R', qE, qE, cE, cE,
                   `Recovery C${cNum}/3`, `Main Turn Grn..`,
                   `รอบ C${cNum} (เฟส 4/4 สายหลักเลี้ยวขวา 2s): เปิดไฟเขียวลูกศรเลี้ยวขวาสายหลักเข้าสู่ถนนสายรอง`);
            addSeg(`C${cNum}_M_TRN_Y`, `C${cNum}`, 1.0, 'R', 'Y', 'R', 'R', qE, qE, cE, cE,
                   `Recovery C${cNum}/3`, `Main Turn Ylw..`,
                   `รอบ C${cNum}: ไฟเหลืองเลี้ยวขวาสายหลัก`);
        }

        // 4. EQUILIBRIUM DONE
        const finalQ = (CFG.cl_active && CFG.actual_q_history.length > 0)
                       ? CFG.actual_q_history[CFG.actual_q_history.length - 1]
                       : aiCurve[3];
        addSeg('DONE', 'NORMAL', 1.2, 'G', 'R', 'R', 'R', finalQ, finalQ, convCurve[3], convCurve[3],
               'Equilibrium Done', 'Restoring Sync',
               `✅ ฟื้นฟูสมดุลครบ 4 เฟสสำเร็จ! ลดความล่าช้าสะสมได้ ${CFG.pct_saved}% กลับสู่วงจรปกติ`);

        return { segs, totalDuration: t };
    }

    const TIMELINE = build4PhaseTimeline();
    const RECOVERY_START_TIME = tp + 1.5;

    const storageKey = `traffic_4p_v3_seq_${CFG.event_seq}`;
    let savedState = null;
    try {
        savedState = JSON.parse(sessionStorage.getItem(storageKey));
    } catch (e) {}

    let simMode = savedState ? savedState.mode : (CFG.has_event ? 'LIVE' : 'NORMAL_LOOP');
    let startEpochMs = savedState ? savedState.startEpochMs : (Date.now() - (RECOVERY_START_TIME * 1000));
    let paused = false;
    let pausedSimSec = 0;

    function saveSimState() {
        try {
            sessionStorage.setItem(storageKey, JSON.stringify({
                mode: simMode,
                startEpochMs: startEpochMs
            }));
        } catch (e) {}
    }

    // -----------------------------------------------------------------------
    // 2. ระบบฟิสิกส์รถยนต์ 8 เลน (ห้ามจอดค้างกลางแยก + ห้ามซ้อนคัน + ห้ามชนตอนเลี้ยว)
    // -----------------------------------------------------------------------
    // พิกัดถนนบน Canvas (1180 x 410):
    // ถนนสายหลัก (แนวนอน): rMainY = 133, rMainH = 144 (y: 133..277, กึ่งกลาง midY = 205)
    //   - เลน M1 (ซ้าย->ขวา วิ่งตรง): y = 151
    //   - เลน M2 (ซ้าย->ขวา เลี้ยวขวาลงล่าง): y = 187
    //   - เลน M3 (ขวา->ซ้าย เลี้ยวขวาขึ้นบน): y = 223
    //   - เลน M4 (ขวา->ซ้าย วิ่งตรง): y = 259
    // ถนนสายรอง (แนวตั้ง): rSideX = 440, rSideW = 144 (x: 440..584, กึ่งกลาง midX = 512)
    //   - เลน S1 (ล่าง->บน วิ่งตรง - เซนเซอร์ HC-SR04): x = 458
    //   - เลน S2 (ล่าง->บน เลี้ยวขวาไปทางขวา): x = 494
    //   - เลน S3 (บน->ล่าง เลี้ยวขวาไปทางซ้าย): x = 530
    //   - เลน S4 (บน->ล่าง วิ่งตรง): x = 566

    const rMainY = 133, rMainH = 144, midY = 205;
    const rSideX = 440, rSideW = 144, midX = 512;

    const stopWestX = rSideX - 38;          // 402
    const stopEastX = rSideX + rSideW + 38; // 622
    const stopSouthY = rMainY + rMainH + 34;// 311
    const stopNorthY = rMainY - 34;         // 99
    const MIN_GAP = 54;

    // รถทางตรงสายหลัก (เริ่มต้นนอกเขตสี่แยกทั้งหมด ไม่ให้มีรถค้างกลางแยก)
    let eastStrCars = [
        { pos: 380, c: '#38BDF8' },
        { pos: 290, c: '#F59E0B' },
        { pos: 180, c: '#10B981' },
        { pos: 70,  c: '#A855F7' }
    ];
    let westStrCars = [
        { pos: 645, c: '#F43F5E' },
        { pos: 750, c: '#38BDF8' },
        { pos: 870, c: '#FBBF24' },
        { pos: 990, c: '#818CF8' }
    ];

    // รถทางตรงสายรองฝั่งบน->ล่าง (Southbound Straight S4: x = 566)
    let southStrCars = [
        { pos: 88,  c: '#A855F7' },
        { pos: 30,  c: '#38BDF8' }
    ];

    // รถทางตรงสายรองฝั่งล่าง->บน (Northbound Straight S1: x = 458 - ซิงค์กับจำนวนคิว liveQ)
    let northStrCars = [
        { pos: 315, c: '#10B981' },
        { pos: 369, c: '#F59E0B' },
        { pos: 423, c: '#F43F5E' },
        { pos: 477, c: '#38BDF8' }
    ];

    // ฟังก์ชันเคลียร์รถออกจากกรอบสี่แยกเมื่อกดปุ่มเปลี่ยนโหมด/ข้ามเฟส
    function clearIntersectionBox() {
        eastStrCars = [
            { pos: stopWestX - 8,   c: '#38BDF8' },
            { pos: stopWestX - 66,  c: '#F59E0B' },
            { pos: stopWestX - 128, c: '#10B981' },
            { pos: stopWestX - 190, c: '#A855F7' }
        ];
        westStrCars = [
            { pos: stopEastX + 8,   c: '#F43F5E' },
            { pos: stopEastX + 66,  c: '#38BDF8' },
            { pos: stopEastX + 128, c: '#FBBF24' },
            { pos: stopEastX + 190, c: '#818CF8' }
        ];
        southStrCars = [
            { pos: stopNorthY - 6,  c: '#A855F7' },
            { pos: stopNorthY - 60, c: '#38BDF8' }
        ];
        northStrCars = [
            { pos: stopSouthY + 4,  c: '#10B981' },
            { pos: stopSouthY + 58, c: '#F59E0B' },
            { pos: stopSouthY + 112, c: '#F43F5E' },
            { pos: stopSouthY + 166, c: '#38BDF8' }
        ];
    }

    function startLiveSync() {
        paused = false;
        clearIntersectionBox();
        if (!CFG.has_event) {
            simMode = 'NORMAL_LOOP';
        } else {
            simMode = 'LIVE';
            startEpochMs = Date.now() - (RECOVERY_START_TIME * 1000);
        }
        saveSimState();
    }

    function startFullReplay() {
        paused = false;
        clearIntersectionBox();
        simMode = 'REPLAY';
        startEpochMs = Date.now();
        saveSimState();
    }

    function togglePause() {
        if (!paused) {
            paused = true;
            pausedSimSec = (Date.now() - startEpochMs) / 1000.0;
        } else {
            paused = false;
            startEpochMs = Date.now() - (pausedSimSec * 1000.0);
        }
    }

    function jumpToStage(groupName) {
        paused = false;
        clearIntersectionBox();
        if (groupName === 'NORMAL') {
            simMode = 'NORMAL_LOOP';
            saveSimState();
            return;
        }
        simMode = 'REPLAY';
        const target = TIMELINE.segs.find(s => s.group === groupName);
        if (target) {
            startEpochMs = Date.now() - (target.start * 1000.0);
            saveSimState();
        }
    }

    function getActiveState(elapsedSec) {
        if (simMode === 'NORMAL_LOOP' || elapsedSec >= TIMELINE.totalDuration) {
            // วงจรปกติ 4 เฟสตาม Wokwi (12.0s ต่อรอบ)
            const c = elapsedSec % 12.0;
            let lights = { mStr: 'R', mTrn: 'R', sStr: 'R', sTrn: 'R' };
            let lcd1 = 'Main Str (1/4)';
            let secLeft = 1;
            let subDesc = 'เฟส 1/4: ไฟเขียวสายหลักวิ่งตรง (Main Straight)';

            if (c < 3.0) {
                lights.mStr = 'G'; lcd1 = 'Main Str (1/4)'; secLeft = Math.ceil(3.0 - c);
                subDesc = 'เฟส 1/4: ไฟเขียวสายหลักวิ่งตรง (Main Straight)';
            } else if (c < 4.0) {
                lights.mStr = 'Y'; lcd1 = 'Main Str (1/4)'; secLeft = 1;
                subDesc = 'เฟส 1/4: ไฟเหลืองสายหลักวิ่งตรง (เคลียร์สี่แยก)';
            } else if (c < 5.5) {
                lights.mTrn = 'G'; lcd1 = 'Main Trn (2/4)'; secLeft = Math.ceil(5.5 - c);
                subDesc = 'เฟส 2/4: ไฟเขียวลูกศรเลี้ยวขวาสายหลัก (เลี้ยวขนานไร้จุดตัด)';
            } else if (c < 6.5) {
                lights.mTrn = 'Y'; lcd1 = 'Main Trn (2/4)'; secLeft = 1;
                subDesc = 'เฟส 2/4: ไฟเหลืองเลี้ยวขวาสายหลัก';
            } else if (c < 8.5) {
                lights.sStr = 'G'; lcd1 = 'Side Str (3/4)'; secLeft = Math.ceil(8.5 - c);
                subDesc = 'เฟส 3/4: ไฟเขียวสายรองวิ่งตรง (Side Straight)';
            } else if (c < 9.5) {
                lights.sStr = 'Y'; lcd1 = 'Side Str (3/4)'; secLeft = 1;
                subDesc = 'เฟส 3/4: ไฟเหลืองสายรองวิ่งตรง (เคลียร์สี่แยก)';
            } else if (c < 11.0) {
                lights.sTrn = 'G'; lcd1 = 'Side Trn (4/4)'; secLeft = Math.ceil(11.0 - c);
                subDesc = 'เฟส 4/4: ไฟเขียวลูกศรเลี้ยวขวาสายรอง (เลี้ยวขนานไร้จุดตัด)';
            } else {
                lights.sTrn = 'Y'; lcd1 = 'Side Trn (4/4)'; secLeft = 1;
                subDesc = 'เฟส 4/4: ไฟเหลืองเลี้ยวขวาสายรอง';
            }

            const endQ = (CFG.cl_active && CFG.actual_q_history.length > 0)
                         ? CFG.actual_q_history[CFG.actual_q_history.length - 1]
                         : (aiCurve[3] || 2.0);

            return {
                id: 'NORMAL', group: 'NORMAL',
                lights,
                liveQ: Math.max(1.5, endQ),
                convQ: convCurve[3] || 8.0,
                secLeft,
                lcd0: 'State: NORMAL',
                lcd1,
                desc: `วงจรปกติ 4 เฟสไร้จุดตัด (${subDesc})`,
                ratio: 1.0
            };
        }

        const seg = TIMELINE.segs.find(s => elapsedSec >= s.start && elapsedSec < s.end) || TIMELINE.segs[TIMELINE.segs.length - 1];
        const localT = elapsedSec - seg.start;
        const ratio = Math.min(1.0, Math.max(0.0, localT / seg.dur));
        const liveQ = seg.qStart + (seg.qEnd - seg.qStart) * ratio;
        const convQ = seg.convS + (seg.convE - seg.convS) * ratio;
        const secLeft = Math.max(1, Math.ceil(seg.dur - localT));

        const lcd0 = seg.lcd0.replace('{LIVE_Q}', String(Math.round(liveQ)).padStart(2, ' '));
        const lcd1 = seg.lcd1.replace('{SEC}', String(secLeft).padStart(2, ' '));

        return {
            id: seg.id,
            group: seg.group,
            lights: seg.lights,
            liveQ,
            convQ,
            secLeft,
            lcd0,
            lcd1,
            desc: seg.desc,
            ratio
        };
    }

    // -----------------------------------------------------------------------
    // ฟังก์ชันอัปเดตคิวรถทางตรงแบบ Strict Stop-Line & Fast Intersection Clearing
    // -----------------------------------------------------------------------
    function update1DLane(cars, dir, lightState, stopPos, baseSpeed, minBound, maxBound) {
        const isGreen = (lightState === 'G');
        if (dir === 1) {
            // วิ่งไปทางค่าบวก (ซ้าย->ขวา หรือ บน->ล่าง)
            cars.sort((a, b) => b.pos - a.pos); // คันหน้าสุดอยู่ index 0
            for (let i = 0; i < cars.length; i++) {
                // ถ้ารถผ่านเส้นหยุดเข้ากลางแยกไปแล้ว ให้เร่งความเร็วเคล
