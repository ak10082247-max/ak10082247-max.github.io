# 🛡️ Kurox Sentinel: Autonomous Agent Security & Pre-Trade DEX Simulation MCP Suite

> **Canonical Manifest**: [`https://ak10082247-max.github.io/mcp_bundle_kurox.json`](https://ak10082247-max.github.io/mcp_bundle_kurox.json)  
> **Protocol**: Model Context Protocol (MCP) + x402 V2 Dual-Chain Micropayments  
> **Supported Networks**: Base Mainnet (`eip155:8453`) & Solana Mainnet (`solana:5eykt4UsFv8P8NJdTREpY1vzqKqZKvdp`)  
> **Gasless Execution**: 100% gas-sponsored via PayAI relayer / EIP-3009 transfer authorizations  

---

## ⚡ Why Autonomous Agents Need Kurox Sentinel

Autonomous trading agents and LLM copilots fail in two primary ways:
1. **Capital Loss on Malicious Swaps**: Swapping into honeypots, un-sellable tokens, 99% fee-on-transfer traps, or drained liquidity pools.
2. **Context Poisoning & Prompt Injection**: External web data or user inputs injecting hidden instructions, stealing agent wallet keys, or breaking structured JSON outputs.

**Kurox Sentinel** provides a drop-in, 4-tool perimeter defense and simulation layer that any MCP-compliant agent can invoke in real-time.

---

## 🛠️ The 4 Consolidated Tools

| Tool Name | Price (USDC) | Network | Core Capability |
| :--- | :---: | :---: | :--- |
| **`simulate_dex_trade`** | **`$0.100`** | Base & Solana | **Pre-trade state-override swap simulation**. Computes exact buy/sell transfer taxes in bps, simulates liquidity exit, and verifies LP lock contracts before broadcasting trades. |
| **`guard_agent_inputs`** | **`$0.015`** | Dual-Chain | **Deterministic prompt-injection firewall**. Neutralizes zero-width unicode smuggling, zalgo obfuscations, role-hijacking tokens (`[INST]`, `<|im_start|>`), and auto-repairs malformed JSON. |
| **`fetch_onchain_alpha`** | **`$0.050`** | Base & Solana | **Real-time whale orderflow & arbitrage radar**. Analyzes Polymarket CLOB implied probabilities vs. spot prices and tracks cross-DEX liquidity imbalances. |
| **`generate_audit_dossier`** | **`$0.150`** | Base & Solana | **7-vector institutional token security report**. Covers bytecode decompilation, holder sybil rings, dev wallet funding clusters, and bridge replay vulnerabilities. |

---

## 🚀 60-Second Setup Guide

### 1. Claude Desktop Setup
Add this block to your `claude_desktop_config.json`:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "kurox-sentinel": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://canaryguard-402.onrender.com/mcp"
      ],
      "env": {
        "X402_NETWORK": "base",
        "X402_PAYMENT_WALLET": "0x80E0Ae84679b7f11bE171DaADd492FBECf628cd6"
      }
    },
    "rugshield-simulator": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://rugshield-402.onrender.com/mcp"
      ],
      "env": {
        "X402_NETWORK": "base"
      }
    }
  }
}
```

---

### 2. Cursor / Windsurf IDE Setup
Add to `.cursor/mcp.json` or `.windsurf/mcp.json`:

```json
{
  "mcpServers": {
    "kurox-security-suite": {
      "url": "https://canaryguard-402.onrender.com/mcp",
      "transport": "sse"
    },
    "rugshield-simulator": {
      "url": "https://rugshield-402.onrender.com/mcp",
      "transport": "sse"
    }
  }
}
```

---

### 3. Coinbase AgentKit Integration
If you are running agents with `@coinbase/agentkit`:

```typescript
import { AgentKit } from "@coinbase/agentkit";
import { KuroxSecurityActionProvider } from "./COINBASE_AGENTKIT_INTEGRATION";

const agentKit = await AgentKit.from({
  actionProviders: [
    new KuroxSecurityActionProvider()
  ]
});

// Agent can now autonomously call:
// agentKit.runAction("simulate_dex_trade", { tokenAddress: "0x...", tradeAmountUsd: 1000 });
```

---

### 4. Eliza (ai16z) Autonomous Agent Integration
If you are running an autonomous Eliza character:

```typescript
import { kuroxPlugin } from "./ELIZA_PLUGIN";

export const character = {
  name: "Autonomous DeFi Sniper",
  plugins: [kuroxPlugin],
  // ...
};
```

---

## 💳 How Autonomous x402 Micropayments Work

You never need a monthly subscription or API key. Payment is settled on-demand per request:

```
[ Autonomous AI Agent ]
         │
         ▼ (1. Request Tool Execution)
[ Kurox Sentinel MCP Server ]
         │
         ▼ (2. HTTP 402: Payment Required — $0.015 to $0.100 USDC)
[ Agent Signs EIP-712 (Base) or SPL Partial Tx (Solana) ]
         │
         ▼ (3. Re-send with PAYMENT-SIGNATURE Header)
[ Coinbase CDP / PayAI Facilitator Settles On-Chain (Zero Gas for Agent) ]
         │
         ▼ (4. HTTP 200 OK: Execution Result + Cryptographic Receipt)
[ Tool Call Complete ]
```

### Authorized Merchant Settlement Addresses:
- **Base Mainnet (ERC-20 USDC)**: `0x80E0Ae84679b7f11bE171DaADd492FBECf628cd6`
- **Solana Mainnet (SPL USDC ATA)**: `DD3A7jaXFeHcif9eYj6Vhomuxypat5Yxi8ow6wxz27yL`

---

## 📜 Full Documentation & Links
- **Machine-Readable Manifest**: [`https://ak10082247-max.github.io/mcp_bundle_kurox.json`](https://ak10082247-max.github.io/mcp_bundle_kurox.json)
- **Turnkey Software Packages ($29 - $39)**: [`https://ak10082247-max.github.io/products.html`](https://ak10082247-max.github.io/products.html)
- **Support & Developer Inquiries**: `armkhan18@gmail.com`
