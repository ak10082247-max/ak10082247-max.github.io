# 🛡️ Kurox Big 3 x402 Suite: Data Feeds, AI Firewall & Pre-Trade DEX Simulation

> **Canonical Manifest**: [`https://ak10082247-max.github.io/mcp_bundle_kurox.json`](https://ak10082247-max.github.io/mcp_bundle_kurox.json)  
> **Protocol**: Model Context Protocol (MCP) + x402 V2 Dual-Chain Micropayments + Apify Store (Credit Card)  
> **Supported Networks**: Base Mainnet (`eip155:8453`) & Solana Mainnet (`solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp`)  
> **Gasless Execution**: 100% gas-sponsored via Coinbase CDP / PayAI relayer (`EIP-3009` & `TransferChecked`)

---

## 🛠️ The Big 3 Production Services

| Service / Tool | Price (USDC) | Rail / Access | Core Capability |
| :--- | :---: | :--- | :--- |
| **`AgentFuel402`** (`b2b_intent_leads`, `llm_clean_markdown`, `ecom_price_stock`, `sdk_live_spec`, `reverse_engineer`) | **`$0.005 – $0.020`** | Base & Solana (`x402`), **`$5.00` Agency Pass**, Apify (Card), Glama MCP | Cloudflare Edge B2B intent leads, RAG-safe Markdown, e-commerce price/stock, live SDK diffs, and hidden API schema discovery. |
| **`CanaryGuard 402`** (`guard_agent_inputs`) | **`$0.015 – $0.020`** | Base & Solana (`x402`), Apify (Card), Remote MCP | Deterministic `<0.1ms` prompt-injection firewall, unicode smuggling sanitizer, MCP tool-poisoning audit, and EIP-712 signer audit. |
| **`RugShield 402`** (`simulate_dex_trade`) | **`$0.010 – $0.020`** | Base & Solana (`x402`), Apify (Card), Remote MCP | Pre-trade DEX honeypot calldata simulation, buy/sell tax estimation, LP lock check, and insider Sybil holder clustering. |

---

## 🚀 60-Second MCP Setup

Add all three flagship servers to `claude_desktop_config.json`, `.cursor/mcp.json`, or `.windsurf/mcp.json`:

```json
{
  "mcpServers": {
    "agentfuel402": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://agentfuel402.ak10082247.workers.dev/mcp"]
    },
    "canaryguard-402": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://canaryguard-402.onrender.com/mcp"]
    },
    "rugshield-402": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://rugshield-402.onrender.com/mcp"]
    }
  }
}
```

Or install AgentFuel402 directly from Glama:
- [`https://glama.ai/mcp/servers/ak10082247-max/agentfuel402`](https://glama.ai/mcp/servers/ak10082247-max/agentfuel402)

---

## 💳 Credit Card (Apify Store) or `$5.00` USDC Agency Pass

- **No crypto wallet needed?** Run any of the 6 live actors on [Apify Store (`kuroxreal`)](https://apify.com/kuroxreal) using a credit card or free monthly Apify credits.
- **High-volume teams?** Mint a 1,000-call prepaid key (`$5.00 USDC` one-time = `$0.005`/call) via `POST https://agentfuel402.ak10082247.workers.dev/v1/pass/prepay`.

### Authorized Merchant Settlement Addresses
- **Base Mainnet (ERC-20 USDC)**: `0x80E0Ae84679b7f11bE171DaADd492FBECf628cd6`
- **Solana Mainnet (Owner)**: `9wuMysgXwNhtQeqJgGByAiMYc4EjzZ5wUSmnjrrt3ffh`
- **Solana Mainnet (SPL USDC ATA)**: `DD3A7jaXFeHcif9eYj6Vhomuxypat5Yxi8ow6wxz27yL`

---

## 📜 Links & Support
- **Storefront Directory**: [`https://ak10082247-max.github.io`](https://ak10082247-max.github.io)
- **Machine-Readable Manifest**: [`https://ak10082247-max.github.io/mcp_bundle_kurox.json`](https://ak10082247-max.github.io/mcp_bundle_kurox.json)
- **Support**: `armkhan18@gmail.com`
