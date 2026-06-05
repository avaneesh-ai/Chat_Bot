const form = document.querySelector("#chatForm");
const input = document.querySelector("#messageInput");
const messages = document.querySelector("#messages");
const sendButton = document.querySelector("#sendButton");
const clearButton = document.querySelector("#clearButton");

let sessionId = localStorage.getItem("chatbot-session-id") || crypto.randomUUID();
localStorage.setItem("chatbot-session-id", sessionId);

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function resizeInput() {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 170)}px`;
}

function addMessage(role, text, options = {}) {
  const message = document.createElement("article");
  message.className = `message ${role === "user" ? "user-message" : "bot-message"}`;

  if (options.typing) {
    message.classList.add("typing");
  }

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "user" ? "You" : "AI";

  const body = document.createElement("p");
  body.textContent = text;

  message.append(avatar, body);
  messages.append(message);
  scrollToBottom();
  return message;
}

async function sendMessage(message) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      sessionId,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "The chatbot could not answer.");
  }

  sessionId = data.sessionId;
  localStorage.setItem("chatbot-session-id", sessionId);
  return data.reply;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const message = input.value.trim();
  if (!message) {
    return;
  }

  addMessage("user", message);
  input.value = "";
  resizeInput();

  const typing = addMessage("bot", "Thinking...", { typing: true });
  sendButton.disabled = true;

  try {
    const reply = await sendMessage(message);
    typing.classList.remove("typing");
    typing.querySelector("p").textContent = reply || "I do not have an answer yet.";
  } catch (error) {
    typing.classList.remove("typing");
    typing.querySelector("p").textContent = error.message;
  } finally {
    sendButton.disabled = false;
    input.focus();
    scrollToBottom();
  }
});

input.addEventListener("input", resizeInput);

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

clearButton.addEventListener("click", async () => {
  await fetch("/api/clear", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ sessionId }),
  });

  sessionId = crypto.randomUUID();
  localStorage.setItem("chatbot-session-id", sessionId);
  messages.innerHTML = "";
  addMessage("bot", "Welcome to the AI ChatBot.");
  input.focus();
});

resizeInput();
