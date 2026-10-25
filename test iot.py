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

# 2. ตั้งค่าหน้าเว็บแบบเต็มจอ
st.set_page_config(
    page_title="Intelligent Queue Rebalancing & Traffic Control",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 3. ตั้งค่าการรีเฟรชหน้าจออัตโนมัติทุกๆ 1 วินาทีเพื่อให้นาฬิกาวิ่งแบบเรียลไทม์
st_autorefresh(interval=1000, limit=None, key="realtime_clock")

# 4. ตกแต่ง UI ด้วย Custom CSS (ฟอนต์ Prompt + การ์ดเรืองแสงสไตล์ศูนย์ควบคุม)
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
                    "เวลา": current_th_time,
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
# 6. ฟังก์ชันสร้าง HTML5 Canvas Animation (ซิงค์ตามสมการ Colab & Wokwi 100%)
# ---------------------------------------------------------------------------
def build_traffic_animation_html(ai_data, cl_data, event_seq):
    sim_config = {
        "has_event": ai_data is not None,
        "event_seq": event_seq,
        "tp": float(ai_data["tp"]) if ai_data else 6.0,
        "q0": float(ai_data["q0"]) if ai_data else 5.0,
        "qm": float(ai_data["qm"]) if ai_data else 30.0,
        "sensor_fault": bool(ai_data.get("sensor_fault", False)) if ai_data else False,
        "plan": ai_data["plan"] if ai_data else [8, 5, 3],
        "r2_score": float(ai_data.get("r2_score", 0.9945)) if ai_data else 0.9945,
        "q_accumulated": float(ai_data["physics"]["q_accumulated"]) if ai_data else 6.5,
        "ai_curve": ai_data["physics"]["ai_curve"] if ai_data else [6.5, 1.3, 0.0, 0.0],
        "conv_curve": ai_data["physics"]["conv_curve"] if ai_data else [6.5, 5.95, 5.4, 4.85],
        "pct_saved": float(ai_data["physics"]["pct_saved"]) if ai_data else 68.5,
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
        @import url('https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
        body {
            background: transparent;
            font-family: 'Prompt', sans-serif;
            color: #e2e8f0;
            overflow: hidden;
        }
        .sim-wrapper {
            background: linear-gradient(145deg, #0f1522, #182234);
            border: 1px solid #2e4057;
            border-radius: 14px;
            padding: 12px 16px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.45);
        }
        .sim-topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid #26354a;
        }
        .sim-title {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 1rem;
            font-weight: 600;
            color: #00d4ff;
        }
        .badge-mode {
            font-size: 0.78rem;
            padding: 3px 10px;
            border-radius: 20px;
            background: rgba(0, 212, 255, 0.15);
            border: 1px solid #00d4ff;
            color: #00d4ff;
        }
        .sim-controls {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }
        .btn-ctrl {
            background: #1e293b;
            color: #cbd5e1;
            border: 1px solid #334155;
            padding: 4px 10px;
            border-radius: 7px;
            font-family: 'Prompt', sans-serif;
            font-size: 0.78rem;
            cursor: pointer;
            transition: all 0.15s;
        }
        .btn-ctrl:hover {
            background: #334155;
            color: #ffffff;
            border-color: #00d4ff;
        }
        .canvas-container {
            position: relative;
            width: 100%;
            height: 430px;
            background: #1b2432;
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #2d3d54;
        }
        canvas {
            width: 100%;
            height: 100%;
            display: block;
        }
        .timeline-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 8px;
            font-size: 0.8rem;
            color: #94a3b8;
            gap: 12px;
        }
        .phase-steps {
            display: flex;
            gap: 6px;
            flex: 1;
        }
        .phase-pill {
            flex: 1;
            text-align: center;
            padding: 4px 6px;
            border-radius: 6px;
            background: #161f2e;
            border: 1px solid #26354a;
            font-size: 0.75rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        .phase-pill.current {
            background: rgba(0, 230, 118, 0.18);
            border-color: #00e676;
            color: #ffffff;
            font-weight: 600;
            box-shadow: 0 0 10px rgba(0, 230, 118, 0.3);
        }
        .phase-pill.preempt-active {
            background: rgba(255, 75, 75, 0.22);
            border-color: #ff4b4b;
            color: #ffffff;
            font-weight: 600;
            box-shadow: 0 0 10px rgba(255, 75, 75, 0.35);
        }
    </style>
    </head>
    <body>
    <div class="sim-wrapper">
        <div class="sim-topbar">
            <div class="sim-title">
                <span>🌐 Digital Twin: Smart Traffic & Queue Rebalancing Animation</span>
                <span id="modeBadge" class="badge-mode">กำลังซิงค์ข้อมูล...</span>
            </div>
            <div class="sim-controls">
                <button class="btn-ctrl" id="btnLive" onclick="startLiveSync()">🔴 ซิงค์ตามบอร์ด Wokwi</button>
                <button class="btn-ctrl" id="btnReplay" onclick="startFullReplay()">🎬 เล่นซ้ำตั้งแต่รถพยาบาลแทรกไฟ</button>
                <button class="btn-ctrl" id="btnPause" onclick="togglePause()">⏸️ หยุด/เล่นต่อ</button>
            </div>
        </div>

        <div class="canvas-container">
            <canvas id="trafficCanvas" width="1150" height="430"></canvas>
        </div>

        <div class="timeline-bar">
            <div class="phase-steps">
                <div class="phase-pill" id="pill_PREEMPT" onclick="jumpToStage('PREEMPT')">🚑 1. รถพยาบาลแทรกไฟ (Preempt)</div>
                <div class="phase-pill" id="pill_OPT" onclick="jumpToStage('OPT')">🧠 2. ส่งข้อมูลประมวลผล AI</div>
                <div class="phase-pill" id="pill_C1" onclick="jumpToStage('C1')">🟢 3. ฟื้นฟูรอบ C1 (Peak Shaving)</div>
                <div class="phase-pill" id="pill_C2" onclick="jumpToStage('C2')">🟢 4. ฟื้นฟูรอบ C2 (Balance)</div>
                <div class="phase-pill" id="pill_C3" onclick="jumpToStage('C3')">🟢 5. ฟื้นฟูรอบ C3 (Resync)</div>
                <div class="phase-pill" id="pill_NORMAL" onclick="jumpToStage('NORMAL')">⚖️ 6. สภาวะสมดุลปกติ (Normal)</div>
            </div>
        </div>
    </div>

    <script>
    const CFG = __CONFIG_JSON__;
    const canvas = document.getElementById('trafficCanvas');
    const ctx = canvas.getContext('2d');

    const plan = CFG.plan || [8, 5, 3];
    const tp = CFG.tp || 6.0;
    const q0 = CFG.q0 || 5.0;
    const qm = CFG.qm || 30.0;
    const qAcc = CFG.q_accumulated || (q0 + 0.25 * tp);
    const aiCurve = CFG.ai_curve || [qAcc, Math.max(0, qAcc - plan[0]*0.65), 0, 0];
    const convCurve = CFG.conv_curve || [qAcc, qAcc, qAcc, qAcc];

    function buildTimeline() {
        const segs = [];
        let t = 0;
        function addSeg(id, group, dur, mr, my, mg, sr, sy, sg, qStart, qEnd, convQ, lcd0, lcd1, desc) {
            segs.push({
                id, group, start: t, end: t + dur, dur,
                lights: {mr, my, mg, sr, sy, sg},
                qStart, qEnd, convQ, lcd0, lcd1, desc
            });
            t += dur;
        }

        // 1. PREEMPT: รถพยาบาลวิ่งผ่านสายหลัก (tp วินาที) แถวคอยสายรองสะสมจาก q0 -> qAcc
        addSeg('PREEMPT', 'PREEMPT', tp, 0,0,1, 1,0,0, q0, qAcc, qAcc,
               'EMERGENCY WAVE!', 'Main Road Green',
               `รถพยาบาลกำลังวิ่งผ่านสายหลัก (${tp.toFixed(1)}s) | ถนนรองติดไฟแดง รถสะสมเพิ่มจาก ${q0} ➔ ${qAcc.toFixed(1)} คัน`);

        // 2. AI OPTIMIZING: ส่ง MQTT ไป Colab และรับแผนกลับ (1.5 วินาที)
        const optLcd0 = CFG.used_edge_ai ? 'Edge AI Active!' : 'AI Optimizing...';
        const optLcd1 = CFG.used_edge_ai ? `Plan:[${plan.join(',')}]` : `Q:${Math.round(q0)} Flw:${Math.round(qm)}`;
        addSeg('OPT', 'OPT', 1.5, 0,0,1, 1,0,0, qAcc, qAcc, qAcc,
               optLcd0, optLcd1,
               `ส่งค่าผ่าน MQTT ➔ สมองกล AI คำนวณแผนไฟเขียว 3 รอบ: C1=${plan[0]}s, C2=${plan[1]}s, C3=${plan[2]}s`);

        // 3. MULTI_RECOVERY 3 รอบ (C1, C2, C3)
        for (let i = 0; i < 3; i++) {
            const cNum = i + 1;
            const gTime = plan[i];
            const qS = (CFG.cl_active && CFG.actual_q_history.length > i) ? CFG.actual_q_history[i] : aiCurve[i];
            const qE = (CFG.cl_active && CFG.actual_q_history.length > i+1) ? CFG.actual_q_history[i+1] : aiCurve[i+1];
            const cQ = convCurve[i+1];

            if (i > 0 && ((CFG.cl_active && CFG.early_cut && qS === 0) || (!CFG.cl_active && qS <= 0.05))) {
                addSeg('EARLY_CUT', `C${cNum}`, 2.0, 0,0,1, 1,0,0, 0, 0, cQ,
                       'ClosedLoop: Q=0!', 'Early Cut->Sync',
                       `⚡ Closed-Loop Sensor ตรวจพบรถถนนรองระบายหมดแล้ว (Q=0)! ตัดจบอัตโนมัติ ประหยัดเวลา ${CFG.time_saved_sec || (plan[i] + (plan[i+1]||0))} วินาที`);
                break;
            }

            addSeg(`C${cNum}_GRN`, `C${cNum}`, gTime, 1,0,0, 0,0,1, qS, qE, cQ,
                   `Rec C${cNum}/3 Q:{LIVE_Q}`, `Side Grn: {SEC}s`,
                   `รอบที่ ${cNum} (ไฟเขียวถนนรอง ${gTime}s): ระบายแถวคอยจาก ${qS.toFixed(1)} ➔ ${qE.toFixed(1)} คัน (ระบบเดิมเหลือ ${cQ.toFixed(1)} คัน)`);

            addSeg(`C${cNum}_YLW`, `C${cNum}`, 1.0, 1,0,0, 0,1,0, qE, qE, cQ,
                   `Recovery C${cNum}/3`, `Side Yellow 1s`,
                   `รอบที่ ${cNum}: ไฟเหลืองถนนสายรอง (1 วินาที) เตรียมสลับคืนไฟให้สายหลัก`);

            addSeg(`C${cNum}_MAIN`, `C${cNum}`, 3.0, 0,0,1, 1,0,0, qE, qE, cQ,
                   `Recovery C${cNum}/3`, `Balancing Main..`,
                   `รอบที่ ${cNum} (Balancing Main 3s): คืนไฟเขียวให้สายหลัก (${qm} คัน/นาที) ป้องกันรถสายหลักติดสะสม`);

            addSeg(`C${cNum}_MYLW`, `C${cNum}`, 1.0, 0,1,0, 1,0,0, qE, qE, cQ,
                   `Recovery C${cNum}/3`, `Main Yellow 1s`,
                   `รอบที่ ${cNum}: ไฟเหลืองสายหลัก (1 วินาที)`);
        }

        // 4. EQUILIBRIUM DONE (1.5 วินาที)
        const finalQ = aiCurve[3] || 0;
        addSeg('DONE', 'NORMAL', 1.5, 0,0,1, 1,0,0, finalQ, finalQ, convCurve[3],
               'Equilibrium Done', 'Restoring Sync',
               `✅ ฟื้นฟูสมดุลสำเร็จ! ลดความล่าช้าสะสมได้ ${CFG.pct_saved}% กลับสู่วงจรไฟปกติ`);

        return { segs, totalDuration: t };
    }

    const TIMELINE = buildTimeline();
    const RECOVERY_START_TIME = tp + 1.5;

    const storageKey = `sim_state_seq_${CFG.event_seq}`;
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

    const mainCars = [];
    for (let i = 0; i < 7; i++) {
        mainCars.push({
            x: i * 165,
            lane: i % 2,
            speed: 2.2 + (i % 3) * 0.3,
            color: ['#38bdf8', '#facc15', '#a855f7', '#fb923c', '#4ade80'][i % 5]
        });
    }

    let packetPhase = 0;

    function getActiveSegment(elapsedSec) {
        if (simMode === 'NORMAL_LOOP' || elapsedSec >= TIMELINE.totalDuration) {
            const cyc = elapsedSec % 7.0;
            let lights = {mr:0, my:0, mg:1, sr:1, sy:0, sg:0};
            if (cyc >= 3.0 && cyc < 4.0) lights = {mr:0, my:1, mg:0, sr:1, sy:0, sg:0};
            else if (cyc >= 4.0 && cyc < 6.0) lights = {mr:1, my:0, mg:0, sr:0, sy:0, sg:1};
            else if (cyc >= 6.0) lights = {mr:1, my:0, mg:0, sr:0, sy:1, sg:0};

            return {
                id: 'NORMAL', group: 'NORMAL',
                lights,
                liveQ: aiCurve[3] || 0,
                convQ: convCurve[3] || 0,
                secLeft: cyc < 3 ? Math.ceil(3 - cyc) : (cyc >= 4 && cyc < 6 ? Math.ceil(6 - cyc) : 1),
                lcd0: 'State: NORMAL',
                lcd1: 'Coordinated Flow',
                desc: CFG.has_event
                    ? 'เข้าสู่สภาวะสมดุลปกติ (Coordinated Flow) — กดปุ่ม "🎬 เล่นซ้ำตั้งแต่รถพยาบาลแทรกไฟ" ด้านบนเพื่อดูลำดับเหตุการณ์ซ้ำได้'
                    : 'กำลังรันวงจรไฟจราจรปกติ (Normal Fixed Cycle) — กดปุ่มแดงบน Wokwi หรือกดปุ่ม "🎬 เล่นซ้ำ" เพื่อจำลองเหตุรถฉุกเฉิน',
                ratio: 1.0
            };
        }

        const seg = TIMELINE.segs.find(s => elapsedSec >= s.start && elapsedSec < s.end) || TIMELINE.segs[TIMELINE.segs.length - 1];
        const localT = elapsedSec - seg.start;
        const ratio = Math.min(1.0, Math.max(0.0, localT / seg.dur));
        const liveQ = seg.qStart + (seg.qEnd - seg.qStart) * ratio;
        const secLeft = Math.max(1, Math.ceil(seg.dur - localT));

        const lcd0 = seg.lcd0.replace('{LIVE_Q}', String(Math.round(liveQ)).padStart(2, ' '));
        const lcd1 = seg.lcd1.replace('{SEC}', String(secLeft).padStart(2, ' '));

        return {
            id: seg.id,
            group: seg.group,
            lights: seg.lights,
            liveQ,
            convQ: seg.convQ,
            secLeft,
            lcd0,
            lcd1,
            desc: seg.desc,
            ratio
        };
    }

    function drawRoundRect(x, y, w, h, r, fill, stroke, lineW=1.5) {
        ctx.beginPath();
        ctx.roundRect(x, y, w, h, r);
        if (fill) { ctx.fillStyle = fill; ctx.fill(); }
        if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = lineW; ctx.stroke(); }
    }

    function drawVehicle(x, y, w, h, color, isVertical=false, isAmbulance=false) {
        ctx.save();
        drawRoundRect(x, y, w, h, 5, color, '#0f172a', 1.5);
        ctx.fillStyle = '#1e293b';
        if (!isVertical) {
            ctx.fillRect(x + w*0.62, y + 3, w*0.22, h - 6);
            ctx.fillRect(x + w*0.15, y + 3, w*0.18, h - 6);
        } else {
            ctx.fillRect(x + 3, y + h*0.15, w - 6, h*0.22);
            ctx.fillRect(x + 3, y + h*0.65, w - 6, h*0.18);
        }
        if (isAmbulance) {
            ctx.fillStyle = '#ef4444';
            ctx.fillRect(x + w*0.32, y + h*0.25, w*0.12, h*0.5);
            ctx.fillRect(x + w*0.20, y + h*0.38, w*0.36, h*0.24);
            const flash = Math.floor(Date.now() / 120) % 2 === 0;
            ctx.beginPath();
            ctx.arc(x + w*0.75, y + h*0.3, 4, 0, Math.PI*2);
            ctx.fillStyle = flash ? '#ef4444' : '#3b82f6';
            ctx.fill();
            ctx.beginPath();
            ctx.arc(x + w*0.75, y + h*0.7, 4, 0, Math.PI*2);
            ctx.fillStyle = flash ? '#3b82f6' : '#ef4444';
            ctx.fill();
        }
        ctx.restore();
    }

    function drawTrafficLight(x, y, label, rOn, yOn, gOn, timerText) {
        drawRoundRect(x, y, 46, 102, 8, '#0f172a', '#475569', 2);
        ctx.beginPath(); ctx.arc(x + 23, y + 20, 10, 0, Math.PI*2);
        ctx.fillStyle = rOn ? '#ff3b3b' : '#331a1a';
        ctx.shadowBlur = rOn ? 14 : 0; ctx.shadowColor = '#ff3b3b';
        ctx.fill(); ctx.shadowBlur = 0;

        ctx.beginPath(); ctx.arc(x + 23, y + 46, 10, 0, Math.PI*2);
        ctx.fillStyle = yOn ? '#facc15' : '#332b14';
        ctx.shadowBlur = yOn ? 14 : 0; ctx.shadowColor = '#facc15';
        ctx.fill(); ctx.shadowBlur = 0;

        ctx.beginPath(); ctx.arc(x + 23, y + 72, 10, 0, Math.PI*2);
        ctx.fillStyle = gOn ? '#00e676' : '#123123';
        ctx.shadowBlur = gOn ? 14 : 0; ctx.shadowColor = '#00e676';
        ctx.fill(); ctx.shadowBlur = 0;

        ctx.fillStyle = '#e2e8f0';
        ctx.font = 'bold 11px "Share Tech Mono", monospace';
        ctx.textAlign = 'center';
        ctx.fillText(timerText, x + 23, y + 95);

        drawRoundRect(x - 18, y - 22, 82, 18, 4, 'rgba(15,23,42,0.85)', '#38bdf8', 1);
        ctx.fillStyle = '#38bdf8';
        ctx.font = '500 10px "Prompt", sans-serif';
        ctx.fillText(label, x + 23, y - 9);
    }

    function renderLoop() {
        const now = Date.now();
        const elapsedSec = paused ? pausedSimSec : (now - startEpochMs) / 1000.0;
        const st = getActiveSegment(elapsedSec);
        packetPhase = (packetPhase + 0.025) % 1.0;

        const badge = document.getElementById('modeBadge');
        if (st.group === 'PREEMPT') {
            badge.textContent = '🚑 EMERGENCY PREEMPTION (กักไฟรถฉุกเฉิน)';
            badge.style.borderColor = '#ff4b4b'; badge.style.color = '#ff4b4b';
        } else if (st.group === 'OPT') {
            badge.textContent = '🧠 CLOUD AI OPTIMIZING (คำนวณแผนฟื้นฟู)';
            badge.style.borderColor = '#facc15'; badge.style.color = '#facc15';
        } else if (['C1', 'C2', 'C3'].includes(st.group)) {
            badge.textContent = `🟢 MULTI-CYCLE RECOVERY (${st.group} | แผน [${plan.join('s, ')}s])`;
            badge.style.borderColor = '#00e676'; badge.style.color = '#00e676';
        } else {
            badge.textContent = '⚖️ COORDINATED NORMAL FLOW (สภาวะสมดุลปกติ)';
            badge.style.borderColor = '#00d4ff'; badge.style.color = '#00d4ff';
        }

        ['PREEMPT', 'OPT', 'C1', 'C2', 'C3', 'NORMAL'].forEach(g => {
            const el = document.getElementById('pill_' + g);
            if (!el) return;
            el.className = 'phase-pill';
            if (st.group === g) {
                el.classList.add(g === 'PREEMPT' ? 'preempt-active' : 'current');
            }
        });

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#141d2b';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.strokeStyle = 'rgba(46, 64, 87, 0.35)';
        ctx.lineWidth = 1;
        for (let gx = 0; gx < canvas.width; gx += 40) {
            ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, canvas.height); ctx.stroke();
        }
        for (let gy = 0; gy < canvas.height; gy += 40) {
            ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(canvas.width, gy); ctx.stroke();
        }

        const roadMainY = 145;
        const roadMainH = 96;
        const roadSideX = 435;
        const roadSideW = 96;

        ctx.fillStyle = '#283242';
        ctx.fillRect(0, roadMainY, canvas.width, roadMainH);
        ctx.fillRect(roadSideX, 0, roadSideW, canvas.height);

        ctx.strokeStyle = '#f59e0b';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(0, roadMainY); ctx.lineTo(roadSideX, roadMainY);
        ctx.moveTo(roadSideX + roadSideW, roadMainY); ctx.lineTo(canvas.width, roadMainY);
        ctx.moveTo(0, roadMainY + roadMainH); ctx.lineTo(roadSideX, roadMainY + roadMainH);
        ctx.moveTo(roadSideX + roadSideW, roadMainY + roadMainH); ctx.lineTo(canvas.width, roadMainY + roadMainH);
        ctx.moveTo(roadSideX, 0); ctx.lineTo(roadSideX, roadMainY);
        ctx.moveTo(roadSideX + roadSideW, 0); ctx.lineTo(roadSideX + roadSideW, roadMainY);
        ctx.moveTo(roadSideX, roadMainY + roadMainH); ctx.lineTo(roadSideX, canvas.height);
        ctx.moveTo(roadSideX + roadSideW, roadMainY + roadMainH); ctx.lineTo(roadSideX + roadSideW, canvas.height);
        ctx.stroke();

        ctx.strokeStyle = '#cbd5e1';
        ctx.lineWidth = 2;
        ctx.setLineDash([14, 12]);
        ctx.beginPath();
        ctx.moveTo(0, roadMainY + roadMainH/2); ctx.lineTo(roadSideX - 15, roadMainY + roadMainH/2);
        ctx.moveTo(roadSideX + roadSideW + 15, roadMainY + roadMainH/2); ctx.lineTo(canvas.width, roadMainY + roadMainH/2);
        ctx.moveTo(roadSideX + roadSideW/2, 0); ctx.lineTo(roadSideX + roadSideW/2, roadMainY - 15);
        ctx.moveTo(roadSideX + roadSideW/2, roadMainY + roadMainH + 15); ctx.lineTo(roadSideX + roadSideW/2, canvas.height);
        ctx.stroke();
        ctx.setLineDash([]);

        ctx.fillStyle = 'rgba(255,255,255,0.75)';
        for (let i = 6; i < roadMainH - 6; i += 14) {
            ctx.fillRect(roadSideX - 18, roadMainY + i, 12, 7);
            ctx.fillRect(roadSideX + roadSideW + 6, roadMainY + i, 12, 7);
        }
        for (let i = 6; i < roadSideW - 6; i += 14) {
            ctx.fillRect(roadSideX + i, roadMainY - 18, 7, 12);
            ctx.fillRect(roadSideX + i, roadMainY + roadMainH + 6, 7, 12);
        }

        ctx.fillStyle = 'rgba(255,255,255,0.45)';
        ctx.font = '600 12px "Prompt", sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText(`MAIN ROAD (สายหลัก: ${qm.toFixed(0)} คัน/นาที)`, 18, roadMainY + 20);
        ctx.save();
        ctx.translate(roadSideX + 20, canvas.height - 15);
        ctx.rotate(-Math.PI/2);
        ctx.fillText('SIDE ROAD (ถนนสายรอง)', 0, 0);
        ctx.restore();

        const mainFlowFactor = (qm / 30.0);
        const mainCanGo = (st.lights.mg === 1 || st.lights.my === 1);
        mainCars.forEach(car => {
            if (car.lane === 0) {
                const stopX = roadSideX - 58;
                const nearStop = (car.x > stopX - 45 && car.x <= stopX);
                if (mainCanGo || !nearStop) {
                    car.x += car.speed * Math.max(0.6, mainFlowFactor);
                }
                if (car.x > canvas.width + 50) car.x = -60;
                drawVehicle(car.x, roadMainY + 12, 38, 22, car.color, false, false);
            } else {
                const stopX = roadSideX + roadSideW + 22;
                const nearStop = (car.x >= stopX && car.x < stopX + 45);
                if (mainCanGo || !nearStop) {
                    car.x -= car.speed * Math.max(0.6, mainFlowFactor);
                }
                if (car.x < -60) car.x = canvas.width + 50;
                drawVehicle(car.x, roadMainY + 60, 38, 22, car.color, false, false);
            }
        });

        if (st.group === 'PREEMPT') {
            const ambX = -60 + (canvas.width + 120) * st.ratio;
            const grad = ctx.createLinearGradient(ambX - 40, 0, ambX + 90, 0);
            grad.addColorStop(0, 'rgba(239, 68, 68, 0)');
            grad.addColorStop(0.5, 'rgba(239, 68, 68, 0.28)');
            grad.addColorStop(1, 'rgba(59, 130, 246, 0)');
            ctx.fillStyle = grad;
            ctx.fillRect(0, roadMainY, canvas.width, roadMainH/2);

            drawVehicle(ambX, roadMainY + 10, 48, 26, '#ffffff', false, true);
        }

        const visibleCars = Math.min(12, Math.ceil(st.liveQ));
        const sideGreenActive = (st.lights.sg === 1);
        const scrollOffset = sideGreenActive ? ((now / 18) % 28) : 0;

        if (sideGreenActive && st.liveQ > 0) {
            const passY = (roadMainY + roadMainH - 10) - ((now / 6) % 160);
            drawVehicle(roadSideX + 14, passY, 22, 34, '#00e676', true, false);
        }

        for (let idx = 0; idx < visibleCars; idx++) {
            const carY = (roadMainY + roadMainH + 22) + (idx * 26) - (sideGreenActive ? scrollOffset * 0.45 : 0);
            if (carY < canvas.height - 10) {
                const cColor = idx === 0 ? '#38bdf8' : (idx < 4 ? '#f97316' : '#ef4444');
                drawVehicle(roadSideX + 14, carY, 22, 22, cColor, true, false);
            }
        }

        const sensorX = roadSideX - 75;
        const sensorY = roadMainY + roadMainH + 55;
        drawRoundRect(sensorX - 55, sensorY - 18, 110, 42, 8, '#0f172a', CFG.sensor_fault ? '#ef4444' : '#00d4ff', 2);
        ctx.fillStyle = CFG.sensor_fault ? '#ef4444' : '#00d4ff';
        ctx.font = '600 11px "Prompt", sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('📡 HC-SR04 Sensor', sensorX, sensorY - 2);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 12px "Share Tech Mono", monospace';
        ctx.fillText(CFG.sensor_fault ? 'FAULT (Est: 8)' : `Queue: ${st.liveQ.toFixed(1)} คัน`, sensorX, sensorY + 15);

        for (let w = 1; w <= 3; w++) {
            const r = ((now / 25) + w * 16) % 52;
            ctx.beginPath();
            ctx.arc(sensorX + 55, sensorY + 4, r, -0.45, 0.45);
            ctx.strokeStyle = CFG.sensor_fault ? `rgba(239,68,68,${1 - r/52})` : `rgba(0,212,255,${1 - r/52})`;
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        drawTrafficLight(roadSideX - 70, roadMainY - 115, 'MAIN ROAD (สายหลัก)',
                         st.lights.mr, st.lights.my, st.lights.mg,
                         st.lights.mg ? 'GO' : (st.lights.my ? '1s' : `${st.secLeft}s`));

        drawTrafficLight(roadSideX + roadSideW + 24, roadMainY + roadMainH + 22, 'SIDE ROAD (สายรอง)',
                         st.lights.sr, st.lights.sy, st.lights.sg,
                         st.lights.sg ? `${st.secLeft}s` : (st.lights.sy ? '1s' : 'WAIT'));

        drawRoundRect(25, 16, 265, 68, 12, 'rgba(15, 23, 42, 0.92)', '#38bdf8', 2);
        ctx.fillStyle = '#38bdf8';
        ctx.font = '600 12px "Prompt", sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('☁️ Cloud AI & MQTT Platform (Colab)', 38, 36);
        ctx.fillStyle = '#cbd5e1';
        ctx.font = '400 11px "Prompt", sans-serif';
        ctx.fillText(`Model: Multi-Output RF (R² = ${CFG.r2_score})`, 38, 54);
        ctx.fillStyle = '#00e676';
        ctx.fillText(`Recovery Plan: C1=${plan[0]}s | C2=${plan[1]}s | C3=${plan[2]}s`, 38, 72);

        ctx.strokeStyle = 'rgba(0, 212, 255, 0.45)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        ctx.moveTo(sensorX, sensorY - 18);
        ctx.lineTo(140, 280);
        ctx.lineTo(140, 84);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(290, 50);
        ctx.lineTo(roadSideX - 47, 50);
        ctx.lineTo(roadSideX - 47, roadMainY - 115);
        ctx.stroke();
        ctx.setLineDash([]);

        const pktY = 280 - (packetPhase * 196);
        ctx.beginPath(); ctx.arc(140, pktY, 4, 0, Math.PI*2);
        ctx.fillStyle = '#00e676'; ctx.fill();
        const pktX = 290 + (packetPhase * (roadSideX - 47 - 290));
        ctx.beginPath(); ctx.arc(pktX, 50, 4, 0, Math.PI*2);
        ctx.fillStyle = '#00d4ff'; ctx.fill();

        const lcdX = canvas.width - 285, lcdY = 16;
        drawRoundRect(lcdX, lcdY, 265, 76, 10, '#0f291e', '#10b981', 2);
        ctx.fillStyle = '#10b981';
        ctx.font = '600 10px "Prompt", sans-serif';
        ctx.textAlign = 'left';
        ctx.fillText('📟 Wokwi ESP32 LCD1602 (I2C 0x27)', lcdX + 12, lcdY + 18);

        drawRoundRect(lcdX + 10, lcdY + 24, 245, 42, 4, '#84cc16', '#3f6212', 1.5);
        ctx.fillStyle = '#0f172a';
        ctx.font = 'bold 14px "Share Tech Mono", monospace';
        ctx.fillText(st.lcd0.padEnd(16, ' ').substring(0, 16), lcdX + 20, lcdY + 42);
        ctx.fillText(st.lcd1.padEnd(16, ' ').substring(0, 16), lcdX + 20, lcdY + 59);

        const cmpX = canvas.width - 335, cmpY = roadMainY + roadMainH + 18;
        drawRoundRect(cmpX, cmpY, 315, 118, 10, 'rgba(15, 23, 42, 0.92)', '#334155', 1.5);
        ctx.fillStyle = '#ffffff';
        ctx.font = '600 12px "Prompt", sans-serif';
        ctx.fillText('📊 เปรียบเทียบแถวคอยถนนสายรอง (Real-Time)', cmpX + 14, cmpY + 22);

        ctx.fillStyle = '#00d4ff';
        ctx.font = '500 11px "Prompt", sans-serif';
        ctx.fillText(`ระบบ AI ฟื้นฟู 3 รอบ: ${st.liveQ.toFixed(1)} คัน`, cmpX + 14, cmpY + 46);
        drawRoundRect(cmpX + 14, cmpY + 52, 285, 10, 5, '#1e293b', null);
        drawRoundRect(cmpX + 14, cmpY + 52, Math.min(285, (st.liveQ / 20.0) * 285), 10, 5, '#00d4ff', null);

        ctx.fillStyle = '#ff4b4b';
        ctx.fillText(`ระบบไฟปกติ (เขียว 2s/รอบ): ${st.convQ.toFixed(1)} คัน`, cmpX + 14, cmpY + 82);
        drawRoundRect(cmpX + 14, cmpY + 88, 285, 10, 5, '#1e293b', null);
        drawRoundRect(cmpX + 14, cmpY + 88, Math.min(285, (st.convQ / 20.0) * 285), 10, 5, '#ff4b4b', null);

        drawRoundRect(20, canvas.height - 50, cmpX - 35, 38, 8, 'rgba(15, 23, 42, 0.92)', '#00d4ff', 1.5);
        ctx.fillStyle = '#e2e8f0';
        ctx.font = '500 12px "Prompt", sans-serif';
        ctx.fillText(`💡 สถานะปัจจุบัน: ${st.desc}`, 32, canvas.height - 26);

        requestAnimationFrame(renderLoop);
    }

    requestAnimationFrame(renderLoop);
    </script>
    </body>
    </html>
    """
    return html_template.replace("__CONFIG_JSON__", config_json)


# ---------------------------------------------------------------------------
# 7. แถบเมนูด้านซ้าย (Sidebar - นาฬิกาเวลาไทย UTC+7)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⏰ เวลาประเทศไทย (UTC+7)")
    current_th_time_live = datetime.now(TH_TIMEZONE).strftime("%H:%M:%S")
    st.markdown(
        f"<h1 style='text-align: center; color: #00d4ff; background: #161b26; padding: 10px; border-radius: 10px; border: 1px solid #2e3b52; margin: 0;'>{current_th_time_live}</h1>",
        unsafe_allow_html=True
    )
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
# 8. แบนเนอร์หัวข้อหลัก (Main Header Banner)
# ---------------------------------------------------------------------------
st.markdown("""
<div class="main-banner">
    <h1>🚦 แบบจำลองระบบควบคุมและปรับสมดุลแถวคอยจราจรอัจฉริยะหลังการแทรกสัญญาณไฟของรถฉุกเฉิน</h1>
    <p>Intelligent Queue Rebalancing and Traffic Control System Simulation Post-Emergency Vehicle Preemption</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 9. แสดงผล Digital Twin Traffic Animation
# ---------------------------------------------------------------------------
anim_html = build_traffic_animation_html(
    store["ai_data"],
    store["closed_loop_data"],
    store["event_seq"]
)
components.html(anim_html, height=545, scrolling=False)

# ---------------------------------------------------------------------------
# 10. ส่วนแสดงผลกราฟและตารางวิเคราะห์ (Main Dashboard Content)
# ---------------------------------------------------------------------------
if store["ai_data"] is None:
    st.info("💡 **ระบบพร้อมรับข้อมูลแล้ว!** กดปุ่มสีแดง (`btn_emg`) ในวงจร Wokwi เพื่อส่งข้อมูลจริงมาที่หน้าเว็บ หรือกดปุ่ม **'🎬 เล่นซ้ำตั้งแต่รถพยาบาลแทรกไฟ'** บนกรอบ Animation ด้านบนเพื่อดูตัวอย่างจำลองได้เลย")
else:
    data = store["ai_data"]
    phys = data["physics"]
    plan = data["plan"]
    cl_data = store["closed_loop_data"]

    if data.get("sensor_fault"):
        st.error("⚠️ **แจ้งเตือนฮาร์ดแวร์:** ตรวจพบความผิดปกติของเซนเซอร์ Ultrasonic (`HC-SR04`) ระบบสลับไปใช้ค่าสถิติสำรองอัตโนมัติ (8 คัน)")

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
