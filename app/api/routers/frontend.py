"""前端页面路由 — 提供聊天 UI。"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["frontend"])

_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Travel Agent ✈️</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, "Segoe UI", "Noto Sans SC", sans-serif; background: #f5f5f5; }
  .container { max-width: 900px; margin: 0 auto; height: 100vh; display: flex; flex-direction: column; }

  /* 顶栏 */
  header { background: #1a1a2e; color: white; padding: 12px 20px; display: flex; align-items: center; gap: 8px; }
  header h1 { font-size: 18px; font-weight: 600; }
  header .badge { background: #16213e; padding: 2px 8px; border-radius: 10px; font-size: 12px; color: #aaa; }

  /* 聊天区 */
  #chat { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 16px; }
  .msg { max-width: 80%; padding: 12px 16px; border-radius: 12px; line-height: 1.6; white-space: pre-wrap; word-break: break-word; }
  .msg.user { align-self: flex-end; background: #2563eb; color: white; }
  .msg.bot { align-self: flex-start; background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  .msg.error { align-self: center; background: #fee; color: #c33; border: 1px solid #fcc; }
  .msg .meta { font-size: 11px; color: #999; margin-top: 4px; }

  /* 追问选项 */
  .questions { background: white; border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  .questions h3 { font-size: 14px; margin-bottom: 12px; color: #333; }
  .q-group { margin-bottom: 16px; }
  .q-group .q-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; color: #555; }
  .q-options { display: flex; flex-wrap: wrap; gap: 8px; }
  .q-opt { padding: 6px 14px; border: 1px solid #ddd; border-radius: 20px; cursor: pointer; font-size: 13px; transition: all 0.2s; }
  .q-opt:hover { border-color: #2563eb; color: #2563eb; }
  .q-opt.selected { background: #2563eb; color: white; border-color: #2563eb; }
  .q-opt .desc { font-size: 11px; color: #999; }
  .q-opt:hover .desc { color: #93c5fd; }
  .q-submit { margin-top: 12px; padding: 8px 24px; background: #2563eb; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
  .q-submit:hover { background: #1d4ed8; }
  .q-submit:disabled { background: #ccc; cursor: not-allowed; }

  /* 行程卡片 */
  .plan-card { background: white; border-radius: 12px; padding: 16px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }
  .plan-card h3 { font-size: 16px; margin-bottom: 8px; }
  .plan-card .total { font-size: 14px; color: #2563eb; font-weight: 600; margin-bottom: 12px; }
  .day-card { border-left: 3px solid #2563eb; padding: 8px 12px; margin: 8px 0; background: #f8f9ff; border-radius: 0 8px 8px 0; }
  .day-card .day-title { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
  .day-card .activity { font-size: 13px; color: #555; padding: 2px 0; }
  .day-card .cost { color: #e67e22; font-weight: 600; }

  /* 输入区 */
  .input-area { padding: 16px 20px; background: white; border-top: 1px solid #eee; display: flex; gap: 8px; }
  .input-area input { flex: 1; padding: 10px 14px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
  .input-area input:focus { outline: none; border-color: #2563eb; }
  .input-area button { padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
  .input-area button:hover { background: #1d4ed8; }
  .input-area button:disabled { background: #ccc; cursor: not-allowed; }

  /* 状态指示 */
  .status { font-size: 12px; color: #999; padding: 4px 20px; background: white; }
  .status .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #ccc; margin-right: 4px; }
  .status.active .dot { background: #22c55e; animation: pulse 1s infinite; }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>✈️ Travel Agent</h1>
    <span class="badge">FastAPI + LangGraph</span>
  </header>

  <div id="chat"></div>

  <div class="status" id="status"><span class="dot"></span><span id="status-text">就绪</span></div>

  <div class="input-area">
    <input id="input" type="text" placeholder="描述你的旅行需求…" autocomplete="off" />
    <button id="send" onclick="send()">发送</button>
  </div>
</div>

<script>
const chat = document.getElementById('chat');
const input = document.getElementById('input');
const sendBtn = document.getElementById('send');
const statusEl = document.getElementById('status');
const statusText = document.getElementById('status-text');
let convId = null;
let busy = false;

input.addEventListener('keydown', e => { if (e.key === 'Enter' && !busy) send(); });

function addMsg(role, text) {
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.textContent = text;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

function setStatus(text, active) {
  statusText.textContent = text;
  statusEl.className = 'status' + (active ? ' active' : '');
}

function renderPlan(plan) {
  if (!plan || !plan.days) return;
  const card = document.createElement('div');
  card.className = 'plan-card';
  let html = '<h3>📋 ' + (plan.title || '行程') + '</h3>';
  html += '<div class="total">总费用：¥' + (plan.total_cost || 0).toFixed(0) + '</div>';
  for (const day of plan.days) {
    html += '<div class="day-card"><div class="day-title">Day ' + day.day + (day.date ? ' · ' + day.date : '') + (day.hotel ? ' · 🏨 ' + day.hotel : '') + '</div>';
    if (day.activities) for (const a of day.activities) {
      html += '<div class="activity">' + (a.time_start||'') + '-' + (a.time_end||'') + ' ' + (a.place_name||a.place?.name||'') + ' <span class="cost">¥' + (a.cost||0) + '</span>' + (a.note ? ' — ' + a.note : '') + '</div>';
    }
    const actCost = (day.activities||[]).reduce((s,a) => s + (a.cost||0), 0);
    const hotelCost = (day.daily_cost||0) - actCost;
    if (hotelCost > 0) html += '<div class="activity">🏨 住宿 <span class="cost">¥' + hotelCost + '</span></div>';
    if (day.daily_cost) html += '<div class="activity cost">当日合计：¥' + day.daily_cost + '</div>';
    html += '</div>';
  }
  card.innerHTML = html;
  chat.appendChild(card);
  chat.scrollTop = chat.scrollHeight;
}

function renderQuestions(questions) {
  if (!questions || !questions.length) return;
  const box = document.createElement('div');
  box.className = 'questions';
  box.innerHTML = '<h3>🤔 请补充以下信息</h3>';
  const selected = {};

  for (const q of questions) {
    const group = document.createElement('div');
    group.className = 'q-group';
    group.innerHTML = '<div class="q-title">' + q.question + '</div>';
    const opts = document.createElement('div');
    opts.className = 'q-options';

    for (const opt of q.options) {
      const btn = document.createElement('div');
      btn.className = 'q-opt';
      btn.innerHTML = opt.label + (opt.description ? ' <span class="desc">' + opt.description + '</span>' : '');
      btn.onclick = () => {
        opts.querySelectorAll('.q-opt').forEach(o => o.classList.remove('selected'));
        btn.classList.add('selected');
        selected[q.field] = opt.value;
      };
      opts.appendChild(btn);
    }
    group.appendChild(opts);
    box.appendChild(group);
  }

  const submit = document.createElement('button');
  submit.className = 'q-submit';
  submit.textContent = '确认';
  submit.onclick = () => {
    const parts = Object.entries(selected).map(([k, v]) => k === 'destination' ? '去' + v : k === 'days' ? v + '天' : k === 'budget' ? '预算' + v + '元' : k === 'travelers' ? v + '人' : v);
    const msg = parts.join('，');
    addMsg('user', msg);
    box.remove();
    callApi(msg);
  };
  box.appendChild(submit);
  chat.appendChild(box);
  chat.scrollTop = chat.scrollHeight;
}

async function send() {
  const text = input.value.trim();
  if (!text || busy) return;
  input.value = '';
  addMsg('user', text);
  await callApi(text);
}

async function callApi(message) {
  busy = true;
  sendBtn.disabled = true;
  setStatus('思考中…', true);

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, conversation_id: convId }),
    });
    const data = await resp.json();

    if (data.conversation_id) convId = data.conversation_id;

    if (data.response) addMsg('bot', data.response);
    if (data.plan) renderPlan(data.plan);
    if (data.needs_more_info) renderQuestions(data.questions);
    if (data.status === 'error') addMsg('error', data.response);

    setStatus('就绪', false);
  } catch (e) {
    addMsg('error', '请求失败：' + e.message);
    setStatus('错误', false);
  }

  busy = false;
  sendBtn.disabled = false;
  input.focus();
}
</script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """聊天 UI 首页。"""
    return HTMLResponse(_PAGE)
