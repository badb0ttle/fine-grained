# AI 情报站智能助手 — Cloudflare Worker 部署

## 快速部署

### 1. 安装 Wrangler
```bash
npm install -g wrangler
wrangler login
```

### 2. 创建 KV Namespace
```bash
npx wrangler kv:namespace create AI_ASSISTANT_KV
```
将输出的 `id` 填入 `wrangler.toml` 的对应字段。

### 3. 设置 DeepSeek API Key
```bash
npx wrangler secret put DEEPSEEK_API_KEY
```
输入你的 DeepSeek API Key。

### 4. 部署
```bash
npx wrangler deploy
```

### 5. 绑定域名（可选）
在 Cloudflare Dashboard → Workers & Pages → ai-intel-assistant → Triggers → 添加自定义域名，如 `ai-assistant.hjhai.xyz`

### 6. 更新前端 WORKER_URL
部署后，修改 `assets/ai-assistant.js` 中的 `WORKER_URL` 为实际 Worker 地址。

## API 说明

**POST /ask**
```json
{
  "question": "什么是 RLHF？",
  "title": "GPT-5 Technical Report",
  "summary": "OpenAI released GPT-5 with ...",
  "source": "OpenAI Blog"
}
```

**Response:**
```json
{
  "answer": "RLHF 即 Reinforcement Learning from Human Feedback...",
  "remaining": 8,
  "used": 2,
  "limit": 10
}
```

**限流:** 每 IP 每天 10 次，超限返回 429。
