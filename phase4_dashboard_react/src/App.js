// v2.0.1
import { useState, useEffect, useRef, useCallback } from "react";
import {
  LineChart, Line, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid,
} from "recharts";

function Sparkline({ data, color }) {
  if (!data || data.length < 2) return null;
  const vals = data.map(d => d.v);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = (max - min) || (max * 0.1) || 1;
  const W = 300, H = 48, px = 6, py = 8;
  const x = (i) => px + (i / (vals.length - 1)) * (W - px * 2);
  const y = (v) => py + (1 - (v - min) / range) * (H - py * 2);
  const pts = vals.map((v, i) => x(i) + "," + y(v)).join(" ");
  const lx = x(vals.length - 1);
  const ly = y(vals[vals.length - 1]);
  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{display:"block",overflow:"visible"}}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2.5"
        strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx={lx} cy={ly} r="4" fill={color}/>
    </svg>
  );
}

// ── Config ─────────────────────────────────────────────────────────────────
const API = "https://9yxcjs8frj.execute-api.us-east-1.amazonaws.com/prod";

// ── Design tokens ──────────────────────────────────────────────────────────
const T = {
  bg:    "#090c10",
  bg2:   "#0f1318",
  bg3:   "#161b22",
  border:"rgba(255,255,255,0.07)",
  border2:"rgba(255,255,255,0.13)",
  gold:  "#c9a84c",
  gold2: "#e8c97a",
  green: "#2dd4a0",
  red:   "#f05252",
  amber: "#f59e0b",
  blue:  "#60a5fa",
  text:  "#e8eaf0",
  text2: "#8b92a0",
  text3: "#4a5260",
};

// ── KPI data ───────────────────────────────────────────────────────────────
const KPI_DATA = [
  { id:"nim",        label:"Net Interest Margin", value:"3.24%", change:-18, dir:"down", status:"amber", target:"3.50%", unit:"%" },
  { id:"npl_ratio",  label:"NPL Ratio",           value:"1.82%", change:-5,  dir:"up",   status:"green", target:"≤2.00%", unit:"%" },
  { id:"casa_ratio", label:"CASA Ratio",           value:"47.3%", change:+32, dir:"up",   status:"green", target:"≥45.0%", unit:"%" },
  { id:"roe_roa",    label:"Return on Equity",     value:"14.8%", change:0,   dir:"flat", status:"green", target:"≥15.0%", unit:"%" },
  { id:"cost_income",label:"Cost-to-Income",       value:"52.1%", change:+85, dir:"down", status:"amber", target:"≤45.0%", unit:"%" },
  { id:"lcr_nsfr",   label:"LCR",                  value:"108.4%",change:-215,dir:"down", status:"red",   target:"≥100%",  unit:"%" },
];

const TREND_DATA = {
  nim:         [{d:"W-4",v:4.1},{d:"W-3",v:3.9},{d:"W-2",v:3.7},{d:"W-1",v:3.5},{d:"Now",v:3.24}],
  npl_ratio:   [{d:"W-4",v:2.8},{d:"W-3",v:2.5},{d:"W-2",v:2.3},{d:"W-1",v:2.0},{d:"Now",v:1.82}],
  casa_ratio:  [{d:"W-4",v:41.0},{d:"W-3",v:43.2},{d:"W-2",v:44.8},{d:"W-1",v:46.1},{d:"Now",v:47.3}],
  roe_roa:     [{d:"W-4",v:11.2},{d:"W-3",v:12.5},{d:"W-2",v:13.1},{d:"W-1",v:14.0},{d:"Now",v:14.8}],
  cost_income: [{d:"W-4",v:46.0},{d:"W-3",v:48.5},{d:"W-2",v:50.0},{d:"W-1",v:51.3},{d:"Now",v:52.1}],
  lcr_nsfr:    [{d:"W-4",v:155.0},{d:"W-3",v:142.0},{d:"W-2",v:130.0},{d:"W-1",v:118.0},{d:"Now",v:108.4}],
};

const HISTORY = [
  { id:"sess-001", date:"Today 03:14 UTC", trigger:"Scheduled", headline:"Further investigation required on key banking KPIs", risk:"medium", pdf:"NIM-investigation-1" },
  { id:"sess-002", date:"Yesterday 16:41", trigger:"Anomaly",   headline:"NIM compressed 18 bps — funding cost pressure identified", risk:"high", pdf:"daily-kpi-investigation-2023-04-15" },
  { id:"sess-003", date:"Apr 06 09:00",    trigger:"Scheduled", headline:"All KPIs within acceptable ranges. LCR watch continues.", risk:"low", pdf:"daily-kpi-investigation-apr06" },
];

// ── Helpers ────────────────────────────────────────────────────────────────
const statusColor = s => ({ green: T.green, amber: T.amber, red: T.red }[s] || T.text2);
const riskColor   = r => ({ low: T.green, medium: T.amber, high: T.red }[r] || T.text2);

// ── Styles ─────────────────────────────────────────────────────────────────
const S = {
  topbar: {
    height: 60, background: "rgba(9,12,16,0.97)", borderBottom: `1px solid ${T.border}`,
    display:"flex", alignItems:"center", justifyContent:"space-between",
    padding:"0 28px", position:"sticky", top:0, zIndex:100,
    backdropFilter:"blur(12px)", flexShrink:0,
  },
  layout: {
    flex:1, display:"grid", gridTemplateColumns:"220px 1fr 340px",
    overflow:"hidden",
  },
  sidebar: {
    background: T.bg2, borderRight:`1px solid ${T.border}`,
    overflowY:"auto", padding:"20px 0",
    display:"flex", flexDirection:"column", gap:0,
  },
  main: {
    overflowY:"auto", padding:"28px 32px",
    background: `linear-gradient(180deg, ${T.bg} 0%, ${T.bg} 100%)`,
  },
  chatPanel: {
    background: T.bg2, borderLeft:`1px solid ${T.border}`,
    display:"flex", flexDirection:"column", overflow:"hidden",
  },
};

// ── Sub-components ─────────────────────────────────────────────────────────

function Logo() {
  return (
    <div style={{display:"flex",alignItems:"center",gap:10}}>
      <div style={{
        width:32, height:32, background:`linear-gradient(135deg,${T.gold},${T.gold2})`,
        borderRadius:8, display:"flex", alignItems:"center", justifyContent:"center",
        fontFamily:"'DM Serif Display',serif", fontSize:16, color:T.bg, fontWeight:700,
      }}>A</div>
      <div>
        <div style={{fontFamily:"'DM Serif Display',serif", fontSize:17, color:T.text}}>Apex Bank</div>
        <div style={{fontSize:9, color:T.gold, letterSpacing:2, textTransform:"uppercase", fontWeight:600}}>BI Copilot</div>
      </div>
    </div>
  );
}

function NavItem({ icon, label, active, onClick }) {
  return (
    <div onClick={onClick} style={{
      display:"flex", alignItems:"center", gap:9,
      padding:"9px 14px", margin:"0 10px 2px", borderRadius:8,
      fontSize:13, cursor:"pointer",
      color: active ? T.gold : T.text2,
      background: active ? "rgba(201,168,76,0.12)" : "transparent",
      transition:"all 0.15s",
    }}>
      <span style={{fontSize:14, width:18, textAlign:"center"}}>{icon}</span>
      {label}
    </div>
  );
}

function KpiPill({ kpi }) {
  const color = statusColor(kpi.status);
  return (
    <div style={{
      display:"flex", alignItems:"center", justifyContent:"space-between",
      padding:"7px 16px", cursor:"pointer",
    }}>
      <span style={{fontSize:11, fontFamily:"'DM Mono',monospace", color:T.text2}}>{kpi.label.replace(" Ratio","").replace("Net Interest ","")}</span>
      <span style={{
        fontSize:10, fontFamily:"'DM Mono',monospace",
        padding:"2px 7px", borderRadius:4, color,
        background: color + "18",
      }}>{kpi.value}</span>
    </div>
  );
}

function KpiCard({ kpi, onClick }) {
  const color = statusColor(kpi.status);
  const changeSign = kpi.change > 0 ? "▲" : kpi.change < 0 ? "▼" : "→";
  const changeColor = kpi.dir === "up" ? T.green : kpi.dir === "down" ? T.red : T.text3;
  const data = TREND_DATA[kpi.id] || [];

  return (
    <div onClick={onClick} style={{
      background: T.bg2, border:`1px solid ${T.border}`,
      borderRadius:12, padding:18, cursor:"pointer",
      position:"relative", overflow:"hidden",
      transition:"border-color 0.2s",
    }}>
      <div style={{
        position:"absolute", top:0, left:0, right:0, height:2,
        background: color,
      }}/>
      <div style={{fontSize:10, letterSpacing:"1.5px", textTransform:"uppercase", color:T.text3, marginBottom:10, fontWeight:600}}>
        {kpi.label}
      </div>
      <div style={{fontFamily:"'DM Serif Display',serif", fontSize:28, color:T.text, letterSpacing:"-0.5px", marginBottom:6}}>
        {kpi.value}
      </div>
      <div style={{display:"flex", justifyContent:"space-between", alignItems:"center"}}>
        <span style={{fontSize:11, fontFamily:"'DM Mono',monospace", color:changeColor}}>
          {changeSign} {Math.abs(kpi.change)} bps WoW
        </span>
        <span style={{fontSize:10, color:T.text3, fontFamily:"'DM Mono',monospace"}}>
          Target {kpi.target}
        </span>
      </div>
      {data.length > 0 && (
        <div style={{marginTop:10}}>
          <Sparkline data={data} color={color}/>
        </div>
      )}
    </div>
  );
}

function AlertBanner({ alerts }) {
  return (
    <div style={{marginBottom:24}}>
      <div style={{fontSize:12, color:T.text2, marginBottom:8, display:"flex", alignItems:"center", gap:8}}>
        ⚠ Active Alerts
        <span style={{background:"rgba(240,82,82,0.15)", color:T.red, fontSize:10, fontFamily:"'DM Mono',monospace", padding:"1px 6px", borderRadius:4}}>
          {alerts.length}
        </span>
      </div>
      {alerts.map((a, i) => (
        <div key={i} style={{
          background: T.bg2, border:`1px solid ${T.border}`,
          borderLeft:`3px solid ${a.severity === "critical" ? T.red : T.amber}`,
          borderRadius:8, padding:"11px 14px", marginBottom:6,
          fontSize:12, color:T.text, display:"flex", justifyContent:"space-between", alignItems:"center",
        }}>
          <span>{a.text}</span>
          <span style={{fontSize:10, color:T.text3, fontFamily:"'DM Mono',monospace", flexShrink:0, marginLeft:12}}>{a.time}</span>
        </div>
      ))}
    </div>
  );
}

// ── Dashboard page ─────────────────────────────────────────────────────────
function DashboardPage({ onInvestigate, loading }) {
  const [selectedKpi, setSelectedKpi] = useState(null);
  const alerts = [
    { text:"NIM compressed −18 bps WoW — funding cost increase detected in Corporate segment", time:"2h ago", severity:"warning" },
    { text:"LCR headroom at 8.4% — approaching regulatory minimum threshold", time:"5h ago", severity:"critical" },
  ];

  return (
    <div>
      <div style={{marginBottom:24}}>
        <div style={{fontFamily:"'DM Serif Display',serif", fontSize:26, letterSpacing:"-0.5px", marginBottom:4}}>KPI Dashboard</div>
        <div style={{fontSize:13, color:T.text2}}>Real-time banking performance · Updated daily 03:00 UTC</div>
      </div>

      <div style={{
        background:T.bg2, border:`1px solid ${T.border}`, borderRadius:12,
        padding:"18px 22px", display:"flex", alignItems:"center",
        justifyContent:"space-between", marginBottom:24,
      }}>
        <div>
          <div style={{fontSize:14, fontWeight:600, marginBottom:3}}>Daily Investigation Ready</div>
          <div style={{fontSize:12, color:T.text2}}>Last run: Today 03:14 UTC · Next: Tomorrow 03:00 UTC</div>
        </div>
        <button onClick={onInvestigate} disabled={loading} style={{
          background:`linear-gradient(135deg,${T.gold},${T.gold2})`,
          color:T.bg, border:"none", padding:"10px 20px", borderRadius:8,
          fontSize:13, fontWeight:600, cursor:loading?"not-allowed":"pointer",
          opacity: loading ? 0.6 : 1, fontFamily:"'Instrument Sans',sans-serif",
        }}>
          {loading ? "Running..." : "Investigate Now"}
        </button>
      </div>

      <AlertBanner alerts={alerts}/>

      <div style={{display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:14}}>
        {KPI_DATA.map(kpi => (
          <KpiCard key={kpi.id} kpi={kpi} onClick={() => setSelectedKpi(kpi)}/>
        ))}
      </div>

      {selectedKpi && (
        <div style={{
          position:"fixed", inset:0, background:"rgba(0,0,0,0.7)",
          display:"flex", alignItems:"center", justifyContent:"center", zIndex:200,
        }} onClick={() => setSelectedKpi(null)}>
          <div onClick={e => e.stopPropagation()} style={{
            background:T.bg2, border:`1px solid ${T.border2}`, borderRadius:16,
            padding:28, width:480, maxWidth:"90vw",
          }}>
            <div style={{display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:20}}>
              <div>
                <div style={{fontSize:11, letterSpacing:"1.5px", textTransform:"uppercase", color:T.text3, marginBottom:6, fontWeight:600}}>
                  {selectedKpi.label}
                </div>
                <div style={{fontFamily:"'DM Serif Display',serif", fontSize:40, letterSpacing:"-1px"}}>
                  {selectedKpi.value}
                </div>
              </div>
              <button onClick={() => setSelectedKpi(null)} style={{background:"none", border:"none", color:T.text2, fontSize:20, cursor:"pointer"}}>×</button>
            </div>
            <div style={{height:140}}>
              <ResponsiveContainer width="100%" height={140}>
                <LineChart data={TREND_DATA[selectedKpi.id] || []} margin={{top:5,right:10,left:0,bottom:5}}>
                  <CartesianGrid stroke={T.border} strokeDasharray="3 3"/>
                  <XAxis dataKey="d" tick={{fill:T.text3, fontSize:11}} axisLine={false} tickLine={false}/>
                  <YAxis tick={{fill:T.text3, fontSize:11}} axisLine={false} tickLine={false} width={40}/>
                  <Tooltip contentStyle={{background:T.bg3, border:`1px solid ${T.border2}`, borderRadius:8, fontSize:12}}
                    labelStyle={{color:T.text2}} itemStyle={{color:statusColor(selectedKpi.status)}}/>
                  <Line type="monotone" dataKey="v" stroke={statusColor(selectedKpi.status)} strokeWidth={2} dot={{r:3, fill:statusColor(selectedKpi.status)}}/>
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:12, marginTop:16}}>
              {[
                ["Target",`${selectedKpi.target}`],
                ["WoW Change",`${selectedKpi.change > 0 ? "+" : ""}${selectedKpi.change} bps`],
                ["Status", selectedKpi.status.toUpperCase()],
                ["Definition","Governed metric"],
              ].map(([k,v]) => (
                <div key={k} style={{background:T.bg3, borderRadius:8, padding:"12px 14px"}}>
                  <div style={{fontSize:10, color:T.text3, marginBottom:4, textTransform:"uppercase", letterSpacing:"1px"}}>{k}</div>
                  <div style={{fontSize:14, fontWeight:500}}>{v}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── History page ───────────────────────────────────────────────────────────
function HistoryPage() {
  return (
    <div>
      <div style={{marginBottom:24}}>
        <div style={{fontFamily:"'DM Serif Display',serif", fontSize:26, letterSpacing:"-0.5px", marginBottom:4}}>Investigation History</div>
        <div style={{fontSize:13, color:T.text2}}>All agent-led KPI investigations and their findings</div>
      </div>
      <div style={{background:T.bg2, border:`1px solid ${T.border}`, borderRadius:12, overflow:"hidden"}}>
        <table style={{width:"100%", borderCollapse:"collapse"}}>
          <thead>
            <tr style={{borderBottom:`1px solid ${T.border}`}}>
              {["Date","Trigger","Headline","Risk","Report"].map(h => (
                <th key={h} style={{textAlign:"left", fontSize:10, letterSpacing:"1px", textTransform:"uppercase", color:T.text3, padding:"12px 16px", fontWeight:600}}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {HISTORY.map(row => (
              <tr key={row.id} style={{borderBottom:`1px solid ${T.border}`}}>
                <td style={{padding:"14px 16px", fontSize:12, fontFamily:"'DM Mono',monospace", color:T.text2}}>{row.date}</td>
                <td style={{padding:"14px 16px", fontSize:12, color: row.trigger === "Anomaly" ? T.red : T.text2}}>{row.trigger}</td>
                <td style={{padding:"14px 16px", fontSize:13}}>{row.headline}</td>
                <td style={{padding:"14px 16px"}}>
                  <span style={{
                    background: riskColor(row.risk) + "18", color: riskColor(row.risk),
                    fontSize:10, fontFamily:"'DM Mono',monospace", padding:"3px 8px", borderRadius:4,
                  }}>{row.risk.toUpperCase()}</span>
                </td>
                <td style={{padding:"14px 16px"}}>
                  <button style={{
                    background:"transparent", border:`1px solid ${T.border2}`,
                    color:T.text2, padding:"4px 10px", borderRadius:5,
                    fontSize:11, cursor:"pointer", fontFamily:"'Instrument Sans',sans-serif",
                  }}>↓ PDF</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Reports page ───────────────────────────────────────────────────────────
const S3_BUCKET = "banking-bi-reports-713520983597";
const AWS_REGION = "us-east-1";

function downloadPDF(path) {
  const url = "https://" + S3_BUCKET + ".s3." + AWS_REGION + ".amazonaws.com/" + path;
  window.location.href = url;
}

function ReportsPage() {
  const [reports, setReports] = useState([]);
  const [loadingReports, setLoadingReports] = useState(true);

  useEffect(() => {
    fetch(`${API}/chat`, {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify({action:"list_reports"}),
    })
    .then(r => r.json())
    .then(data => {
      const body = typeof data.body === "string" ? JSON.parse(data.body) : data;
      if (body.reports) setReports(body.reports);
      else {
        // Fallback: list from S3 directly
        setReports([
          { name:"KPI Investigation — Apr 08 2026", date:"Apr 08 17:11 UTC", size:"6 KB", risk:"medium", path:"reports/2026/04/08/kpi-investigation-2026-04-08.pdf" },
          { name:"NIM Investigation — Apr 08 2026", date:"Apr 08 11:14 UTC", size:"4 KB", risk:"medium", path:"reports/2026/04/08/NIM-investigation-001.pdf" },
          { name:"NIM Investigation — Apr 07 2026", date:"Apr 07 18:09 UTC", size:"3 KB", risk:"medium", path:"reports/2026/04/07/NIM-investigation-1.pdf" },
        ]);
      }
    })
    .catch(() => {
      setReports([
        { name:"Daily KPI Investigation", date:"Apr 08 11:14 UTC", size:"4 KB", risk:"medium", path:"reports/2026/04/08/NIM-investigation-001.pdf" },
        { name:"Daily KPI Investigation", date:"Apr 07 18:09 UTC", size:"3 KB", risk:"medium", path:"reports/2026/04/07/NIM-investigation-1.pdf" },
      ]);
    })
    .finally(() => setLoadingReports(false));
  }, []);

  return (
    <div>
      <div style={{marginBottom:24}}>
        <div style={{fontFamily:"'DM Serif Display',serif", fontSize:26, letterSpacing:"-0.5px", marginBottom:4}}>PDF Reports</div>
        <div style={{fontSize:13, color:T.text2}}>Executive reports generated by the BI Copilot agents</div>
      </div>
      {loadingReports && <div style={{color:T.text2, fontSize:13}}>Loading reports...</div>}
      <div style={{display:"grid", gridTemplateColumns:"repeat(2,1fr)", gap:14}}>
        {reports.map(r => (
          <div key={r.key} style={{
            background:T.bg2, border:`1px solid ${T.border}`, borderRadius:12, padding:20,
          }}>
            <div style={{display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:12}}>
              <div style={{
                width:40, height:48, background:T.bg3, borderRadius:6,
                display:"flex", alignItems:"center", justifyContent:"center",
                fontSize:20, border:`1px solid ${T.border}`,
              }}>📄</div>
              <span style={{
                background: riskColor(r.risk) + "18", color: riskColor(r.risk),
                fontSize:10, fontFamily:"'DM Mono',monospace", padding:"3px 8px", borderRadius:4,
              }}>{r.risk.toUpperCase()}</span>
            </div>
            <div style={{fontSize:14, fontWeight:600, marginBottom:4}}>{r.name}</div>
            <div style={{fontSize:11, color:T.text2, marginBottom:14, fontFamily:"'DM Mono',monospace"}}>{r.date} · {r.size}</div>
            <button onClick={() => downloadPDF(r.path)} style={{
              width:"100%", background:`linear-gradient(135deg,${T.gold},${T.gold2})`,
              color:T.bg, border:"none", padding:"9px", borderRadius:7,
              fontSize:12, fontWeight:600, cursor:"pointer", fontFamily:"'Instrument Sans',sans-serif",
            }}>Download PDF</button>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Chat panel ─────────────────────────────────────────────────────────────
function ChatPanel() {
  const [messages, setMessages] = useState([
    { role:"agent", text:"Good morning. I'm your Banking BI Copilot. I've detected 2 active alerts — NIM compression and LCR approaching threshold. Would you like me to investigate?" }
  ]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({behavior:"smooth"}); }, [messages, thinking]);

  const send = useCallback(async (msg) => {
    if (!msg.trim()) return;
    setMessages(m => [...m, {role:"user", text:msg}]);
    setInput("");
    setThinking(true);

    try {
      const resp = await fetch(`${API}/chat`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({message:msg}),
      });
      const data = await resp.json();
      let text = "";
      if (data.body) {
        try { text = JSON.parse(data.body).response || JSON.parse(data.body).message || "Investigation complete."; }
        catch { text = data.body; }
      } else { text = data.response || data.message || "Investigation complete. Check Reports for your PDF."; }
      setMessages(m => [...m, {role:"agent", text}]);
    } catch {
      setMessages(m => [...m, {role:"agent", text:"Unable to reach the BI Copilot pipeline. Please try again."}]);
    }
    setThinking(false);
  }, []);

  const quickQs = ["Why is NIM falling?", "LCR risk analysis", "Generate PDF report", "CASA trend drivers"];

  return (
    <div style={S.chatPanel}>
      <div style={{padding:"18px 18px 14px", borderBottom:`1px solid ${T.border}`}}>
        <div style={{fontSize:14, fontWeight:600, marginBottom:2}}>BI Copilot</div>
        <div style={{fontSize:11, color:T.text2}}>Ask anything about your banking KPIs</div>
      </div>

      <div style={{flex:1, overflowY:"auto", padding:"14px 14px 0", display:"flex", flexDirection:"column", gap:10}}>
        {messages.map((m,i) => (
          <div key={i} style={{
            maxWidth:"90%", padding:"10px 13px", borderRadius:10, fontSize:12, lineHeight:1.6,
            alignSelf: m.role === "user" ? "flex-end" : "flex-start",
            background: m.role === "user" ? "rgba(201,168,76,0.12)" : T.bg3,
            border: m.role === "user" ? `1px solid rgba(201,168,76,0.2)` : `1px solid ${T.border}`,
            borderBottomRightRadius: m.role === "user" ? 3 : 10,
            borderBottomLeftRadius:  m.role === "user" ? 10 : 3,
          }}>
            {m.role === "agent" && (
              <div style={{fontSize:9, color:T.gold, letterSpacing:"1.5px", textTransform:"uppercase", marginBottom:5, fontWeight:600}}>Copilot</div>
            )}
            {m.text}
          </div>
        ))}
        {thinking && (
          <div style={{
            alignSelf:"flex-start", background:T.bg3, border:`1px solid ${T.border}`,
            borderRadius:10, borderBottomLeftRadius:3, padding:"12px 16px",
            display:"flex", gap:5,
          }}>
            {[0,1,2].map(i => (
              <div key={i} style={{
                width:5, height:5, borderRadius:"50%", background:T.text3,
                animation:`bounce 1.2s ${i*0.2}s infinite`,
              }}/>
            ))}
          </div>
        )}
        <div ref={bottomRef}/>
      </div>

      <div style={{padding:"12px 14px"}}>
        <div style={{display:"flex", flexWrap:"wrap", gap:5, marginBottom:8}}>
          {quickQs.map(q => (
            <button key={q} onClick={() => send(q)} style={{
              fontSize:10, background:T.bg3, border:`1px solid ${T.border}`,
              color:T.text2, padding:"4px 10px", borderRadius:20, cursor:"pointer",
              fontFamily:"'Instrument Sans',sans-serif", transition:"all 0.15s",
            }}>{q}</button>
          ))}
        </div>
        <div style={{
          display:"flex", gap:8, background:T.bg3,
          border:`1px solid ${T.border2}`, borderRadius:10, padding:"9px 12px",
        }}>
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key==="Enter" && !e.shiftKey) { e.preventDefault(); send(input); }}}
            placeholder="Ask about KPIs, drivers, risks..."
            rows={1}
            style={{
              flex:1, background:"transparent", border:"none", outline:"none",
              color:T.text, fontSize:12, fontFamily:"'Instrument Sans',sans-serif",
              resize:"none", maxHeight:70, lineHeight:1.5,
            }}
          />
          <button onClick={() => send(input)} style={{
            background:T.gold, border:"none", color:T.bg,
            width:28, height:28, borderRadius:7, cursor:"pointer",
            fontSize:13, flexShrink:0, alignSelf:"flex-end",
          }}>→</button>
        </div>
      </div>
      <style>{`@keyframes bounce { 0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-5px)} }`}</style>
    </div>
  );
}

// ── App ────────────────────────────────────────────────────────────────────
export default function App() {
  const [page, setPage] = useState("dashboard");
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);

  const showToast = (title, body) => {
    setToast({title, body});
    setTimeout(() => setToast(null), 4000);
  };

  const triggerInvestigation = async () => {
    setLoading(true);
    showToast("Investigation Started", "Agents are investigating all 6 KPIs...");
    try {
      const resp = await fetch(`${API}/investigate`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({trigger:"manual", kpis:["nim","npl_ratio","casa_ratio","roe_roa","cost_income","lcr_nsfr"]}),
      });
      const data = await resp.json();
      const body = typeof data.body === "string" ? JSON.parse(data.body) : data;
      const sid = (body.session_id || data.session_id || "").slice(0,8);
      showToast("Investigation Complete ✓", `PDF report generated. Session: ${sid}...`);
    } catch {
      showToast("Error", "Could not reach the agent pipeline.");
    }
    setLoading(false);
  };

  const now = new Date().toLocaleDateString("en-US", {weekday:"short", month:"short", day:"numeric"});

  return (
    <>
      {/* Topbar */}
      <div style={S.topbar}>
        <Logo/>
        <div style={{display:"flex", alignItems:"center", gap:20}}>
          <div style={{display:"flex", alignItems:"center", gap:6, fontSize:11, color:T.green, fontFamily:"'DM Mono',monospace"}}>
            <div style={{width:6, height:6, borderRadius:"50%", background:T.green, animation:"pulse 2s infinite"}}/>
            Agents Active
          </div>
          <div style={{fontSize:11, color:T.text2, fontFamily:"'DM Mono',monospace"}}>{now}</div>
          <button onClick={triggerInvestigation} disabled={loading} style={{
            background:`linear-gradient(135deg,${T.gold},${T.gold2})`,
            color:T.bg, border:"none", padding:"8px 16px", borderRadius:6,
            fontSize:12, fontWeight:600, cursor:loading?"not-allowed":"pointer",
            fontFamily:"'Instrument Sans',sans-serif", opacity:loading?0.6:1,
          }}>▶ Run Investigation</button>
        </div>
      </div>

      {/* Layout */}
      <div style={S.layout}>
        {/* Sidebar */}
        <div style={S.sidebar}>
          <div style={{padding:"0 10px", marginBottom:6}}>
            <div style={{fontSize:9, letterSpacing:"2px", textTransform:"uppercase", color:T.text3, padding:"0 6px", marginBottom:6, fontWeight:600}}>Navigation</div>
            <NavItem icon="⬡" label="Dashboard"     active={page==="dashboard"}   onClick={() => setPage("dashboard")}/>
            <NavItem icon="◷" label="Investigations" active={page==="history"}     onClick={() => setPage("history")}/>
            <NavItem icon="⬒" label="PDF Reports"    active={page==="reports"}     onClick={() => setPage("reports")}/>
          </div>

          <div style={{height:1, background:T.border, margin:"12px 16px"}}/>

          <div style={{padding:"0 6px"}}>
            <div style={{fontSize:9, letterSpacing:"2px", textTransform:"uppercase", color:T.text3, padding:"0 10px", marginBottom:6, fontWeight:600}}>KPI Monitor</div>
            {KPI_DATA.map(k => <KpiPill key={k.id} kpi={k}/>)}
          </div>
        </div>

        {/* Main */}
        <div style={S.main}>
          {page === "dashboard"  && <DashboardPage onInvestigate={triggerInvestigation} loading={loading}/>}
          {page === "history"    && <HistoryPage/>}
          {page === "reports"    && <ReportsPage/>}
        </div>

        {/* Chat */}
        <ChatPanel/>
      </div>

      {/* Toast */}
      {toast && (
        <div style={{
          position:"fixed", bottom:24, right:24,
          background:T.bg3, border:`1px solid ${T.border2}`,
          borderRadius:10, padding:"14px 18px", zIndex:1000, maxWidth:320,
          animation:"fadeUp 0.3s ease",
        }}>
          <div style={{fontWeight:600, marginBottom:3, fontSize:13}}>{toast.title}</div>
          <div style={{color:T.text2, fontSize:12}}>{toast.body}</div>
        </div>
      )}

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        @keyframes fadeUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
        * { scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.1) transparent; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
      `}</style>
    </>
  );
}
