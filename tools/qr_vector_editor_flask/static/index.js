(function () {
  const fileListEl = document.getElementById("file-list");
  const placeholderEl = document.getElementById("placeholder");
  const editorEl = document.getElementById("editor");
  const metaEl = document.getElementById("meta");
  const statusEl = document.getElementById("status");
  const zoomInput = document.getElementById("zoom");
  const zoomVal = document.getElementById("zoom-val");
  const origLargeEl = document.getElementById("orig-large");
  const canvas = document.getElementById("qr-canvas");
  const ctx = canvas.getContext("2d");

  let current = null;      // { filename, obj }
  let vector = null;       // 2D array
  let moduleN = 0;
  let widthPx = 0, heightPx = 0;

  function setStatus(msg, ok = true) {
    statusEl.style.color = ok ? "#2f855a" : "#c53030";
    statusEl.textContent = msg || "";
    if (msg) setTimeout(() => (statusEl.textContent = ""), 1600);
  }

  async function loadList() {
    const res = await fetch("/api/list");
    const files = await res.json();
    fileListEl.innerHTML = "";
    const thumbSize = 96;

    files.forEach(it => {
      const div = document.createElement("div");
      div.className = "item";
      div.dataset.filename = it.json;

      const title = document.createElement("div");
      title.textContent = it.json;
      title.style.fontWeight = "600";
      title.style.fontSize = "13px";
      title.style.marginBottom = "6px";
      div.appendChild(title);

      const row = document.createElement("div");
      row.className = "row";
      const imgOrig = document.createElement("img");
      const imgRend = document.createElement("img");

      imgRend.src = `/api/render?file=${encodeURIComponent(it.json)}&size=${thumbSize}`;
      if (it.original_exists) {
        imgOrig.src = `/api/original?file=${encodeURIComponent(it.json)}&size=${thumbSize}`;
      } else {
        imgOrig.src =
          `data:image/svg+xml;utf8,` +
          encodeURIComponent(
            `<svg xmlns='http://www.w3.org/2000/svg' width='${thumbSize}' height='${thumbSize}'>
               <rect width='100%' height='100%' fill='#fff'/>
               <text x='50%' y='50%' dominant-baseline='middle' text-anchor='middle'
                     font-size='12' fill='#999'>no orig</text>
             </svg>`
          );
      }

      row.appendChild(imgOrig);
      row.appendChild(imgRend);
      div.appendChild(row);

      div.addEventListener("click", () => selectFile(it.json));
      fileListEl.appendChild(div);
    });
  }

  async function selectFile(filename) {
    const res = await fetch(`/api/load?file=${encodeURIComponent(filename)}`);
    const obj = await res.json();
    if (obj.error) {
      setStatus(`読み込み失敗: ${obj.error}`, false);
      return;
    }
    current = { filename, obj };
    vector = obj.vector;
    moduleN = obj.module;
    widthPx = obj.width;
    heightPx = obj.height;

    placeholderEl.classList.add("hidden");
    editorEl.classList.remove("hidden");

    metaEl.textContent = `file=${filename} | module=${moduleN}, width=${widthPx}, height=${heightPx}`;
    origLargeEl.src = `/api/original?file=${encodeURIComponent(filename)}&size=${calcDisplaySize()}`;

    drawAll();
  }

  function calcDisplaySize() {
    const panel = origLargeEl.closest(".panel");
    const panelWidth = panel.getBoundingClientRect().width;
    return Math.max(256, Math.floor(panelWidth - 24));
  }

  function drawAll() {
    if (!vector) return;
    const zoom = parseInt(zoomInput.value, 10);
    zoomVal.textContent = zoom;

    const cssSize = moduleN * zoom;
    const dpr = window.devicePixelRatio || 1;

    canvas.style.width = cssSize + "px";
    canvas.style.height = cssSize + "px";
    canvas.width = Math.floor(cssSize * dpr);
    canvas.height = Math.floor(cssSize * dpr);

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssSize, cssSize);

    for (let gy = 0; gy < moduleN; gy++) {
      for (let gx = 0; gx < moduleN; gx++) {
        const v = vector[gy][gx];
        ctx.fillStyle = (v === 1) ? "#000" : "#fff";
        ctx.fillRect(gx * zoom, gy * zoom, zoom, zoom);
      }
    }
    ctx.strokeStyle = "rgba(0,0,0,0.12)";
    for (let i = 0; i <= moduleN; i++) {
      ctx.beginPath(); ctx.moveTo(0, i * zoom); ctx.lineTo(moduleN * zoom, i * zoom); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(i * zoom, 0); ctx.lineTo(i * zoom, moduleN * zoom); ctx.stroke();
    }
  }

  function cellFromEvent(evt) {
    const rect = canvas.getBoundingClientRect();
    const zoom = parseInt(zoomInput.value, 10);
    const x = evt.clientX - rect.left;
    const y = evt.clientY - rect.top;
    const gx = Math.floor(x / zoom);
    const gy = Math.floor(y / zoom);
    if (gx < 0 || gy < 0 || gx >= moduleN || gy >= moduleN) return null;
    return { gx, gy };
  }

  async function toggleAndSave(gx, gy) {
    const payload = { file: current.filename, gx, gy };
    const resp = await fetch("/api/toggle", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const r = await resp.json();
    if (!resp.ok || !r.ok) {
      setStatus(`保存失敗: ${(r && r.error) || resp.statusText}`, false);
      return;
    }
    vector[gy][gx] = r.value;
    drawAll();
    setStatus(`保存: (${gx}, ${gy}) → ${r.value}`);
  }

  canvas.addEventListener("click", (evt) => {
    const cell = cellFromEvent(evt);
    if (!cell) return;
    toggleAndSave(cell.gx, cell.gy);
  });

  zoomInput.addEventListener("input", () => {
    drawAll();
  });

  window.addEventListener("resize", () => {
    if (current) {
      origLargeEl.src = `/api/original?file=${encodeURIComponent(current.filename)}&size=${calcDisplaySize()}`;
    }
  });

  // 初期化
  loadList().then(() => {
    if (typeof PRESELECT === "string" && PRESELECT.length > 0) {
      selectFile(PRESELECT);
    }
  });
})();
