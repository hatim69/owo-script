const root = document.getElementById("app");
const AVATARS = ["🙂", "😎", "🧛", "🧝", "🤖", "🐺", "🦊", "👽", "🧟", "🥷", "👑", "🎭"];

let state = null;
let fandoms = null;
let draftAvatar = AVATARS[0];

async function api(path, opts) {
  const res = await fetch(path, {
    method: opts ? "POST" : "GET",
    headers: opts ? { "Content-Type": "application/json" } : undefined,
    body: opts ? JSON.stringify(opts) : undefined,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Something went wrong.");
  return data;
}

function toast(msg) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = msg;
  document.getElementById("phone").appendChild(el);
  setTimeout(() => el.remove(), 2200);
}

function timeAgo(ts) {
  const s = Math.max(1, Math.floor(Date.now() / 1000 - ts));
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h`;
}

async function refresh() {
  state = await api("/api/state");
  render();
}

async function boot() {
  try {
    [state, fandoms] = await Promise.all([api("/api/state"), api("/api/fandoms")]);
  } catch (e) {
    root.innerHTML = `<div class="screen center"><p>${e.message}</p></div>`;
    return;
  }
  render();
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
}

function render() {
  if (!state.persona) return renderPersonaScreen();
  if (!state.fandom) return renderFandomScreen();
  return renderFeedScreen();
}

// --- Screen: persona creation ------------------------------------------------
function renderPersonaScreen() {
  root.innerHTML = `
    <div class="screen">
      <div class="hero">
        <div class="logo">✨</div>
        <h1>status</h1>
        <p>sims, but social. Build a persona, drop into a fandom, and live out a story-driven social life.</p>
      </div>
      <div class="field mt16">
        <label>Choose an avatar</label>
        <div class="avatar-grid" id="avatar-grid"></div>
      </div>
      <div class="field">
        <label>Display name</label>
        <input id="persona-name" maxlength="24" placeholder="e.g. Nyx Waverly" />
      </div>
      <div class="field">
        <label>Bio <span class="dim">(optional)</span></label>
        <textarea id="persona-bio" maxlength="120" placeholder="Who are you in this world?"></textarea>
      </div>
      <button class="btn" id="persona-continue">Continue</button>
    </div>
  `;

  const grid = document.getElementById("avatar-grid");
  AVATARS.forEach((a) => {
    const b = document.createElement("div");
    b.className = "avatar-choice" + (a === draftAvatar ? " selected" : "");
    b.textContent = a;
    b.onclick = () => {
      draftAvatar = a;
      grid.querySelectorAll(".avatar-choice").forEach((el) => el.classList.remove("selected"));
      b.classList.add("selected");
    };
    grid.appendChild(b);
  });

  document.getElementById("persona-continue").onclick = async () => {
    const name = document.getElementById("persona-name").value.trim();
    const bio = document.getElementById("persona-bio").value.trim();
    if (!name) return toast("Give your persona a name first.");
    try {
      state = await api("/api/persona", { name, avatar: draftAvatar, bio });
      render();
    } catch (e) {
      toast(e.message);
    }
  };
}

// --- Screen: fandom selection ------------------------------------------------
function renderFandomScreen() {
  root.innerHTML = `
    <div class="screen">
      <div class="hero">
        <div class="logo">${draftAvatar}</div>
        <h1>Pick your world</h1>
        <p>Your persona will drop into this community, alongside its cast of characters.</p>
      </div>
      <div class="fandom-list" id="fandom-list"></div>
    </div>
  `;
  const list = document.getElementById("fandom-list");
  fandoms.forEach((f) => {
    const card = document.createElement("div");
    card.className = "fandom-card";
    card.innerHTML = `
      <div class="emoji">${f.emoji}</div>
      <div>
        <div class="name">${f.name}</div>
        <div class="desc">${f.desc}</div>
      </div>
    `;
    card.onclick = async () => {
      try {
        state = await api("/api/fandom", { fandom_id: f.id });
        render();
      } catch (e) {
        toast(e.message);
      }
    };
    list.appendChild(card);
  });
}

// --- Screen: feed --------------------------------------------------------------
function renderFeedScreen() {
  const energyPct = Math.round((state.energy / state.max_energy) * 100);
  root.innerHTML = `
    <div class="topbar">
      <div class="brand">status<span>.</span></div>
      <div class="energy-pill" id="energy-pill">
        ⚡ ${state.energy}/${state.max_energy}
        <div class="energy-bar-mini"><div style="width:${energyPct}%"></div></div>
      </div>
    </div>
    <div class="profile-strip">
      <div class="avatar">${state.persona.avatar}</div>
      <div>
        <div class="name">${escapeHtml(state.persona.name)}</div>
        <div class="meta">${state.fandom.emoji} ${state.fandom.name} · Clout ${state.clout}</div>
      </div>
      <div class="tier-badge">${state.tier.icon} ${state.tier.label}</div>
    </div>
    <div class="composer">
      <textarea id="post-text" maxlength="280" placeholder="What's happening in your story?"></textarea>
      <div class="composer-row">
        <span class="cost">Costs 15 ⚡ to post</span>
        <button class="btn small" id="post-btn">Post</button>
      </div>
    </div>
    <div class="feed" id="feed"></div>
    <div class="bottom-actions">
      <button class="btn secondary small" id="reset-btn">Restart</button>
      <button class="btn secondary small" id="premium-btn">${state.premium ? "★ Premium" : "Go Premium (demo)"}</button>
      <button class="btn small" id="ad-btn">Watch ad +⚡</button>
    </div>
  `;

  const feed = document.getElementById("feed");
  state.posts.forEach((p) => feed.appendChild(renderPost(p)));

  document.getElementById("post-btn").onclick = submitPost;
  document.getElementById("ad-btn").onclick = watchAd;
  document.getElementById("premium-btn").onclick = togglePremium;
  document.getElementById("reset-btn").onclick = restart;
  document.getElementById("energy-pill").onclick = watchAd;
}

function renderPost(p) {
  const el = document.createElement("div");
  el.className = "post";
  const comments = p.comments
    .map(
      (c) => `<div class="comment"><span class="avatar">${c.avatar}</span><span><span class="author">${escapeHtml(c.author)}</span>${escapeHtml(c.text)}</span></div>`
    )
    .join("");
  el.innerHTML = `
    <div class="post-head">
      <span class="avatar">${p.avatar}</span>
      <span class="author">${escapeHtml(p.author)}</span>
      <span class="time">${timeAgo(p.ts)}</span>
    </div>
    <div class="post-text">${escapeHtml(p.text)}</div>
    <div class="post-stats">
      <span>❤️ ${p.likes}</span>
      <span>💬 ${p.comments.length}</span>
      <span class="badge-cat ${p.category}">${p.category}</span>
    </div>
    ${comments ? `<div class="comments">${comments}</div>` : ""}
  `;
  return el;
}

async function submitPost() {
  const input = document.getElementById("post-text");
  const text = input.value.trim();
  if (!text) return toast("Write something first.");
  const btn = document.getElementById("post-btn");
  btn.disabled = true;
  try {
    state = await api("/api/post", { text });
    render();
  } catch (e) {
    if (e.message.toLowerCase().includes("energy")) {
      toast("Out of energy - watch an ad or go premium.");
    } else {
      toast(e.message);
    }
  } finally {
    btn.disabled = false;
  }
}

async function watchAd() {
  toast("Watching ad…");
  const btn = document.getElementById("ad-btn");
  if (btn) btn.disabled = true;
  setTimeout(async () => {
    try {
      const res = await api("/api/energy/watch_ad", {});
      state = res;
      toast(`+${res.gained} energy`);
      render();
    } catch (e) {
      toast(e.message);
    }
  }, 900);
}

async function togglePremium() {
  try {
    state = await api("/api/premium", { premium: !state.premium });
    toast(state.premium ? "Premium activated (demo) - energy refilled!" : "Premium turned off.");
    render();
  } catch (e) {
    toast(e.message);
  }
}

async function restart() {
  if (!confirm("Start over? This clears your persona, fandom, and feed.")) return;
  state = await api("/api/reset", {});
  render();
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s == null ? "" : s;
  return div.innerHTML;
}

boot();
