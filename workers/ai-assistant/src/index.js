/**
 * AI 情报站智能助手 — Cloudflare Worker
 * 
 * 部署: npx wrangler deploy
 * 需要: KV namespace `AI_ASSISTANT_KV` + secret `DEEPSEEK_API_KEY`
 * 
 * npx wrangler kv:namespace create AI_ASSISTANT_KV
 * npx wrangler secret put DEEPSEEK_API_KEY
 */

// ── Config ──
const DAILY_LIMIT = 10;          // 每日每 IP 限额
const DEEPSEEK_MODEL = "deepseek-chat";
const MAX_TOKENS = 600;         // 回答最大 token 数

// ── CORS headers ──
const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "https://ai.hjhai.xyz",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Max-Age": "86400",
};

// ── System prompt ──
const SYSTEM_PROMPT = `你是 AI 情报站的智能助手。用户正在阅读一篇 AI 技术文章，对文中的某个术语/概念有疑问。
请用简洁易懂的中文解释（2-4 句话即可），帮助用户理解。如果涉及论文或技术细节，给出关键要点。
不要做多余的寒暄，直接回答问题。`;

// ── Utils ──
function today() {
  return new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Shanghai" }))
    .toISOString().slice(0, 10);
}

function getClientIP(request) {
  return request.headers.get("CF-Connecting-IP") || "unknown";
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data, null, 2), {
    status,
    headers: { ...CORS_HEADERS, "Content-Type": "application/json; charset=utf-8" },
  });
}

function error(msg, status = 400) {
  return json({ error: msg }, status);
}

// ── KV 限流 ──
async function checkRateLimit(ip, env) {
  const key = `rate_limit:${ip}:${today()}`;
  const count = parseInt((await env.AI_ASSISTANT_KV.get(key)) || "0", 10);
  return { count, remaining: DAILY_LIMIT - count };
}

async function incrementRateLimit(ip, env) {
  const key = `rate_limit:${ip}:${today()}`;
  const count = parseInt((await env.AI_ASSISTANT_KV.get(key)) || "0", 10);
  // TTL: 到明天凌晨(北京时间)
  const nextDay = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Shanghai" }));
  nextDay.setDate(nextDay.getDate() + 1);
  nextDay.setHours(0, 0, 0, 0);
  const ttl = Math.ceil((nextDay.getTime() - Date.now()) / 1000);
  await env.AI_ASSISTANT_KV.put(key, String(count + 1), { expirationTtl: ttl });
  return count + 1;
}

// ── DeepSeek API ──
async function askDeepSeek(question, context, apiKey) {
  const messages = [
    { role: "system", content: SYSTEM_PROMPT },
  ];
  
  // 注入文章上下文
  if (context) {
    messages.push({
      role: "system",
      content: `用户当前正在阅读的文章信息：\n标题：${context.title || "未知"}\n摘要：${context.summary || "无"}\n来源：${context.source || "未知"}`,
    });
  }
  
  messages.push({ role: "user", content: question });

  const resp = await fetch("https://api.deepseek.com/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: DEEPSEEK_MODEL,
      messages,
      max_tokens: MAX_TOKENS,
      temperature: 0.3,
    }),
  });

  if (!resp.ok) {
    const err = await resp.text();
    throw new Error(`DeepSeek API error ${resp.status}: ${err}`);
  }

  const data = await resp.json();
  return data.choices[0].message.content;
}

// ── Main handler ──
export default {
  async fetch(request, env) {
    // CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    const url = new URL(request.url);

    // Health check
    if (url.pathname === "/health") {
      return json({ status: "ok" });
    }

    // POST /ask only
    if (url.pathname !== "/ask" || request.method !== "POST") {
      return error("POST /ask only", 404);
    }

    // Parse body
    let body;
    try {
      body = await request.json();
    } catch {
      return error("Invalid JSON body");
    }

    const { question, title, summary, source } = body;
    if (!question || typeof question !== "string" || question.trim().length === 0) {
      return error("Missing 'question' field");
    }
    if (question.length > 500) {
      return error("Question too long (max 500 chars)");
    }

    // Rate limit
    const ip = getClientIP(request);
    const { count, remaining } = await checkRateLimit(ip, env);

    if (remaining <= 0) {
      return json({
        error: `今日提问次数已用完（${DAILY_LIMIT}/${DAILY_LIMIT}），请明天再来！`,
        remaining: 0,
        limit: DAILY_LIMIT,
      }, 429);
    }

    // Call DeepSeek
    try {
      const answer = await askDeepSeek(question.trim(), {
        title: title || "",
        summary: (summary || "").slice(0, 300),
        source: source || "",
      }, env.DEEPSEEK_API_KEY);

      // Increment after success
      const newCount = await incrementRateLimit(ip, env);
      const newRemaining = DAILY_LIMIT - newCount;

      return json({
        answer,
        remaining: Math.max(0, newRemaining),
        used: newCount,
        limit: DAILY_LIMIT,
      });
    } catch (e) {
      console.error("DeepSeek error:", e.message);
      return error("AI 服务暂时不可用，请稍后重试", 502);
    }
  },
};
