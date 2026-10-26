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

# 2. ตั้งค่าหน้าเว็บแบบ Wide Screen (ซ่อน Sidebar แบบเดิมเพื่อใช้ Top Command Bar สมัยใหม่)
st.set_page_config(
    page_title="AERO-TRAFFIC OS | 4-Phase AIoT Intersection Control",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 3. รีเฟรชอัตโนมัติทุก 1 วินาที
st_autorefresh(interval=1000, limit=None, key="mobility_os_pulse")

# 4. ตกแต่ง UX/UI ใหม่ทั้งหมดด้วยธีม Carbon Obsidian & Amber/Emerald (ใช้ฟอนต์ IBM Plex Sans Thai + Plus Jakarta Sans)
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
            radial-gradient(at 0% 0%, rgba(245, 158, 11, 0.06) 0px, transparent 45%),
            radial-gradient(at 100% 0%, rgba(99, 102, 241, 0.07) 0px, transparent 45%);
        color: var(--text-primary);
        font-family: 'Plus Jakarta Sans', 'IBM Plex Sans Thai', sans-serif;
    }

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', 'IBM Plex Sans Thai', sans-serif !important;
    }

    .block-container {
        padding-top: 1.4rem !important;
        padding-bottom: 2rem !important;
        max-width: 1440px !important;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    /* Top Command Bar */
    .os-navbar {
        background: rgba(18, 20, 29, 0.88);
        backdrop-filter: blur(16px);
        border: 1px solid var(--border-subtle);
        border-radius: 18px;
        padding: 18px 26px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
        margin-bottom: 18px;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
    }

    .os-brand {
        display: flex;
        align-items: center;
        gap: 16px;
    }

    .os-logo-badge {
        width: 48px;
        height: 48px;
        border-radius: 14px;
        background: linear-gradient(135deg, #F59E0B 0%, #EA580C 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        box-shadow: 0 0 20px rgba(245, 158, 11, 0.35);
    }

    .os-title-group h1 {
        font-size: 1.35rem;
        font-weight: 700;
        color: #FFFFFF;
        margin: 0;
        letter-spacing: -0.02em;
    }

    .os-title-group p {
        font-size: 0.84rem;
        color: var(--text-muted);
        margin: 3px 0 0 0;
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
        padding: 8px 14px;
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.8rem;
        font-weight: 500;
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
        font-size: 1.05rem;
        font-weight: 700;
        color: #F59E0B;
        background: rgba(245, 158, 11, 0.1);
        border: 1px solid rgba(245, 158, 11, 0.35);
        padding: 8px 16px;
        border-radius: 12px;
    }

    /* Bento KPI Cards */
    .bento-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 14px;
        margin: 16px 0 20px 0;
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
        padding: 16px 18px;
        margin-bottom: 14px;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 5. ระบบจัดการ MQTT เบื้องหลัง (Singleton Background Worker)
# ---------------------------------------------------------------------------
@st.cache_resource
def init_mqtt_store():
    store = {
        "connected": False,
        "ai_data": None,
        "closed_loop_data": None,
        "event_log": [],
        "event_seq": 0
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
                store["event_seq"] += 1
                current_th_time = datetime.now(TH_TIMEZONE).strftime("%H:%M:%S")
                store["event_log"].insert(0, {
                    "เวลา (UTC+7)": current_th_time,
                    "กักไฟ (s)": payload["tp"],
                    "คิวสะสม (คัน)": payload["physics"]["q_accumulated"],
                    "แผน AI 4-Phase (C1,C2,C3)": f"{payload['plan'][0]}s / {payload['plan'][1]}s / {payload['plan'][2]}s",
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
# 6. ฟังก์ชันสร้าง HTML5 Canvas Animation (4-Phase Intersection + Bezier Turning)
# ---------------------------------------------------------------------------
def build_4phase_animation_html(ai_data, cl_data, event_seq):
    tp_val = float(ai_data["tp"]) if ai_data else 6.0
    q0_val = float(ai_data["q0"]) if ai_data else 6.0
    qm_val = float(ai_data["qm"]) if ai_data else 28.0
    plan_val = ai_data["plan"] if ai_data else [7, 5, 3]

    # คำนวณฟิสิกส์สำรองตรงตามสมการใน Google Colab 100%
    q_acc_default = round(q0_val + (0.25 * tp_val), 2)
    c1_default = round(max(0.0, q_acc_default - (plan_val[0] * 0.65)), 2)
    c2_default = round(max(0.0, c1_default - (plan_val[1] * 0.65)), 2)
    c3_default = round(max(0.0, c2_default - (plan_val[2] * 0.65)), 2)

    conv1_default = round(max(0.0, q_acc_default - (2.0 * 0.65) + (0.25 * 3.0)), 2)
    conv2_default = round(max(0.0, conv1_default - (2.0 * 0.65) + (0.25 * 3.0)), 2)
    conv3_default = round(max(0.0, conv2_default - (2.0 * 0.65) + (0.25 * 3.0)), 2)

    sim_config = {
        "has_event": ai_data is not None,
        "event_seq": event_seq,
        "tp": tp_val,
        "q0": q0_val,
        "qm": qm_val,
        "sensor_fault": bool(ai_data.get("sensor_fault", False)) if ai_data else False,
        "plan": plan_val,
        "r2_score": float(ai_data.get("r2_score", 0.9629)) if ai_data else 0.9629,
        "q_accumulated": float(ai_data["physics"]["q_accumulated"]) if ai_data else q_acc_default,
        "ai_curve": ai_data["physics"]["ai_curve"] if ai_data else [q_acc_default, c1_default, c2_default, c3_default],
        "conv_curve": ai_data["physics"]["conv_curve"] if ai_data else [q_acc_default, conv1_default, conv2_default, conv3_default],
        "pct_saved": float(ai_data["physics"]["pct_saved"]) if ai_data else 71.2,
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
            margin-bottom: 12px;
            padding-bottom: 10px;
            border-bottom: 1px solid #222636;
        }
        .cockpit-title {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 0.98rem;
            font-weight: 700;
            color: #F8FAFC;
        }
        .phase-tag {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.76rem;
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
            height: 460px;
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
        .scrubber-bar {
            margin-top: 12px;
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 8px;
        }
        .step-node {
            text-align: center;
            padding: 8px 6px;
            border-radius: 10px;
            background: #171A26;
            border: 1px solid #262B3D;
            color: #94A3B8;
            font-size: 0.75rem;
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
            background: rgba(16, 185, 129, 0.16);
            border: 1.5px solid #10B981;
            color: #FFFFFF;
            box-shadow: 0 0 14px rgba(16, 185, 129, 0.28);
        }
        .step-node.active-emg {
            background: rgba(244, 63, 94, 0.2);
            border: 1.5px solid #F43F5E;
            color: #FFFFFF;
            box-shadow: 0 0 14px rgba(244, 63, 94, 0.35);
        }
        .step-node.active-norm {
            background: rgba(245, 158, 11, 0.18);
            border: 1.5px solid #F59E0B;
            color: #FFFFFF;
        }
    </style>
    </head>
    <body>
    <div class="cockpit-shell">
        <div class="cockpit-header">
            <div class="cockpit-title">
                <span>⚡ 4-PHASE SMART INTERSECTION DIGITAL TWIN (ทางตรง + เลี้ยวขวาอิสระ 12 LEDs)</span>
                <span id="phaseBadge" class="phase-tag">INITIALIZING...</span>
            </div>
            <div class="ctrl-group">
                <button class="ctrl-btn" onclick="startLiveSync()">📡 ซิงค์เวลาจริงกับ Wokwi</button>
                <button class="ctrl-btn" onclick="startFullReplay()">🎬 เล่นซ้ำตั้งแต่รถพยาบาลแทรกไฟ</button>
                <button class="ctrl-btn" onclick="togglePause()">⏯️ หยุด / เล่นต่อ</button>
            </div>
        </div>

        <div class="viewport-frame">
            <canvas id="simCanvas" width="1180" height="460"></canvas>
        </div>

        <div class="scrubber-bar">
            <div class="step-node" id="node_PREEMPT" onclick="jumpToStage('PREEMPT')">🚑 1. Preempt (กักไฟรถฉุกเฉิน)</div>
            <div class="step-node" id="node_OPT" onclick="jumpToStage('OPT')">🧠 2. Cloud AI ประมวลผล</div>
            <div class="step-node" id="node_C1" onclick="jumpToStage('C1')">🟢 3. รอบ C1 (4-Phase Peak)</div>
            <div class="step-node" id="node_C2" onclick="jumpToStage('C2')">🟢 4. รอบ C2 (4-Phase Balance)</div>
            <div class="step-node" id="node_C3" onclick="jumpToStage('C3')">🟢 5. รอบ C3 (4-Phase Resync)</div>
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
    // สร้างตารางเวลา 4 เฟส ให้ตรงกับโค้ด main.py บน Wokwi ทุกวินาที!
    // ไฟ 4 ชุด: mStr (สายหลักตรง), mTrn (สายหลักเลี้ยวขวา), sStr (สายรองตรง), sTrn (สายรองเลี้ยวขวา)
    // ค่าสี: 'R' = แดง, 'Y' = เหลือง, 'G' = เขียว
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

        // 1. PREEMPT: เปิดไฟเขียวเฉพาะสายหลักทางตรง (G, R, R, R) ให้รถพยาบาลวิ่งผ่าน 6 วินาที
        addSeg('PREEMPT', 'PREEMPT', tp, 'G', 'R', 'R', 'R', q0, qAcc, q0, qAcc,
               'EMERGENCY WAVE!', 'Main Straight Go',
               `[Phase: PREEMPT] เปิดไฟเขียวสายหลักทางตรงให้รถพยาบาล (${tp.toFixed(1)}s) | ถนนรองสะสมรถเพิ่ม Q = ${q0} + 0.25×${tp.toFixed(1)} = ${qAcc.toFixed(2)} คัน`);

        // 2. AI OPTIMIZING (1.5s)
        const optLcd0 = CFG.used_edge_ai ? 'Edge AI Active!' : 'AI Optimizing...';
        const optLcd1 = CFG.used_edge_ai ? `Plan:[${plan.join(',')}]` : `Q:${Math.round(q0)} Flw:${Math.round(qm)}`;
        addSeg('OPT', 'OPT', 1.5, 'G', 'R', 'R', 'R', qAcc, qAcc, qAcc, qAcc,
               optLcd0, optLcd1,
               `[MQTT -> Cloud AI] โมเดล Multi-Output RF คำนวณแผนฟื้นฟู 3 รอบ: C1=${plan[0]}s, C2=${plan[1]}s, C3=${plan[2]}s`);

        // 3. MULTI_RECOVERY 3 รอบ (แต่ละรอบทำงานครบ 4 เฟสตาม Wokwi: Side Str -> Side Turn -> Main Str -> Main Turn)
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
                       `⚡ [Closed-Loop Early Cut] เซนเซอร์ HC-SR04 ตรวจพบคิวรถถนนรองหมดแล้ว (Q=0) ตัดจบและคืนซิงค์ไฟทันที!`);
                break;
            }

            // เฟสย่อยที่ 1: สายรอง วิ่งตรง (R, R, G, R) ตามเวลา AI Plan
            addSeg(`C${cNum}_S_STR`, `C${cNum}`, gTime, 'R', 'R', 'G', 'R', qS, qE, cS, cE,
                   `Rec C${cNum}/3 Q:{LIVE_Q}`, `Side Str Grn:{SEC}s`,
                   `รอบ C${cNum} [เฟส 1/4 สายรองตรง ${gTime}s]: ระบายแถวคอยหลักจาก ${qS.toFixed(2)} ➔ ${qE.toFixed(2)} คัน (ไม่มีรถเลี้ยวตัดหน้า)`);
            addSeg(`C${cNum}_S_STR_Y`, `C${cNum}`, 1.0, 'R', 'R', 'Y', 'R', qE, qE, cE, cE,
                   `Rec C${cNum}/3 Q:{LIVE_Q}`, `Side Str Yellow `,
                   `รอบ C${cNum} [ไฟเหลืองสายรองทางตรง 1s]`);

            // เฟสย่อยที่ 2: สายรอง เลี้ยวขวา (R, R, R, G) 2 วินาที + เหลือง 1 วินาที
            addSeg(`C${cNum}_S_TRN`, `C${cNum}`, 2.0, 'R', 'R', 'R', 'G', qE, qE, cE, cE,
                   `Recovery C${cNum}/3`, `Side Turn Grn..`,
                   `รอบ C${cNum} [เฟส 2/4 สายรองเลี้ยวขวา 2s]: เปิดไฟเขียวลูกศรเลี้ยวขวาถนนสายรองอย่างปลอดภัย`);
            addSeg(`C${cNum}_S_TRN_Y`, `C${cNum}`, 1.0, 'R', 'R', 'R', 'Y', qE, qE, cE, cE,
                   `Recovery C${cNum}/3`, `Side Turn Ylw..`,
                   `รอบ C${cNum} [ไฟเหลืองลูกศรเลี้ยวขวาสายรอง 1s]`);

            // เฟสย่อยที่ 3: สายหลัก วิ่งตรง (G, R, R, R) 3 วินาที + เหลือง 1 วินาที
            addSeg(`C${cNum}_M_STR`, `C${cNum}`, 3.0, 'G', 'R', 'R', 'R', qE, qE, cE, cE,
                   `Recovery C${cNum}/3`, `Main Str Grn..`,
                   `รอบ C${cNum} [เฟส 3/4 สายหลักตรง 3s]: ระบายรถสายหลักทางตรง (${qm.toFixed(0)} คัน/นาที) ป้องกัน Shockwave`);
            addSeg(`C${cNum}_M_STR_Y`, `C${cNum}`, 1.0, 'Y', 'R', 'R', 'R', qE, qE, cE, cE,
                   `Recovery C${cNum}/3`, `Main Str Ylw..`,
                   `รอบ C${cNum} [ไฟเหลืองสายหลักทางตรง 1s]`);

            // เฟสย่อยที่ 4: สายหลัก เลี้ยวขวา (R, G, R, R) 2 วินาที + เหลือง 1 วินาที
            addSeg(`C${cNum}_M_TRN`, `C${cNum}`, 2.0, 'R', 'G', 'R', 'R', qE, qE, cE, cE,
                   `Recovery C${cNum}/3`, `Main Turn Grn..`,
                   `รอบ C${cNum} [เฟส 4/4 สายหลักเลี้ยวขวา 2s]: เปิดไฟเขียวลูกศรเลี้ยวขวาสายหลักเข้าสู่ถนนรอง`);
            addSeg(`C${cNum}_M_TRN_Y`, `C${cNum}`, 1.0, 'R', 'Y', 'R', 'R', qE, qE, cE, cE,
                   `Recovery C${cNum}/3`, `Main Turn Ylw..`,
                   `รอบ C${cNum} [ไฟเหลืองลูกศรเลี้ยวขวาสายหลัก 1s]`);
        }

        // 4. EQUILIBRIUM DONE
        const finalQ = (CFG.cl_active && CFG.actual_q_history.length > 0)
                       ? CFG.actual_q_history[CFG.actual_q_history.length - 1]
                       : aiCurve[3];
        addSeg('DONE', 'NORMAL', 1.2, 'G', 'R', 'R', 'R', finalQ, finalQ, convCurve[3], convCurve[3],
               'Equilibrium Done', 'Restoring Sync',
               `✅ ฟื้นฟูครบ 4 เฟสสำเร็จ! ลดความล่าช้าได้ ${CFG.pct_saved}% คืนสู่วงจรไฟ 4 เฟสปกติ`);

        return { segs, totalDuration: t };
    }

    const TIMELINE = build4PhaseTimeline();
    const RECOVERY_START_TIME = tp + 1.5;

    const storageKey = `aero_4phase_seq_${CFG.event_seq}`;
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

    function startLiveSync() {
        paused = false;
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

    // ึงเฟสปัจจุบัน (รวมถึงวงจร NORMAL 4 เฟส: Main Str -> Main Trn -> Side Str -> Side Trn รวม 12 วินาที)
    function getActiveState(elapsedSec) {
        if (simMode === 'NORMAL_LOOP' || elapsedSec >= TIMELINE.totalDuration) {
            // วงจรปกติ 4 เฟสตามโค้ด Wokwi:
            // 1) Main Str: เขียว 3.0s, เหลือง 1.0s (0.0 - 4.0)
            // 2) Main Trn: เขียว 1.5s, เหลือง 1.0s (4.0 - 6.5)
            // 3) Side Str: เขียว 2.0s, เหลือง 1.0s (6.5 - 9.5)
            // 4) Side Trn: เขียว 1.5s, เหลือง 1.0s (9.5 - 12.0)
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
                subDesc = 'เฟส 1/4: ไฟเหลืองสายหลักวิ่งตรง';
            } else if (c < 5.5) {
                lights.mTrn = 'G'; lcd1 = 'Main Trn (2/4)'; secLeft = Math.ceil(5.5 - c);
                subDesc = 'เฟส 2/4: ไฟเขียวลูกศรเลี้ยวขวาสายหลัก (Main Right-Turn)';
            } else if (c < 6.5) {
                lights.mTrn = 'Y'; lcd1 = 'Main Trn (2/4)'; secLeft = 1;
                subDesc = 'เฟส 2/4: ไฟเหลืองเลี้ยวขวาสายหลัก';
            } else if (c < 8.5) {
                lights.sStr = 'G'; lcd1 = 'Side Str (3/4)'; secLeft = Math.ceil(8.5 - c);
                subDesc = 'เฟส 3/4: ไฟเขียวสายรองวิ่งตรง (Side Straight)';
            } else if (c < 9.5) {
                lights.sStr = 'Y'; lcd1 = 'Side Str (3/4)'; secLeft = 1;
                subDesc = 'เฟส 3/4: ไฟเหลืองสายรองวิ่งตรง';
            } else if (c < 11.0) {
                lights.sTrn = 'G'; lcd1 = 'Side Trn (4/4)'; secLeft = Math.ceil(11.0 - c);
                subDesc = 'เฟส 4/4: ไฟเขียวลูกศรเลี้ยวขวาสายรอง (Side Right-Turn)';
            } else {
                lights.sTrn = 'Y'; lcd1 = 'Side Trn (4/4)'; secLeft = 1;
                subDesc = 'เฟส 4/4: ไฟเหลืองเลี้ยวขวาสายรอง';
            }

            const endQ = (CFG.cl_active && CFG.actual_q_history.length > 0)
                         ? CFG.actual_q_history[CFG.actual_q_history.length - 1]
                         : (aiCurve[3] || 0);

            return {
                id: 'NORMAL', group: 'NORMAL',
                lights,
                liveQ: endQ,
                convQ: convCurve[3] || 0,
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
    // ระบบจัดการรถยนต์ทั้งทางตรง (Straight Lanes) และรถเลี้ยวโค้ง (Bezier Turn)
    // -----------------------------------------------------------------------
    // พิกัดกึ่งกลางสี่แยก: cx = 490, cy = 225
    // ถนนสายหลัก (แนวนอน): y = 145 ถึง 305 (ความกว้าง 160px แบ่ง 4 เลนย่อย เลนละ 40px)
    //   - เลน 1 (y=155): ซ้าย->ขวา วิ่งตรง (East Straight)
    //   - เลน 2 (y=195): ซ้าย->ขวา เลี้ยวขวาลงล่าง (East -> South Turn)
    //   - เลน 3 (y=235): ขวา->ซ้าย เลี้ยวขวาขึ้นบน (West -> North Turn)
    //   - เลน 4 (y=275): ขวา->ซ้าย วิ่งตรง (West Straight)
    // ถนนสายรอง (แนวตั้ง): x = 410 ถึง 570 (ความกว้าง 160px แบ่ง 4 เลนย่อย เลนละ 40px)
    //   - เลน 1 (x=420): ล่าง->บน วิ่งตรง (North Straight - เซนเซอร์ HC-SR04 จับเลนนี้)
    //   - เลน 2 (x=460): ล่าง->บน เลี้ยวขวาไปทางขวา (North -> East Turn)
    //   - เลน 3 (x=500): บน->ล่าง เลี้ยวขวาไปทางซ้าย (South -> West Turn)
    //   - เลน 4 (x=540): บน->ล่าง วิ่งตรง (South Straight)

    const eastStrCars = [ {x: 80, c: '#38BDF8'}, {x: 240, c: '#F59E0B'}, {x: 720, c: '#10B981'}, {x: 980, c: '#A855F7'} ];
    const westStrCars = [ {x: 1060, c: '#F43F5E'}, {x: 840, c: '#38BDF8'}, {x: 310, c: '#FBBF24'}, {x: 90, c: '#818CF8'} ];

    function updateStraightLane(cars, dir, canGo, stopX, speed) {
        const GAP = 68;
        if (dir === 1) {
            cars.sort((a, b) => b.x - a.x);
            for (let i = 0; i < cars.length; i++) {
                let nx = cars[i].x + speed;
                if (!canGo && cars[i].x <= stopX && nx > stopX) nx = stopX;
                if (i > 0 && cars[i-1].x > cars[i].x && (cars[i-1].x - nx) < GAP) {
                    nx = cars[i-1].x - GAP;
                }
                cars[i].x = nx;
            }
            cars.forEach(car => {
                if (car.x > canvas.width + 60) {
                    const minX = Math.min(...cars.map(it => it.x));
                    car.x = Math.min(-60, minX - GAP - 25);
                }
            });
        } else {
            cars.sort((a, b) => a.x - b.x);
            for (let i = 0; i < cars.length; i++) {
                let nx = cars[i].x - speed;
                if (!canGo && cars[i].x >= stopX && nx < stopX) nx = stopX;
                if (i > 0 && cars[i-1].x < cars[i].x && (nx - cars[i-1].x) < GAP) {
                    nx = cars[i-1].x + GAP;
                }
                cars[i].x = nx;
            }
            cars.forEach(car => {
                if (car.x < -60) {
                    const maxX = Math.max(...cars.map(it => it.x));
                    car.x = Math.max(canvas.width + 60, maxX + GAP + 25);
                }
            });
        }
    }

    // ฟังก์ชันคำนวณจุดและมุมหมุนบนเส้นโค้ง Quadratic Bezier สำหรับรถเลี้ยว
    function getBezierPointAndAngle(t, p0, p1, p2) {
        const inv = 1 - t;
        const x = inv*inv*p0.x + 2*inv*t*p1.x + t*t*p2.x;
        const y = inv*inv*p0.y + 2*inv*t*p1.y + t*t*p2.y;
        const dx = 2*inv*(p1.x - p0.x) + 2*t*(p2.x - p1.x);
        const dy = 2*inv*(p1.y - p0.y) + 2*t*(p2.y - p1.y);
        return { x, y, angle: Math.atan2(dy, dx) };
    }

    function drawRoundBox(x, y, w, h, r, fill, stroke, lw=1.5) {
        ctx.beginPath();
        ctx.roundRect(x, y, w, h, r);
        if (fill) { ctx.fillStyle = fill; ctx.fill(); }
        if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lw; ctx.stroke(); }
    }

    // วาดรถยนต์ด้วยมุมหมุนอิสระ (angle เป็นเรเดียน: 0=ขวา, PI=ซ้าย, -PI/2=ขึ้นบน, PI/2=ลงล่าง)
    function drawCarRotated(cx, cy, angle, color, isAmbulance=false) {
        const w = isAmbulance ? 44 : 34;
        const h = isAmbulance ? 22 : 18;
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(angle);
        drawRoundBox(-w/2, -h/2, w, h, 4, color, '#090A0F', 1.5);
        // กระจกหน้าและหลัง
        ctx.fillStyle = '#1E293B';
        ctx.fillRect(w*0.12, -h/2 + 2.5, w*0.24, h - 5);
        ctx.fillRect(-w*0.36, -h/2 + 2.5, w*0.18, h - 5);

        if (isAmbulance) {
            ctx.fillStyle = '#EF4444';
            ctx.fillRect(-6, -h*0.28, 4, h*0.56);
            ctx.fillRect(-10, -2, 12, 4);
            const flash = Math.floor(Date.now() / 110) % 2 === 0;
            ctx.beginPath(); ctx.arc(w*0.28, -4, 3.2, 0, Math.PI*2);
            ctx.fillStyle = flash ? '#EF4444' : '#3B82F6'; ctx.fill();
            ctx.beginPath(); ctx.arc(w*0.28, 4, 3.2, 0, Math.PI*2);
            ctx.fillStyle = flash ? '#3B82F6' : '#EF4444'; ctx.fill();
        }
        ctx.restore();
    }

    // วาดเสาไฟจราจรแบบ Dual-Head 6 ดวง (ซ้าย: ทางตรง ● | ขวา: เลี้ยวขวา ➔)
    function drawDualSignalHead(x, y, title, strState, trnState, timerText) {
        drawRoundBox(x, y, 78, 96, 10, 'rgba(13, 15, 23, 0.95)', '#383E56', 2);

        // หัวข้อเสาไฟ
        drawRoundBox(x - 8, y - 20, 94, 18, 5, '#181B26', '#F59E0B', 1);
        ctx.fillStyle = '#FBBF24';
        ctx.font = '700 9.5px "Plus Jakarta Sans", "IBM Plex Sans Thai", sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(title, x + 39, y - 7);

        // ป้ายคอลัมน์ย่อย: ตรง (●) vs เลี้ยว (➔)
        ctx.fillStyle = '#94A3B8';
        ctx.font = '600 9px "IBM Plex Sans Thai", sans-serif';
        ctx.fillText('ตรง', x + 22, y + 13);
        ctx.fillText('เลี้ยว', x + 56, y + 13);

        const colors = [
            { key: 'R', on: '#F43F5E', off: '#2D161E', py: y + 27 },
            { key: 'Y', on: '#F59E0B', off: '#2E2514', py: y + 46 },
            { key: 'G', on: '#10B981', off: '#112A22', py: y + 65 }
        ];

        colors.forEach(c => {
            // ดวงไฟทางตรง (ซ้าย)
            const sOn = (strState === c.key);
            ctx.beginPath(); ctx.arc(x + 22, c.py, 7.5, 0, Math.PI*2);
            ctx.fillStyle = sOn ? c.on : c.off;
            ctx.shadowBlur = sOn ? 12 : 0; ctx.shadowColor = c.on;
            ctx.fill(); ctx.shadowBlur = 0;

            // ดวงไฟเลี้ยวขวา (ขวา)
            const tOn = (trnState === c.key);
            ctx.beginPath(); ctx.arc(x + 56, c.py, 7.5, 0, Math.PI*2);
            ctx.fillStyle = tOn ? c.on : c.off;
            ctx.shadowBlur = tOn ? 12 : 0; ctx.shadowColor = c.on;
            ctx.fill(); ctx.shadowBlur = 0;

            // วาดสัญลักษณ์ลูกศร ➔ ทับบนดวงไฟเลี้ยว
            ctx.fillStyle = tOn ? '#090A0F' : '#475569';
            ctx.font = 'bold 9px monospace';
            ctx.fillText('➔', x + 56, c.py + 3);
        });

        // นับถอยหลัง
        ctx.fillStyle = '#F8FAFC';
        ctx.font = '700 10.5px "JetBrains Mono", monospace';
        ctx.fillText(timerText, x + 39, y + 88);
    }

    let packetT = 0;
    let mainTurnProgress = 0.15;
    let sideTurnProgress = 0.15;
    let sideStraightScroll = 0;

    function renderFrame() {
        const now = Date.now();
        const elapsedSec = paused ? pausedSimSec : (now - startEpochMs) / 1000.0;
        const st = getActiveState(elapsedSec);
        packetT = (packetT + 0.02) % 1.0;

        // อัปเดตป้ายสถานะด้านบน
        const badge = document.getElementById('phaseBadge');
        if (st.group === 'PREEMPT') {
            badge.textContent = '🚑 PHASE: EMERGENCY PREEMPTION (กักไฟรถพยาบาล)';
            badge.style.borderColor = '#F43F5E'; badge.style.color = '#FDA4AF';
        } else if (st.group === 'OPT') {
            badge.textContent = '🧠 PHASE: CLOUD AI OPTIMIZING (คำนวณแผน 4 เฟส)';
            badge.style.borderColor = '#6366F1'; badge.style.color = '#A5B4FC';
        } else if (['C1', 'C2', 'C3'].includes(st.group)) {
            badge.textContent = `🟢 PHASE: 4-PHASE RECOVERY (${st.group} | แผน [${plan.join('s, ')}s])`;
            badge.style.borderColor = '#10B981'; badge.style.color = '#6EE7B7';
        } else {
            badge.textContent = `🔄 PHASE: 4-PHASE NORMAL CYCLE (${st.lcd1})`;
            badge.style.borderColor = '#F59E0B'; badge.style.color = '#FCD34D';
        }

        ['PREEMPT', 'OPT', 'C1', 'C2', 'C3', 'NORMAL'].forEach(g => {
            const el = document.getElementById('node_' + g);
            if (!el) return;
            el.className = 'step-node';
            if (st.group === g) {
                if (g === 'PREEMPT') el.classList.add('active-emg');
                else if (g === 'NORMAL') el.classList.add('active-norm');
                else el.classList.add('active-rec');
            }
        });

        // 1. วาดพื้นหลัง Carbon Grid
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#0D0F17';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.strokeStyle = 'rgba(38, 42, 59, 0.45)';
        ctx.lineWidth = 1;
        for (let gx = 0; gx < canvas.width; gx += 38) {
            ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, canvas.height); ctx.stroke();
        }
        for (let gy = 0; gy < canvas.height; gy += 38) {
            ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(canvas.width, gy); ctx.stroke();
        }

        // พิกัดถนน 4 เลนย่อย (กว้าง 152px ทั้งสายหลักและสายรอง)
        const rMainY = 148, rMainH = 152; // y: 148..300 (กึ่งกลาง 224)
        const rSideX = 434, rSideW = 152; // x: 434..586 (กึ่งกลาง 510)

        // พื้นถนนแอสฟัลต์
        ctx.fillStyle = '#1E2230';
        ctx.fillRect(0, rMainY, canvas.width, rMainH);
        ctx.fillRect(rSideX, 0, rSideW, canvas.height);

        // เส้นแบ่งเลนย่อย (ระหว่างเลนทางตรง และ เลนเลี้ยวขวา)
        ctx.strokeStyle = 'rgba(148, 163, 184, 0.35)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([10, 10]);
        // เลนย่อยสายหลัก
        [rMainY + 38, rMainY + 114].forEach(ly => {
            ctx.beginPath();
            ctx.moveTo(0, ly); ctx.lineTo(rSideX - 16, ly);
            ctx.moveTo(rSideX + rSideW + 16, ly); ctx.lineTo(canvas.width, ly);
            ctx.stroke();
        });
        // เลนย่อยสายรอง
        [rSideX + 38, rSideX + 114].forEach(lx => {
            ctx.beginPath();
            ctx.moveTo(lx, 0); ctx.lineTo(lx, rMainY - 16);
            ctx.moveTo(lx, rMainY + rMainH + 16); ctx.lineTo(lx, canvas.height);
            ctx.stroke();
        });
        ctx.setLineDash([]);

        // เส้นคู่เหลืองเกาะกลางถนน (Median Divider)
        ctx.strokeStyle = '#F59E0B';
        ctx.lineWidth = 2.5;
        const midY = rMainY + rMainH / 2;
        const midX = rSideX + rSideW / 2;
        ctx.beginPath();
        ctx.moveTo(0, midY); ctx.lineTo(rSideX - 16, midY);
        ctx.moveTo(rSideX + rSideW + 16, midY); ctx.lineTo(canvas.width, midY);
        ctx.moveTo(midX, 0); ctx.lineTo(midX, rMainY - 16);
        ctx.moveTo(midX, rMainY + rMainH + 16); ctx.lineTo(midX, canvas.height);
        ctx.stroke();

        // เส้นขอบถนนด้านนอก
        ctx.strokeStyle = '#475569';
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(0, rMainY); ctx.lineTo(rSideX, rMainY);
        ctx.moveTo(rSideX + rSideW, rMainY); ctx.lineTo(canvas.width, rMainY);
        ctx.moveTo(0, rMainY + rMainH); ctx.lineTo(rSideX, rMainY + rMainH);
        ctx.moveTo(rSideX + rSideW, rMainY + rMainH); ctx.lineTo(canvas.width, rMainY + rMainH);
        ctx.moveTo(rSideX, 0); ctx.lineTo(rSideX, rMainY);
        ctx.moveTo(rSideX + rSideW, 0); ctx.lineTo(rSideX + rSideW, rMainY);
        ctx.moveTo(rSideX, rMainY + rMainH); ctx.lineTo(rSideX, canvas.height);
        ctx.moveTo(rSideX + rSideW, rMainY + rMainH); ctx.lineTo(rSideX + rSideW, canvas.height);
        ctx.stroke();

        // เส้นไกด์นำทางเลี้ยวโค้งกลางสี่แยก (Turning Guide Arcs)
        ctx.strokeStyle = 'rgba(245, 158, 11, 0.22)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([5, 6]);
        // โค้งเลี้ยวสายรอง (ล่างขึ้นบน -> เลี้ยวขวาไปทางตะวันออก)
        ctx.beginPath();
        ctx.moveTo(rSideX + 57, rMainY + rMainH);
        ctx.quadraticCurveTo(rSideX + 57, rMainY + 19, rSideX + rSideW, rMainY + 19);
        ctx.stroke();
        // โค้งเลี้ยวสายหลัก (ซ้ายไปขวา -> เลี้ยวลงล่าง)
        ctx.beginPath();
        ctx.moveTo(rSideX, rMainY + 57);
        ctx.quadraticCurveTo(rSideX + 133, rMainY + 57, rSideX + 133, rMainY + rMainH);
        ctx.stroke();
        ctx.setLineDash([]);

        // สัญลักษณ์ลูกศรบอกเลนบนพื้นถนน
        ctx.fillStyle = 'rgba(226, 232, 240, 0.45)';
        ctx.font = 'bold 13px monospace';
        ctx.textAlign = 'center';
        ctx.fillText('➔ ตรง', rSideX - 42, rMainY + 23);
        ctx.fillText('↳ เลี้ยว', rSideX - 42, rMainY + 61);
        ctx.fillText('↰ เลี้ยว', rSideX + rSideW + 44, rMainY + 99);
        ctx.fillText('⬅ ตรง', rSideX + rSideW + 44, rMainY + 137);

        ctx.fillText('↑', rSideX + 19, rMainY + rMainH + 28);
        ctx.fillText('↱', rSideX + 57, rMainY + rMainH + 28);
        ctx.fillText('↲', rSideX + 95, rMainY - 18);
        ctx.fillText('↓', rSideX + 133, rMainY - 18);

        // -------------------------------------------------------------------
        // อัปเดตและวาดรถยนต์ในทั้ง 4 เฟส (ตรง + เลี้ยวโค้ง Bezier ไม่ชนกัน 100%)
        // -------------------------------------------------------------------
        const mStrGo = (st.lights.mStr === 'G' || st.lights.mStr === 'Y');
        const mTrnGo = (st.lights.mTrn === 'G' || st.lights.mTrn === 'Y');
        const sStrGo = (st.lights.sStr === 'G' || st.lights.sStr === 'Y');
        const sTrnGo = (st.lights.sTrn === 'G' || st.lights.sTrn === 'Y');
        const speedMain = 1.6 + (qm / 60.0) * 1.3;

        if (!paused) {
            updateStraightLane(eastStrCars, 1, mStrGo, rSideX - 36, speedMain);
            updateStraightLane(westStrCars, -1, mStrGo, rSideX + rSideW + 36, speedMain);

            if (mTrnGo) mainTurnProgress = (mainTurnProgress + 0.016) % 1.0;
            else mainTurnProgress = 0.0;

            if (sTrnGo) sideTurnProgress = (sideTurnProgress + 0.016) % 1.0;
            else sideTurnProgress = 0.0;

            if (sStrGo) sideStraightScroll = (sideStraightScroll + 1.8) % 32;
            else sideStraightScroll = 0;
        }

        // 1) วาดรถสายหลัก วิ่งตรง (เลนซ้าย->ขวา y=167 และ เลนขวา->ซ้าย y=281)
        eastStrCars.forEach(c => {
            if (st.group === 'PREEMPT') return;
            drawCarRotated(c.x, rMainY + 19, 0, c.c, false);
        });
        westStrCars.forEach(c => {
            drawCarRotated(c.x, rMainY + 133, Math.PI, c.c, false);
        });

        // รถพยาบาลในช่วง PREEMPT
        if (st.group === 'PREEMPT') {
            const ambX = -50 + (canvas.width + 100) * st.ratio;
            const sirengrad = ctx.createLinearGradient(ambX - 50, 0, ambX + 90, 0);
            sirengrad.addColorStop(0, 'rgba(244, 63, 94, 0)');
            sirengrad.addColorStop(0.5, 'rgba(244, 63, 94, 0.32)');
            sirengrad.addColorStop(1, 'rgba(59, 130, 246, 0)');
            ctx.fillStyle = sirengrad;
            ctx.fillRect(0, rMainY, canvas.width, 40);
            drawCarRotated(ambX, rMainY + 19, 0, '#FFFFFF', true);
        }

        // 2) วาดรถสายหลัก เลี้ยวขวา (เมื่อไฟเลี้ยว mTrnGo สว่าง จะวิ่งโค้ง Bezier เข้าถนนสายรอง)
        if (mTrnGo) {
            // คันที่ 1: วิ่งจากซ้าย เลี้ยวลงถนนรองด้านล่าง
            const pE = getBezierPointAndAngle(
                mainTurnProgress,
                { x: rSideX - 25, y: rMainY + 57 },
                { x: rSideX + 133, y: rMainY + 57 },
                { x: rSideX + 133, y: rMainY + rMainH + 65 }
            );
            drawCarRotated(pE.x, pE.y, pE.angle, '#F59E0B', false);

            // คันที่ 2: วิ่งจากขวา เลี้ยวขึ้นถนนรองด้านบน
            const pW = getBezierPointAndAngle(
                mainTurnProgress,
                { x: rSideX + rSideW + 25, y: rMainY + 95 },
                { x: rSideX + 19, y: rMainY + 95 },
                { x: rSideX + 19, y: rMainY - 65 }
            );
            drawCarRotated(pW.x, pW.y, pW.angle, '#38BDF8', false);
        } else {
            // จอดรอไฟเขียวลูกศรเลี้ยวขวาอย่างเป็นระเบียบ
            drawCarRotated(rSideX - 38, rMainY + 57, 0, '#F59E0B', false);
            drawCarRotated(rSideX - 96, rMainY + 57, 0, '#A855F7', false);
            drawCarRotated(rSideX + rSideW + 38, rMainY + 95, Math.PI, '#38BDF8', false);
        }

        // 3) วาดแถวคอยถนนสายรอง ทางตรง (วัดด้วยเซนเซอร์ HC-SR04 ตามค่า liveQ จริง)
        const qCount = Math.min(5, Math.ceil(st.liveQ));
        const laneN_X = rSideX + 19;
        const stopS_Y = rMainY + rMainH + 34;

        if (sStrGo && st.liveQ > 0.1) {
            const passY = (rMainY + rMainH) - ((now / 6.5) % (rMainH + 110));
            drawCarRotated(laneN_X, passY, -Math.PI/2, '#10B981', false);
        }
        for (let i = 0; i < qCount; i++) {
            const cy = stopS_Y + (i * 34) - (sStrGo ? sideStraightScroll * 0.5 : 0);
            if (cy < canvas.height - 48) {
                const col = i === 0 ? '#10B981' : (i < 3 ? '#F59E0B' : '#F43F5E');
                drawCarRotated(laneN_X, cy, -Math.PI/2, col, false);
            }
        }

        // 4) วาดรถถนนสายรอง เลี้ยวขวา (เมื่อไฟเลี้ยว sTrnGo สว่าง จะวิ่งโค้ง Bezier ออกสู่สายหลัก)
        const laneTurnN_X = rSideX + 57;
        if (sTrnGo) {
            // เลี้ยวจากสายรองล่าง ออกไปสายหลักฝั่งขวา
            const pS = getBezierPointAndAngle(
                sideTurnProgress,
                { x: laneTurnN_X, y: rMainY + rMainH + 20 },
                { x: laneTurnN_X, y: rMainY + 19 },
                { x: rSideX + rSideW + 80, y: rMainY + 19 }
            );
            drawCarRotated(pS.x, pS.y, pS.angle, '#10B981', false);

            // เลี้ยวจากสายรองบน ออกไปสายหลักฝั่งซ้าย
            const pN = getBezierPointAndAngle(
                sideTurnProgress,
                { x: rSideX + 95, y: rMainY - 20 },
                { x: rSideX + 95, y: rMainY + 133 },
                { x: rSideX - 80, y: rMainY + 133 }
            );
            drawCarRotated(pN.x, pN.y, pN.angle, '#EC4899', false);
        } else {
            // จอดรอไฟเลี้ยวที่เลนเลี้ยวสายรอง
            if (st.liveQ > 0.5) {
                drawCarRotated(laneTurnN_X, stopS_Y + 4, -Math.PI/2, '#10B981', false);
            }
            drawCarRotated(rSideX + 95, rMainY - 36, Math.PI/2, '#EC4899', false);
        }

        // -------------------------------------------------------------------
        // วาดเซนเซอร์ Ultrasonic HC-SR04 + เรดาร์ตรวจจับแถวคอย
        // -------------------------------------------------------------------
        const senX = rSideX - 86, senY = rMainY + rMainH + 58;
        drawRoundBox(senX - 62, senY - 20, 124, 46, 10, '#12141D', CFG.sensor_fault ? '#F43F5E' : '#10B981', 2);
        ctx.fillStyle = CFG.sensor_fault ? '#F43F5E' : '#10B981';
        ctx.font = '700 10.5px "Plus Jakarta Sans", sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('📡 HC-SR04 SONAR', senX, senY - 3);
        ctx.fillStyle = '#FFFFFF';
        ctx.font = '700 12px "JetBrains Mono", monospace';
        ctx.fillText(CFG.sensor_fault ? 'FAULT (Est:8)' : `Queue: ${st.liveQ.toFixed(1)} คัน`, senX, senY + 16);

        for (let w = 1; w <= 3; w++) {
            const rad = ((now / 26) + w * 14) % 44;
            ctx.beginPath();
            ctx.arc(senX + 62, senY + 4, rad, -0.4, 0.4);
            ctx.strokeStyle = CFG.sensor_fault ? `rgba(244,63,94,${1 - rad/44})` : `rgba(16,185,129,${1 - rad/44})`;
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        // -------------------------------------------------------------------
        // วาดเสาไฟจราจร Dual-Head (แสดงทั้งไฟตรง ● และไฟเลี้ยว ➔ ครบ 12 ดวง)
        // -------------------------------------------------------------------
        drawDualSignalHead(
            rSideX - 102, rMainY - 108,
            'MAIN ROAD (6 LEDs)',
            st.lights.mStr, st.lights.mTrn,
            (st.lights.mStr === 'G' || st.lights.mTrn === 'G') ? `${st.secLeft}s` : 'HOLD'
        );

        drawDualSignalHead(
            rSideX + rSideW + 24, rMainY + rMainH + 22,
            'SIDE ROAD (6 LEDs)',
            st.lights.sStr, st.lights.sTrn,
            (st.lights.sStr === 'G' || st.lights.sTrn === 'G') ? `${st.secLeft}s` : 'WAIT'
        );

        // กล่อง Cloud AI & MQTT Telemetry (มุมซ้ายบน)
        drawRoundBox(20, 14, 285, 76, 12, 'rgba(18, 20, 29, 0.95)', '#6366F1', 1.8);
        ctx.fillStyle = '#818CF8';
        ctx.font = '700 11.5px "Plus Jakarta Sans", sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('☁️ CLOUD AI ENGINE (Multi-Output RF)', 34, 34);
        ctx.fillStyle = '#CBD5E1';
        ctx.font = '500 11px "IBM Plex Sans Thai", sans-serif';
        ctx.fillText(`Test Accuracy R² = ${CFG.r2_score} | Flow: ${qm.toFixed(0)} คัน/นาที`, 34, 54);
        ctx.fillStyle = '#FBBF24';
        ctx.font = '700 11px "JetBrains Mono", monospace';
        ctx.fillText(`AI Plan: C1=${plan[0]}s | C2=${plan[1]}s | C3=${plan[2]}s`, 34, 74);

        // หน้าจอ Wokwi ESP32 LCD1602 (มุมขวาบน)
        const lcdX = canvas.width - 290, lcdY = 14;
        drawRoundBox(lcdX, lcdY, 270, 78, 12, '#0F1F1C', '#10B981', 1.8);
        ctx.fillStyle = '#34D399';
        ctx.font = '700 10px "JetBrains Mono", monospace';
        ctx.fillText('📟 WOKWI LCD1602 (I2C 0x27)', lcdX + 14, lcdY + 19);

        drawRoundBox(lcdX + 12, lcdY + 25, 246, 43, 6, '#84CC16', '#3F6212', 1.5);
        ctx.fillStyle = '#090A0F';
        ctx.font = '700 13.5px "JetBrains Mono", monospace';
        ctx.fillText(st.lcd0.padEnd(16, ' ').substring(0, 16), lcdX + 22, lcdY + 43);
        ctx.fillText(st.lcd1.padEnd(16, ' ').substring(0, 16), lcdX + 22, lcdY + 61);

        // กล่องเปรียบเทียบแถวคอย Real-Time (มุมขวาล่าง)
        const cmpX = canvas.width - 340, cmpY = rMainY + rMainH + 16;
        drawRoundBox(cmpX, cmpY, 320, 96, 12, 'rgba(18, 20, 29, 0.95)', '#2E3348', 1.5);
        ctx.fillStyle = '#F8FAFC';
        ctx.font = '600 11.5px "IBM Plex Sans Thai", sans-serif';
        ctx.fillText('📊 เปรียบเทียบแถวคอยถนนสายรอง (AI vs ระบบไฟเดิม)', cmpX + 14, cmpY + 21);

        ctx.fillStyle = '#10B981';
        ctx.font = '600 11px "IBM Plex Sans Thai", sans-serif';
        ctx.fillText(`AI 4-Phase Recovery: ${st.liveQ.toFixed(2)} คัน`, cmpX + 14, cmpY + 42);
        drawRoundBox(cmpX + 14, cmpY + 47, 290, 8, 4, '#1E293B', null);
        drawRoundBox(cmpX + 14, cmpY + 47, Math.min(290, (st.liveQ / 18.0) * 290), 8, 4, '#10B981', null);

        ctx.fillStyle = '#F43F5E';
        ctx.fillText(`ระบบไฟปกติ (ไม่มี AI): ${st.convQ.toFixed(2)} คัน`, cmpX + 14, cmpY + 71);
        drawRoundBox(cmpX + 14, cmpY + 76, 290, 8, 4, '#1E293B', null);
        drawRoundBox(cmpX + 14, cmpY + 76, Math.min(290, (st.convQ / 18.0) * 290), 8, 4, '#F43F5E', null);

        // แถบอธิบายสถานะฟิสิกส์ด้านล่างซ้าย
        drawRoundBox(20, canvas.height - 44, cmpX - 34, 34, 9, 'rgba(18, 20, 29, 0.95)', '#F59E0B', 1.4);
        ctx.fillStyle = '#F8FAFC';
        ctx.font = '500 11.5px "IBM Plex Sans Thai", sans-serif';
        ctx.fillText(`⚡ ${st.desc}`, 32, canvas.height - 22);

        requestAnimationFrame(renderFrame);
    }

    requestAnimationFrame(renderFrame);
    </script>
    </body>
    </html>
    """
    return html_template.replace("__CONFIG_JSON__", config_json)


# ---------------------------------------------------------------------------
# 7. ส่วนแสดงผล Top Command Bar (แทนที่ Banner และ Sidebar แบบเดิม)
# ---------------------------------------------------------------------------
current_th_time_live = datetime.now(TH_TIMEZONE).strftime("%H:%M:%S")
mqtt_dot = "dot-online" if store["connected"] else "dot-warn"
mqtt_text = "HiveMQ Connected" if store["connected"] else "Connecting Broker..."

if store["ai_data"]:
    r2_val = store["ai_data"].get("r2_score", 0.9629)
    ai_status_text = f"RF Model R² = {r2_val}"
else:
    ai_status_text = "AI Standby (Ready)"

if store["closed_loop_data"]:
    if store["closed_loop_data"].get("early_cut"):
        saved_sec = store["closed_loop_data"].get("time_saved_sec", 0)
        cl_text = f"Early Cut (-{saved_sec}s)"
        cl_dot = "dot-warn"
    else:
        cl_text = "Closed-Loop Synced"
        cl_dot = "dot-online"
else:
    cl_text = "4-Phase Active"
    cl_dot = "dot-online"

st.markdown(f"""
<div class="os-navbar">
    <div class="os-brand">
        <div class="os-logo-badge">⚡</div>
        <div class="os-title-group">
            <h1>AERO-TRAFFIC OS // 4-Phase Smart Intersection & Queue Rebalancing</h1>
            <p>ระบบควบคุมสี่แยกไฟจราจรอัจฉริยะ 4 เฟส (ทางตรง + เลี้ยวขวาอิสระ 12 LEDs) และปรับสมดุลแถวคอยหลังรถฉุกเฉินแทรกสัญญาณไฟ</p>
        </div>
    </div>
    <div class="os-telemetry-pills">
        <div class="t-pill"><span class="dot {mqtt_dot}"></span>{mqtt_text}</div>
        <div class="t-pill"><span class="dot dot-online"></span>{ai_status_text}</div>
        <div class="t-pill"><span class="dot {cl_dot}"></span>{cl_text}</div>
        <div class="clock-pill">🕒 {current_th_time_live} UTC+7</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 8. แสดงผล Digital Twin 4-Phase Intersection Canvas
# ---------------------------------------------------------------------------
anim_html = build_4phase_animation_html(
    store["ai_data"],
    store["closed_loop_data"],
    store["event_seq"]
)
components.html(anim_html, height=630, scrolling=False)

# ---------------------------------------------------------------------------
# 9. ส่วนแสดงผล Bento KPI Cards & Interactive Analytics
# ---------------------------------------------------------------------------
if store["ai_data"] is None:
    st.markdown("""
    <div class="panel-box" style="border-left: 4px solid #F59E0B; display: flex; justify-content: space-between; align-items: center;">
        <div>
            <strong style="color: #FBBF24; font-size: 0.95rem;">📡 ระบบพร้อมรับสัญญาณ Telemetry จากบอร์ด ESP32 (Wokwi)</strong>
            <p style="color: #94A3B8; font-size: 0.85rem; margin: 4px 0 0 0;">
                กดปุ่มสีแดง (<code>btn_emg</code> Pin 4) ใน Wokwi เพื่อส่งข้อมูลจริงมายังหน้าเว็บ หรือกดปุ่ม <b>"🎬 เล่นซ้ำตั้งแต่รถพยาบาลแทรกไฟ"</b> บนจอ Digital Twin ด้านบนเพื่อสาธิตการทำงานทั้ง 4 เฟสได้ทันที
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    data = store["ai_data"]
    phys = data["physics"]
    plan = data["plan"]
    cl_data = store["closed_loop_data"]

    if data.get("sensor_fault"):
        st.error("⚠️ **ตรวจพบความผิดปกติของเซนเซอร์ HC-SR04:** ระบบสลับเข้าสู่โหมด Fault-Tolerant ใช้ค่าประเมินทางสถิติสำรอง (8.0 คัน) อัตโนมัติ")

    # การ์ดตัวเลข Bento Grid 4 ใบ (ดีไซน์ใหม่ทั้งหมด ไม่ใช้ st.metric เดิม)
    st.markdown(f"""
    <div class="bento-grid">
        <div class="bento-card bento-rose">
            <div class="bento-label">🚑 เวลากักไฟรถฉุกเฉิน (Preemption)</div>
            <div class="bento-value">{data['tp']} s</div>
            <div class="bento-sub">อัตราไหลสายหลัก: {data['qm']:.0f} คัน/นาที</div>
        </div>
        <div class="bento-card bento-amber">
            <div class="bento-label">🚗 แถวคอยสะสมรวม (Accumulated Queue)</div>
            <div class="bento-value">{phys['q_accumulated']} คัน</div>
            <div class="bento-sub">คิวตั้งต้น {data['q0']:.0f} คัน + ไหลเข้า {round(phys['q_accumulated'] - data['q0'], 2)} คัน</div>
        </div>
        <div class="bento-card bento-emerald">
            <div class="bento-label">🟢 แผนไฟเขียวสายรอง 3 รอบ (AI Plan)</div>
            <div class="bento-value">{sum(plan)} s</div>
            <div class="bento-sub">C1: {plan[0]}s &nbsp;|&nbsp; C2: {plan[1]}s &nbsp;|&nbsp; C3: {plan[2]}s</div>
        </div>
        <div class="bento-card bento-indigo">
            <div class="bento-label">⚡ ประสิทธิภาพลดความล่าช้า (Delay Saved)</div>
            <div class="bento-value">{phys['pct_saved']}%</div>
            <div class="bento-sub">ระบายรถออกได้รวม {phys['cleared_cars']} คัน</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # แถวกราฟวิเคราะห์ 3 คอลัมน์ในโทนสี Carbon / Emerald / Amber / Indigo
    c_line, c_bar, c_gauge = st.columns([2.2, 1.3, 1.3])
    stages = ["หลังรถพยาบาลผ่าน", "จบรอบ 1 (C1)", "จบรอบ 2 (C2)", "จบรอบ 3 (C3)"]

    with c_line:
        st.markdown('<div class="section-header">📈 การสลายตัวของแถวคอยถนนสายรอง (Queue Dissipation Profile)</div>', unsafe_allow_html=True)
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=stages, y=phys["conv_curve"],
            mode='lines+markers', name='ระบบไฟปกติ (ไม่มี AI)',
            line=dict(color='#F43F5E', width=3, dash='dash'),
            marker=dict(size=8, symbol='square')
        ))
        fig_line.add_trace(go.Scatter(
            x=stages, y=phys["ai_curve"],
            mode='lines+markers', name=f'แผน AI 4-Phase ({plan[0]}s, {plan[1]}s, {plan[2]}s)',
            line=dict(color='#F59E0B', width=4),
            marker=dict(size=10, symbol='circle')
        ))
        if cl_data and "actual_q_history" in cl_data:
            actual_q = cl_data["actual_q_history"]
            fig_line.add_trace(go.Scatter(
                x=stages[:len(actual_q)], y=actual_q,
                mode='lines+markers', name='วัดจริงจากเซนเซอร์ (Closed-Loop)',
                line=dict(color='#10B981', width=4, dash='dot'),
                marker=dict(size=11, symbol='diamond')
            ))
        fig_line.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(18,20,29,0.9)",
            plot_bgcolor="rgba(13,15,23,0.7)",
            font=dict(family="Plus Jakarta Sans, IBM Plex Sans Thai", color="#CBD5E1"),
            yaxis_title="ความยาวแถวคอย (คัน)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=15, r=15, t=35, b=15),
            height=320
        )
        st.plotly_chart(fig_line, use_container_width=True)

    with c_bar:
        st.markdown('<div class="section-header">📊 ดัชนีความล่าช้าสะสม (Webster Delay)</div>', unsafe_allow_html=True)
        fig_bar = go.Figure(data=[
            go.Bar(
                x=["ระบบเดิม (Snapback)", "AI 4-Phase"],
                y=[phys["delay_snapback"], phys["delay_ai"]],
                text=[f"{phys['delay_snapback']} s", f"{phys['delay_ai']} s"],
                textposition='auto',
                marker_color=['#F43F5E', '#10B981'],
                width=0.45
            )
        ])
        fig_bar.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(18,20,29,0.9)",
            plot_bgcolor="rgba(13,15,23,0.7)",
            font=dict(family="Plus Jakarta Sans, IBM Plex Sans Thai", color="#CBD5E1"),
            yaxis_title="ความล่าช้า (วินาที-คัน)",
            margin=dict(l=15, r=15, t=35, b=15),
            height=320
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with c_gauge:
        st.markdown('<div class="section-header">🎯 ประสิทธิภาพการฟื้นฟูสมดุล</div>', unsafe_allow_html=True)
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=phys["pct_saved"],
            domain={'x': [0.05, 0.95], 'y': [0.12, 0.88]},
            number={'suffix': "%", 'font': {'size': 36, 'color': '#10B981', 'family': 'JetBrains Mono'}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1},
                'bar': {'color': "#F59E0B"},
                'bgcolor': "#181B26",
                'steps': [
                    {'range': [0, 40], 'color': "rgba(244, 63, 94, 0.2)"},
                    {'range': [40, 70], 'color': "rgba(245, 158, 11, 0.2)"},
                    {'range': [70, 100], 'color': "rgba(16, 185, 129, 0.22)"}
                ]
            }
        ))
        fig_gauge.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(18,20,29,0.9)",
            font=dict(family="Plus Jakarta Sans, IBM Plex Sans Thai", color="#CBD5E1"),
            margin=dict(l=25, r=25, t=20, b=15),
            height=320
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    # แถวตารางข้อมูล 4-Phase Multi-Cycle Plan และ Event Log
    tab_col1, tab_col2 = st.columns([3.1, 1.9])

    with tab_col1:
        st.markdown('<div class="section-header">📋 ตารางลำดับเฟสการฟื้นฟู 4-Phase Multi-Cycle Recovery</div>', unsafe_allow_html=True)
        actual_c = cl_data["actual_q_history"][1:] if (cl_data and "actual_q_history" in cl_data) else ["รอผล...", "รอผล...", "รอผล..."]
        while len(actual_c) < 3:
            actual_c.append(0)

        df_plan = pd.DataFrame({
            "รอบฟื้นฟู": ["รอบที่ 1 (C1)", "รอบที่ 2 (C2)", "รอบที่ 3 (C3)"],
            "ไฟเขียวสายรองตรง (AI)": [plan[0], plan[1], plan[2]],
            "เฟสเสริมไร้จุดตัด (Fixed)": ["เลี้ยวรอง 2s | หลักตรง 3s | เลี้ยวหลัก 2s"] * 3,
            "คิวคาดการณ์ (AI)": [f"{phys['ai_curve'][1]} คัน", f"{phys['ai_curve'][2]} คัน", f"{phys['ai_curve'][3]} คัน"],
            "คิวจริง (Sensor)": [
                f"{actual_c[0]} คัน" if isinstance(actual_c[0], (int, float)) else actual_c[0],
                f"{actual_c[1]} คัน" if isinstance(actual_c[1], (int, float)) else actual_c[1],
                f"{actual_c[2]} คัน" if isinstance(actual_c[2], (int, float)) else actual_c[2]
            ],
            "เป้าหมายเชิงวิศวกรรม": ["Peak Shaving (ตัดยอดวิกฤต)", "Dynamic Balance (เกลี่ยสมดุล)", "Phase Resync (คืนซิงค์ 4 เฟส)"]
        })
        st.dataframe(
            df_plan,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ไฟเขียวสายรองตรง (AI)": st.column_config.ProgressColumn(
                    "ไฟเขียวสายรองตรง (s)",
                    format="%d วินาที",
                    min_value=0,
                    max_value=16
                )
            }
        )

    with tab_col2:
        head_c1, head_c2 = st.columns([3, 1.2])
        with head_c1:
            st.markdown('<div class="section-header">🕒 บันทึกเหตุการณ์ (Telemetry Log)</div>', unsafe_allow_html=True)
        with head_c2:
            if st.button("🗑️ ล้างประวัติ", use_container_width=True):
                store["event_log"].clear()
                st.rerun()

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
