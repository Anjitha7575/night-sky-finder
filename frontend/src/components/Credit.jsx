import { useState } from "react";
import { Copy } from "./Icons";

const EMAIL = "anjd137@gmail.com";

export default function Credit() {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(EMAIL);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard blocked (e.g. not https): the mail link still works
    }
  }

  return (
    <div className="credit">
      Made by <b>Anjitha D</b>
      <span aria-hidden="true">·</span>
      <a href={`mailto:${EMAIL}`}>{EMAIL}</a>
      <button onClick={copy} aria-label="Copy email address" title={copied ? "Copied" : "Copy email"}>
        {copied ? "✓" : <Copy />}
      </button>
    </div>
  );
}
