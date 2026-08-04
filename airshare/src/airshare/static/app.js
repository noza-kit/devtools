(() => {
  const code = window.AIRSHARE_CODE || "";
  const authHeaders = code ? { "X-AirShare-Code": code } : {};
  const withCode = (url) => (code ? `${url}${url.includes("?") ? "&" : "?"}code=${encodeURIComponent(code)}` : url);

  const fileInput = document.getElementById("file-input");
  const pickButton = document.getElementById("pick-button");
  const dropZone = document.getElementById("drop-zone");
  const uploadStatus = document.getElementById("upload-status");
  const fileList = document.getElementById("file-list");
  const refreshButton = document.getElementById("refresh-button");

  function formatSize(bytes) {
    const units = ["B", "KB", "MB", "GB"];
    let value = bytes;
    let unitIndex = 0;
    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024;
      unitIndex += 1;
    }
    return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
  }

  async function refreshFiles() {
    try {
      const response = await fetch(withCode("/api/files"), { headers: authHeaders });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const entries = await response.json();
      renderFiles(entries);
    } catch (err) {
      fileList.innerHTML = '<li class="empty">読み込みに失敗しました</li>';
    }
  }

  function renderFiles(entries) {
    if (entries.length === 0) {
      fileList.innerHTML = '<li class="empty">ファイルはありません</li>';
      return;
    }
    fileList.innerHTML = "";
    for (const entry of entries) {
      const li = document.createElement("li");
      const link = document.createElement("a");
      link.href = withCode(`/api/files/${encodeURIComponent(entry.name)}`);
      link.className = "file-link";
      link.textContent = entry.name;
      const meta = document.createElement("span");
      meta.className = "file-meta";
      meta.textContent = formatSize(entry.size);
      li.appendChild(link);
      li.appendChild(meta);
      fileList.appendChild(li);
    }
  }

  async function uploadFiles(files) {
    if (!files || files.length === 0) return;
    uploadStatus.textContent = `アップロード中... (0/${files.length})`;
    let done = 0;
    for (const file of files) {
      const form = new FormData();
      form.append("file", file);
      try {
        const response = await fetch(withCode("/api/upload"), {
          method: "POST",
          headers: authHeaders,
          body: form,
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        done += 1;
        uploadStatus.textContent = `アップロード中... (${done}/${files.length})`;
      } catch (err) {
        uploadStatus.textContent = `アップロード失敗: ${file.name}`;
        return;
      }
    }
    uploadStatus.textContent = `${done}件アップロードしました`;
  }

  pickButton.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    uploadFiles(fileInput.files);
    fileInput.value = "";
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.add("drag-active");
    });
  });
  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropZone.classList.remove("drag-active");
    });
  });
  dropZone.addEventListener("drop", (event) => {
    const files = event.dataTransfer && event.dataTransfer.files;
    uploadFiles(files);
  });

  refreshButton.addEventListener("click", refreshFiles);

  refreshFiles();
  setInterval(refreshFiles, 5000);
})();
