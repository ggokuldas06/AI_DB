<script setup>
import { ref, nextTick } from 'vue'
import { marked } from 'marked'

const mode = ref('query')
const input = ref('')
const messages = ref([])
const loading = ref(false)
const chatArea = ref(null)

function scrollToBottom() {
  nextTick(() => {
    if (chatArea.value) {
      chatArea.value.scrollTop = chatArea.value.scrollHeight
    }
  })
}

async function send() {
  const text = input.value.trim()
  if (!text || loading.value) return

  messages.value.push({ type: 'user', content: text })
  input.value = ''
  loading.value = true
  scrollToBottom()

  const endpoint = mode.value === 'query' ? '/api/query' : '/api/report'
  const body = mode.value === 'query'
    ? { question: text }
    : { request: text }

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await response.json()
    if (!response.ok) {
      messages.value.push({ type: 'error', content: data.error || 'Request blocked.' })
    } else {
      messages.value.push({ type: 'result', content: data.result })
    }
    scrollToBottom()
  } catch (e) {
    messages.value.push({ type: 'error', content: e.message })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function switchMode(m) {
  if (loading.value) return
  mode.value = m
  messages.value = []
  input.value = ''
}
</script>

<template>
  <div class="app">
    <div class="mode-bar">
      <button
        class="mode-btn"
        :class="{ active: mode === 'query' }"
        @click="switchMode('query')"
      >Query</button>
      <span class="mode-sep">/</span>
      <button
        class="mode-btn"
        :class="{ active: mode === 'report' }"
        @click="switchMode('report')"
      >Create Report</button>
    </div>

    <div class="chat" ref="chatArea">
      <div
        v-for="(msg, i) in messages"
        :key="i"
        :class="['msg', msg.type]"
      >
        <template v-if="msg.type === 'user'">
          <span class="msg-text">{{ msg.content }}</span>
        </template>
        <template v-else-if="msg.type === 'progress'">
          <span class="dot">·</span>
          <span class="msg-text">{{ msg.content }}</span>
        </template>
        <template v-else-if="msg.type === 'result'">
          <div class="msg-text markdown" v-html="marked(msg.content)"></div>
        </template>
        <template v-else-if="msg.type === 'error'">
          <span class="msg-text">Error: {{ msg.content }}</span>
        </template>
      </div>

      <div v-if="loading" class="msg progress">
        <span class="dot blink">·</span>
        <span class="msg-text">Thinking...</span>
      </div>

      <div v-if="messages.length === 0 && !loading" class="empty">
        <span v-if="mode === 'query'">Ask anything about your data</span>
        <span v-else>Describe the report you need</span>
      </div>
    </div>

    <div class="input-bar">
      <textarea
        v-model="input"
        @keydown="handleKey"
        :placeholder="mode === 'query' ? 'What are the top customers by revenue?' : 'Generate a sales report by region and category...'"
        :disabled="loading"
        rows="1"
      ></textarea>
      <button class="send-btn" @click="send" :disabled="loading || !input.trim()">
        Send
      </button>
    </div>
  </div>
</template>

<style>
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  background: #000;
  color: #e0e0e0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 14px;
  height: 100vh;
  overflow: hidden;
}

#app {
  height: 100vh;
}

.app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 800px;
  margin: 0 auto;
}

.mode-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 20px 24px 16px;
  border-bottom: 1px solid #1a1a1a;
}

.mode-btn {
  background: none;
  border: none;
  color: #555;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.03em;
  cursor: pointer;
  padding: 0;
  transition: color 0.15s;
}

.mode-btn:hover {
  color: #888;
}

.mode-btn.active {
  color: #e0e0e0;
}

.mode-sep {
  color: #2a2a2a;
  font-size: 13px;
}

.chat {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  scrollbar-width: thin;
  scrollbar-color: #1f1f1f #000;
}

.chat::-webkit-scrollbar {
  width: 4px;
}
.chat::-webkit-scrollbar-track {
  background: #000;
}
.chat::-webkit-scrollbar-thumb {
  background: #1f1f1f;
  border-radius: 2px;
}

.empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2e2e2e;
  font-size: 13px;
  letter-spacing: 0.04em;
}

.msg {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  max-width: 100%;
}

.msg.user {
  justify-content: flex-end;
}

.msg.user .msg-text {
  background: #1a1a1a;
  color: #d0d0d0;
  padding: 10px 14px;
  border-radius: 12px 12px 2px 12px;
  max-width: 70%;
  line-height: 1.5;
}

.msg.progress .msg-text {
  color: #3a3a3a;
  font-size: 12px;
  line-height: 1.6;
}

.dot {
  color: #3a3a3a;
  font-size: 18px;
  line-height: 1.2;
  flex-shrink: 0;
}

@keyframes blink {
  0%, 100% { opacity: 0.2; }
  50% { opacity: 1; }
}

.blink {
  animation: blink 1.2s ease-in-out infinite;
}

.msg.result .msg-text {
  color: #c8c8c8;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 13px;
}

.msg.error .msg-text {
  color: #6b2020;
  font-size: 12px;
}

.input-bar {
  display: flex;
  gap: 10px;
  padding: 16px 24px 24px;
  border-top: 1px solid #111;
  align-items: flex-end;
}

textarea {
  flex: 1;
  background: #111;
  border: none;
  border-radius: 8px;
  color: #d0d0d0;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.5;
  padding: 12px 14px;
  resize: none;
  outline: none;
  min-height: 46px;
  max-height: 160px;
  overflow-y: auto;
  transition: background 0.15s;
}

textarea:focus {
  background: #161616;
}

textarea::placeholder {
  color: #2e2e2e;
}

textarea:disabled {
  opacity: 0.5;
}

.send-btn {
  background: #2a2a2a;
  border: none;
  border-radius: 8px;
  color: #999;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  padding: 12px 18px;
  height: 46px;
  transition: background 0.15s, color 0.15s;
  flex-shrink: 0;
  letter-spacing: 0.03em;
}

.send-btn:hover:not(:disabled) {
  background: #333;
  color: #ccc;
}

.markdown { line-height: 1.7; color: #c8c8c8; }
.markdown h1, .markdown h2, .markdown h3 { color: #e0e0e0; font-weight: 600; margin: 1em 0 0.4em; }
.markdown h2 { font-size: 15px; border-bottom: 1px solid #1e1e1e; padding-bottom: 4px; }
.markdown h3 { font-size: 14px; }
.markdown strong { color: #e8e8e8; font-weight: 600; }
.markdown ul, .markdown ol { padding-left: 1.4em; margin: 0.4em 0; }
.markdown li { margin: 0.2em 0; }
.markdown p { margin: 0.5em 0; }
.markdown code { background: #111; padding: 1px 5px; border-radius: 3px; font-family: 'SF Mono', monospace; font-size: 12px; }
.markdown table { border-collapse: collapse; width: 100%; margin: 0.6em 0; font-size: 13px; }
.markdown th { color: #888; font-weight: 500; text-align: left; padding: 4px 8px; border-bottom: 1px solid #222; }
.markdown td { padding: 4px 8px; border-bottom: 1px solid #111; }

.send-btn:disabled {
  opacity: 0.3;
  cursor: default;
}
</style>
