// Browser-side Kick.com chat connector for public chats.
// Resolves kick.com/{channel} to a chatroom id in the browser, then subscribes
// to Kick's public Pusher channel: chatrooms.{chatroomId}.v2.
const PUSHER_KEY = "32cbd69e4b950bf97679";
const PUSHER_URL = `wss://ws-us2.pusher.com/app/${PUSHER_KEY}?protocol=7&client=js&version=8.4.0-rc2&flash=false`;
const PING_INTERVAL = 30000;
const RECONNECT_DELAY = 3000;
const CHANNEL_DATA_URLS = [
  "https://kick.com/api/v1/channels/{slug}",
  "https://kick.com/api/v2/channels/{slug}",
];

class KickChat {
  constructor(channel, options) {
    const normalized = String(channel || "").trim().toLowerCase();
    if (!normalized) throw new Error("Kick channel is required.");
    this.channel = normalized;
    this.options = options || {};
    this.ws = null;
    this.pingTimer = null;
    this.reconnectTimer = null;
    this.listeners = {};
    this.chatroomId = null;
    this.destroyed = false;
  }

  on(event, fn) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(fn);
    return this;
  }

  emit(event, data) {
    (this.listeners[event] || []).forEach((fn) => fn(data || {}));
  }

  async connect() {
    this.destroyed = false;
    this.clearReconnectTimer();
    this.closeSocket();
    this.emit("status", { state: "resolving", message: `Resolving Kick channel ${this.channel}...` });
    try {
      if (this.options.chatroomId) {
        this.chatroomId = this.options.chatroomId;
      } else {
        this.chatroomId = await this.resolveChatroomId();
      }
      this.connectPusher();
    } catch (err) {
      this.emit("error", { message: `Kick chat failed: ${err.message}` });
    }
  }

  disconnect() {
    this.destroyed = true;
    this.clearReconnectTimer();
    this.closeSocket();
    this.emit("disconnected", {});
  }

  async resolveChatroomId() {
    const slug = encodeURIComponent(this.channel);
    for (const template of CHANNEL_DATA_URLS) {
      try {
        const response = await fetch(template.replace("{slug}", slug));
        if (!response.ok) continue;
        const data = await response.json();
        const id = data.chatroom && data.chatroom.id;
        if (id) return id;
      } catch (_err) {
        // Try the next endpoint.
      }
    }
    throw new Error("Could not resolve Kick chatroom id. Kick may be blocking this browser request.");
  }

  connectPusher() {
    if (this.destroyed || !this.chatroomId) return;
    this.clearReconnectTimer();
    this.closeSocket();
    const ws = new WebSocket(PUSHER_URL);
    this.ws = ws;

    ws.onopen = () => {
      this.clearPingTimer();
      this.pingTimer = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ event: "pusher:ping", data: {} }));
        }
      }, PING_INTERVAL);
    };

    ws.onmessage = (event) => this.handlePusherMessage(ws, event.data);
    ws.onerror = () => {
      if (this.ws === ws) ws.close();
    };
    ws.onclose = () => {
      if (this.ws !== ws) return;
      this.clearPingTimer();
      this.ws = null;
      if (!this.destroyed) {
        this.emit("status", { state: "reconnecting", message: "Kick chat disconnected; reconnecting..." });
        this.reconnectTimer = setTimeout(() => {
          this.reconnectTimer = null;
          this.connectPusher();
        }, RECONNECT_DELAY);
      }
    };
  }

  handlePusherMessage(ws, rawMessage) {
    try {
      const msg = JSON.parse(rawMessage);
      if (msg.event === "pusher:connection_established") {
        ws.send(JSON.stringify({
          event: "pusher:subscribe",
          data: { auth: "", channel: `chatrooms.${this.chatroomId}.v2` },
        }));
        return;
      }
      if (msg.event === "pusher_internal:subscription_succeeded") {
        this.emit("connected", { chatroomId: this.chatroomId, message: `Connected to Kick chatroom ${this.chatroomId}.` });
        return;
      }
      if (msg.event === "pusher:ping") {
        ws.send(JSON.stringify({ event: "pusher:pong", data: {} }));
        return;
      }
      if (msg.event === "pusher:pong") return;
      if (msg.event === "App\\Events\\ChatMessageEvent" || msg.event === "App\\Events\\ChatMessageSentEvent") {
        const chatData = JSON.parse(msg.data);
        this.emit("message", {
          author: (chatData.sender && (chatData.sender.username || chatData.sender.slug)) || "Anonymous",
          text: chatData.content || "",
          raw: chatData,
        });
      }
    } catch (_err) {
      // Ignore malformed Pusher messages.
    }
  }

  clearPingTimer() {
    if (this.pingTimer) clearInterval(this.pingTimer);
    this.pingTimer = null;
  }

  clearReconnectTimer() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
  }

  closeSocket() {
    this.clearPingTimer();
    if (!this.ws) return;
    const ws = this.ws;
    this.ws = null;
    ws.onclose = null;
    ws.onerror = null;
    try { ws.close(); } catch (_err) {}
  }
}

window.KickChat = KickChat;
