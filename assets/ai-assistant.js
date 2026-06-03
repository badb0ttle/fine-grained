/**
 * AI 情报站智能助手 — 前端 Widget
 * 
 * 用法: 页面加载后自动挂载浮动按钮
 * 文章内调用 AIAssistant.openWithArticle(title, summary, source) 打开抽屉
 */

(function () {
  "use strict";

  // ⚠️ 部署后替换为你的 Worker URL
  const WORKER_URL = "https://ai-intel-assistant.hjhai.workers.dev/ask";
  const DAILY_LIMIT = 10;

  // ── 状态 ──
  let remaining = DAILY_LIMIT;   // 从 Worker 获取，初始假设满额
  let context = null;            // { title, summary, source }
  let isLoading = false;
  let drawerOpen = false;

  // ── DOM refs ──
  let elFab, elOverlay, elDrawer, elMessages, elInput, elSendBtn;
  let elQuota, elContextTag;

  // ── 初始化 ──
  function init() {
    if (document.getElementById("ai-fab")) return; // 已初始化

    // 恢复已用次数 (localStorage, 当天)
    restoreQuota();

    // 注入 HTML
    const html = `
      <button class="ai-fab" id="ai-fab" title="AI 助手">
        🤖
        <span class="ai-fab-badge" id="ai-fab-badge">${remaining}</span>
      </button>

      <div class="ai-overlay" id="ai-overlay"></div>

      <div class="ai-drawer" id="ai-drawer">
        <div class="ai-drawer-header">
          <div class="ai-drawer-title">
            <span class="icon">🤖</span> AI 助手
          </div>
          <button class="ai-drawer-close" id="ai-drawer-close">✕</button>
        </div>

        <div class="ai-quota" id="ai-quota">
          <span>今日剩余 <span class="ai-quota-remaining" id="ai-quota-count">${remaining}</span> / ${DAILY_LIMIT} 次</span>
        </div>

        <div class="ai-context-tag" id="ai-context-tag" style="display:none">
          📖 <span class="article-title" id="ai-context-title"></span>
          <button class="ai-context-clear" id="ai-context-clear" title="清除上下文">✕</button>
        </div>

        <div class="ai-messages" id="ai-messages">
          <div class="ai-welcome">
            <span class="emoji">🤖</span>
            在看文章时点击 <strong>「问 AI」</strong> 按钮<br>
            或直接在这里输入问题<br>
            <small>每天 ${DAILY_LIMIT} 次免费提问</small>
          </div>
        </div>

        <div class="ai-input-area">
          <textarea class="ai-input" id="ai-input" 
            placeholder="输入你的问题..." 
            rows="1"
            maxlength="500"></textarea>
          <button class="ai-send-btn" id="ai-send-btn" title="发送">➤</button>
        </div>
      </div>
    `;

    const wrapper = document.createElement("div");
    wrapper.innerHTML = html;
    while (wrapper.firstChild) {
      document.body.appendChild(wrapper.firstChild);
    }

    // 绑定 refs
    elFab = document.getElementById("ai-fab");
    elOverlay = document.getElementById("ai-overlay");
    elDrawer = document.getElementById("ai-drawer");
    elMessages = document.getElementById("ai-messages");
    elInput = document.getElementById("ai-input");
    elSendBtn = document.getElementById("ai-send-btn");
    elQuota = document.getElementById("ai-quota-count");
    elContextTag = document.getElementById("ai-context-tag");

    // 事件绑定
    elFab.addEventListener("click", toggleDrawer);
    elOverlay.addEventListener("click", closeDrawer);
    document.getElementById("ai-drawer-close").addEventListener("click", closeDrawer);
    document.getElementById("ai-context-clear").addEventListener("click", clearContext);
    elSendBtn.addEventListener("click", sendMessage);
    elInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
    // 自动调整输入框高度
    elInput.addEventListener("input", autoResizeInput);

    // ESC 关闭
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && drawerOpen) closeDrawer();
    });

    // 移动端键盘适配 (Visual Viewport API)
    if (window.visualViewport) {
      window.visualViewport.addEventListener("resize", function () {
        if (drawerOpen) {
          var offset = window.innerHeight - window.visualViewport.height;
          if (offset > 80) {
            // 键盘弹出 — 确保输入区可见
            elMessages.scrollTop = elMessages.scrollHeight;
          }
        }
      });
      window.visualViewport.addEventListener("scroll", function () {
        if (drawerOpen) {
          elMessages.scrollTop = elMessages.scrollHeight;
        }
      });
    }

    updateFabState();
  }

  // ── 打开/关闭 ──
  function toggleDrawer() {
    if (drawerOpen) {
      closeDrawer();
    } else {
      openDrawer();
    }
  }

  function openDrawer() {
    drawerOpen = true;
    elDrawer.classList.add("open");
    elOverlay.classList.add("open");
    elFab.style.display = "none";
    setTimeout(() => elInput.focus(), 300);
  }

  function closeDrawer() {
    drawerOpen = false;
    elDrawer.classList.remove("open");
    elOverlay.classList.remove("open");
    elFab.style.display = "flex";
  }

  // ── 文章上下文 ──
  window.AIAssistant = {
    openWithArticle: function (title, summary, source) {
      context = { title: title || "", summary: summary || "", source: source || "" };
      updateContextUI();
      if (!drawerOpen) openDrawer();
      // 添加系统消息提示上下文已设置
      addMessage("assistant", `已切换上下文：正在阅读「<b>${escHtml(title)}</b>」，有问题可以直接问我～`);
    },
  };

  function updateContextUI() {
    if (context && context.title) {
      elContextTag.style.display = "flex";
      document.getElementById("ai-context-title").textContent = context.title;
    } else {
      elContextTag.style.display = "none";
    }
  }

  function clearContext() {
    context = null;
    updateContextUI();
    addMessage("assistant", "已清除文章上下文，现在是自由问答模式～");
  }

  // ── 发送消息 ──
  async function sendMessage() {
    if (isLoading) return;

    const text = elInput.value.trim();
    if (!text) return;

    // 检查本地限额
    if (remaining <= 0) {
      addMessage("error", `今日提问次数已用完（${DAILY_LIMIT}/${DAILY_LIMIT}），请明天再来 🙏`);
      return;
    }

    // 显示用户消息
    addMessage("user", text);
    elInput.value = "";
    autoResizeInput();

    // 显示 typing
    const typingEl = addTyping();
    setLoading(true);

    try {
      const resp = await fetch(WORKER_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: text,
          title: context?.title || "",
          summary: context?.summary || "",
          source: context?.source || "",
        }),
      });

      const data = await resp.json();

      // 移除 typing
      removeTyping(typingEl);

      if (!resp.ok) {
        if (resp.status === 429) {
          remaining = 0;
          updateQuota();
          updateFabState();
          addMessage("error", data.error || "今日提问次数已用完");
        } else {
          addMessage("error", data.error || "服务暂时不可用，请稍后重试");
        }
      } else {
        addMessage("assistant", data.answer);
        remaining = data.remaining;
        updateQuota();
        saveQuota(data.used || (DAILY_LIMIT - remaining));
        updateFabState();
      }
    } catch (e) {
      removeTyping(typingEl);
      addMessage("error", "网络连接失败，请检查网络后重试");
      console.error("AI Assistant error:", e);
    }

    setLoading(false);
    elInput.focus();
  }

  function setLoading(loading) {
    isLoading = loading;
    elSendBtn.disabled = loading;
    elInput.disabled = loading;
  }

  // ── 消息渲染 ──
  function addMessage(role, text) {
    const div = document.createElement("div");
    div.className = "ai-msg " + role;
    div.innerHTML = text;
    elMessages.appendChild(div);
    scrollToBottom();
    return div;
  }

  function addTyping() {
    const div = document.createElement("div");
    div.className = "ai-msg assistant ai-typing-msg";
    div.innerHTML = '<div class="ai-typing"><span></span><span></span><span></span></div>';
    elMessages.appendChild(div);
    scrollToBottom();
    return div;
  }

  function removeTyping(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  function scrollToBottom() {
    setTimeout(() => {
      elMessages.scrollTop = elMessages.scrollHeight;
    }, 50);
  }

  // ── 配额管理 ──
  function updateQuota() {
    elQuota.textContent = remaining;
    if (remaining <= 0) {
      elQuota.className = "ai-quota-exhausted";
    } else {
      elQuota.className = "ai-quota-remaining";
    }
  }

  function updateFabState() {
    const badge = document.getElementById("ai-fab-badge");
    if (badge) badge.textContent = remaining;
    if (remaining <= 0) {
      elFab.classList.add("limited");
    } else {
      elFab.classList.remove("limited");
    }
  }

  function getQuotaKey() {
    const d = new Date();
    return "ai_quota_" + d.getFullYear() + "-" + 
      String(d.getMonth() + 1).padStart(2, "0") + "-" + 
      String(d.getDate()).padStart(2, "0");
  }

  function restoreQuota() {
    try {
      const key = getQuotaKey();
      const used = parseInt(localStorage.getItem(key) || "0", 10);
      remaining = Math.max(0, DAILY_LIMIT - used);
    } catch (e) {
      remaining = DAILY_LIMIT;
    }
  }

  function saveQuota(used) {
    try {
      const key = getQuotaKey();
      localStorage.setItem(key, String(used));
    } catch (e) { /* ignore */ }
  }

  // ── 工具函数 ──
  function autoResizeInput() {
    elInput.style.height = "auto";
    elInput.style.height = Math.min(elInput.scrollHeight, 120) + "px";
  }

  function escHtml(s) {
    if (!s) return "";
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  // ── 页面加载时初始化 ──
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
