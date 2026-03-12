(function () {
  "use strict";

  var DEFAULTS = {
    apiBase: "",
    inputId: "llm-gateway-input",
    sendButtonId: "llm-gateway-send",
    outputId: "llm-gateway-output",
    statusId: "llm-gateway-status",
    topK: 6,
    stream: false,
  };

  var tokenCache = {
    token: "",
    expMs: 0,
  };

  function parseJwtExpMs(token) {
    try {
      var parts = token.split(".");
      if (parts.length !== 3) {
        return 0;
      }
      var payload = JSON.parse(atob(parts[1]));
      if (!payload || typeof payload.exp !== "number") {
        return 0;
      }
      return payload.exp * 1000;
    } catch (_err) {
      return 0;
    }
  }

  function getScriptOrigin() {
    if (document.currentScript && document.currentScript.src) {
      try {
        return new URL(document.currentScript.src).origin;
      } catch (_err) {
        return "";
      }
    }

    var scripts = document.getElementsByTagName("script");
    var last = scripts[scripts.length - 1];
    if (last && last.src) {
      try {
        return new URL(last.src).origin;
      } catch (_err) {
        return "";
      }
    }

    return "";
  }

  function resolveApiBase(apiBase) {
    var trimmed = (apiBase || "").trim();
    if (trimmed) {
      return trimmed.replace(/\/$/, "");
    }
    return getScriptOrigin();
  }

  function isTokenValid() {
    if (!tokenCache.token || !tokenCache.expMs) {
      return false;
    }
    return Date.now() < tokenCache.expMs - 5000;
  }

  async function fetchToken(apiBase) {
    if (isTokenValid()) {
      return tokenCache.token;
    }

    var response = await fetch(apiBase + "/v1/auth/token", {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      var detail = await response.text();
      throw new Error(detail || "Failed to fetch token");
    }

    var data = await response.json();
    tokenCache.token = data.access_token || "";
    tokenCache.expMs = parseJwtExpMs(tokenCache.token);
    return tokenCache.token;
  }

  async function sendQuery(opts, queryText) {
    var apiBase = resolveApiBase(opts.apiBase);
    var token = await fetchToken(apiBase);

    var response = await fetch(apiBase + "/v1/query", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer " + token,
      },
      body: JSON.stringify({
        query: queryText,
        top_k: opts.topK,
        stream: Boolean(opts.stream),
      }),
    });

    if (!response.ok) {
      var detail = await response.text();
      throw new Error(detail || "Query request failed");
    }

    if (!opts.stream) {
      var payload = await response.json();
      return {
        answer: payload.answer || "",
        context_chunks: payload.context_chunks || [],
      };
    }

    var reader = response.body && response.body.getReader ? response.body.getReader() : null;
    if (!reader) {
      throw new Error("Streaming is not supported in this browser");
    }

    var decoder = new TextDecoder();
    var done = false;
    var aggregate = "";
    while (!done) {
      var part = await reader.read();
      done = part.done;
      if (!done && part.value) {
        aggregate += decoder.decode(part.value, { stream: true });
      }
    }
    aggregate += decoder.decode();

    var lines = aggregate.split("\n");
    var content = [];
    for (var i = 0; i < lines.length; i += 1) {
      var line = lines[i].trim();
      if (line.indexOf("data:") === 0) {
        content.push(line.slice(5).trim());
      }
    }

    return {
      answer: content.join("\n"),
      context_chunks: [],
    };
  }

  function getRequiredElement(id, label) {
    var el = document.getElementById(id);
    if (!el) {
      throw new Error(label + " element not found: #" + id);
    }
    return el;
  }

  function bind(userOptions) {
    var opts = Object.assign({}, DEFAULTS, userOptions || {});
    var input = getRequiredElement(opts.inputId, "Input");
    var button = getRequiredElement(opts.sendButtonId, "Send button");
    var output = getRequiredElement(opts.outputId, "Output");
    var status = opts.statusId ? document.getElementById(opts.statusId) : null;

    if (!(input instanceof HTMLInputElement || input instanceof HTMLTextAreaElement)) {
      throw new Error("Input must be <input> or <textarea>");
    }

    function setStatus(text) {
      if (status) {
        status.textContent = text;
      }
    }

    async function handleSend() {
      var queryText = input.value.trim();
      if (!queryText) {
        setStatus("Type a question first.");
        return;
      }

      button.disabled = true;
      setStatus("Thinking...");

      try {
        var result = await sendQuery(opts, queryText);
        output.textContent = result.answer || "(No answer)";
        setStatus("Done");
      } catch (err) {
        output.textContent = "";
        setStatus(err && err.message ? err.message : "Request failed");
      } finally {
        button.disabled = false;
      }
    }

    function clickHandler() {
      handleSend();
    }

    function keydownHandler(event) {
      if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
        handleSend();
      }
    }

    button.addEventListener("click", clickHandler);
    input.addEventListener("keydown", keydownHandler);

    return {
      query: function (text) {
        input.value = text || "";
        return handleSend();
      },
      destroy: function () {
        button.removeEventListener("click", clickHandler);
        input.removeEventListener("keydown", keydownHandler);
      },
    };
  }

  window.LLMGateway = {
    bind: bind,
    query: function (queryText, options) {
      return sendQuery(Object.assign({}, DEFAULTS, options || {}), queryText);
    },
  };
})();
