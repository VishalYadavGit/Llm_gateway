# Frontend Integration Guide

Use this guide to integrate LLM Gateway into any website with existing HTML elements.

Gateway domain:
- `https://ai.devlooper.in`

## Required Element IDs

Set these IDs in your HTML:
- `llm-gateway-input` for your `<input>` or `<textarea>`
- `llm-gateway-send` for your send button
- `llm-gateway-output` for where the answer will render
- `llm-gateway-status` (optional) for status/errors

## 2-5 Line Integration

```html
<!-- Required IDs: llm-gateway-input, llm-gateway-send, llm-gateway-output, llm-gateway-status(optional) -->
<textarea id="llm-gateway-input"></textarea><button id="llm-gateway-send">Send</button><pre id="llm-gateway-output"></pre><small id="llm-gateway-status"></small>
<script src="https://ai.devlooper.in/assets/embed.js"></script>
<script>LLMGateway.bind({ inputId: "llm-gateway-input", sendButtonId: "llm-gateway-send", outputId: "llm-gateway-output", statusId: "llm-gateway-status" });</script>
```

## Notes

- Your website origin must be configured as the project's `allowed_origin` in LLM Gateway.
- The SDK automatically calls:
  - `GET /v1/auth/token`
  - `POST /v1/query`
- If your API is not on the same domain as the script, pass `apiBase`:

```html
<script>
  LLMGateway.bind({
    inputId: "llm-gateway-input",
    sendButtonId: "llm-gateway-send",
    outputId: "llm-gateway-output",
    statusId: "llm-gateway-status",
    apiBase: "https://ai.devlooper.in"
  });
</script>
```
