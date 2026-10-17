"use strict";
const out = document.getElementById("out");
const form = document.getElementById("ask-form");
const qbox = document.getElementById("q");
const go = document.getElementById("go");

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function render(r) {
  out.replaceChildren();
  const card = el("div", "card " + (r.status === "answered" ? "" : "declined"));
  if (r.status === "answered") {
    card.appendChild(el("p", "answer", r.answer));
    r.citations.forEach((c, i) => {
      const box = el("div", "cite");
      const q = el("blockquote");
      q.appendChild(el("span", "n", "[" + (i + 1) + "] "));
      q.appendChild(document.createTextNode("“" + c.quote + "”"));
      box.appendChild(q);
      const src = el("div", "src");
      src.appendChild(document.createTextNode(c.doc_title + " — " + c.section_path + " — "));
      const a = el("a", null, "page " + c.page);
      a.href = c.url; a.target = "_blank"; a.rel = "noopener";
      src.appendChild(a);
      box.appendChild(src);
      card.appendChild(box);
    });
  } else if (r.status === "clarify") {
    card.appendChild(el("p", "answer", "A clarifying question: " + r.clarifying_question));
  } else {
    card.appendChild(el("p", "answer", r.answer || "I don't know — the documents don't cover this."));
    if (r.checked_sections && r.checked_sections.length) {
      card.appendChild(el("p", "meta", "Closest sections checked:"));
      const ul = el("ul", "checked");
      r.checked_sections.forEach((s) => ul.appendChild(el("li", null, s)));
      card.appendChild(ul);
    }
  }
  const t = r.timings_ms || {};
  const cost = r.cost_usd == null ? "n/a" : "$" + r.cost_usd.toFixed(5);
  card.appendChild(el("div", "meta", "Latency " + Math.round(t.total || 0) + " ms · cost " + cost));
  out.appendChild(card);
}

async function ask(question) {
  go.disabled = true;
  out.replaceChildren(el("div", "card", "Searching the documents…"));
  try {
    const res = await fetch("/api/ask", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const body = await res.json();
    if (!res.ok) {
      out.replaceChildren(el("div", "card declined", typeof body.detail === "string" ? body.detail : "Request failed"));
    } else {
      render(body);
    }
  } catch (e) {
    out.replaceChildren(el("div", "card declined", "Network error: " + e.message));
  } finally {
    go.disabled = false;
  }
}

form.addEventListener("submit", (ev) => { ev.preventDefault(); ask(qbox.value.trim()); });

fetch("/api/examples").then((r) => r.json()).then((list) => {
  const chips = document.getElementById("chips");
  list.forEach((q) => {
    const b = el("button", "chip", q);
    b.type = "button";
    b.addEventListener("click", () => { qbox.value = q; ask(q); });
    chips.appendChild(b);
  });
}).catch(() => {});
