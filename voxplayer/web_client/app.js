(function () {
  "use strict";

  var baseEl = document.getElementById("base");
  var titleEl = document.getElementById("title");
  var metaEl = document.getElementById("meta");
  var errEl = document.getElementById("err");
  var pathEl = document.getElementById("path");
  var lastStatus = { volume_percent: 50 };

  function baseUrl() {
    return (baseEl.value || "http://127.0.0.1:17890").replace(/\/$/, "");
  }

  function basename(p) {
    if (!p) return "(nothing loaded)";
    var parts = String(p).split(/[/\\]/);
    return parts[parts.length - 1] || p;
  }

  function fmtMs(ms) {
    ms = Math.max(0, parseInt(ms, 10) || 0);
    var sec = Math.floor(ms / 1000);
    var m = Math.floor(sec / 60);
    var s = sec % 60;
    var h = Math.floor(m / 60);
    m = m % 60;
    if (h) return h + ":" + String(m).padStart(2, "0") + ":" + String(s).padStart(2, "0");
    return m + ":" + String(s).padStart(2, "0");
  }

  function request(method, path, body) {
    var opts = {
      method: method,
      headers: { Accept: "application/json" },
    };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    return fetch(baseUrl() + path, opts).then(function (res) {
      return res.json().catch(function () {
        return { ok: res.ok };
      });
    });
  }

  function showError(e) {
    errEl.textContent = e ? String(e) : "";
  }

  function render(st) {
    lastStatus = st || lastStatus;
    if (st && st.error) {
      titleEl.textContent = "Daemon unreachable";
      metaEl.textContent = "";
      showError(st.error);
      return;
    }
    showError("");
    var playing = st.playing ? "PLAYING" : "PAUSED";
    titleEl.textContent = "[" + playing + "] " + basename(st.path);
    metaEl.textContent =
      fmtMs(st.position_ms) +
      " / " +
      fmtMs(st.duration_ms) +
      " · vol " +
      (st.volume_percent || 0) +
      "%" +
      (st.version ? " · v" + st.version : "");
  }

  function refresh() {
    return request("GET", "/status")
      .then(render)
      .catch(function (e) {
        render({ error: e.message || String(e) });
      });
  }

  function act(name) {
    var p;
    if (name === "refresh") return refresh();
    if (name === "vol-up") {
      p = request("POST", "/volume", {
        percent: Math.min(200, (lastStatus.volume_percent || 50) + 5),
      });
    } else if (name === "vol-down") {
      p = request("POST", "/volume", {
        percent: Math.max(0, (lastStatus.volume_percent || 50) - 5),
      });
    } else if (name === "seek-back") {
      p = request("POST", "/seek", { relative_ms: -5000 });
    } else if (name === "seek-fwd") {
      p = request("POST", "/seek", { relative_ms: 5000 });
    } else if (name === "open") {
      var path = (pathEl.value || "").trim();
      if (!path) {
        showError("path required");
        return;
      }
      p = request("POST", "/open", { path: path });
    } else {
      p = request("POST", "/" + name, {});
    }
    p.then(function () {
      return refresh();
    }).catch(function (e) {
      showError(e.message || String(e));
    });
  }

  document.querySelectorAll("button[data-act]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      act(btn.getAttribute("data-act"));
    });
  });
  baseEl.addEventListener("change", refresh);
  refresh();
  setInterval(refresh, 1000);
})();
