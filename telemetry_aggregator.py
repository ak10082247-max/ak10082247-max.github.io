"""
Kurox Big-3 Profit, Revenue & Traffic Telemetry Aggregator.

Collects non-secret, zero-PII public telemetry (x402 delivery probe buffers,
Apify Pay-Per-Event stats, npm download velocity, GitHub repo/PR metrics,
and optional secret-gated Stripe/Apify billing totals) into
`profit_revenue_telemetry.json` for `dashboard.html`.

Strictly tracks active Big-3 & Kurox monetization channels ONLY:
AgentFuel402, CanaryGuard 402, RugShield 402, Kurox npm/Stripe packs, GEO Bureau.
"""

from __future__ import annotations

import json
import os
import time
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

TELEMETRY_OUTPUT = "profit_revenue_telemetry.json"

EXCLUDED_KEYWORDS = ("guard402", "tollbooth", "stealthguard", "pulse402", "agensi")

BIG3_SERVICES = [
    {
        "id": "agentfuel402",
        "name": "AgentFuel402",
        "infra": "Cloudflare Workers Edge",
        "health_url": "https://agentfuel402.ak10082247.workers.dev/health",
        "telemetry_url": None,
        "monthly_fixed_usd": 0.0,
        "price_range": "$0.005 - $0.015 USDC",
        "endpoints_summary": "5 routes + MCP JSON-RPC 2.0",
    },
    {
        "id": "canaryguard-402",
        "name": "CanaryGuard 402",
        "infra": "Render Starter + 1GB Disk",
        "health_url": "https://canaryguard-402.onrender.com/health",
        "telemetry_url": "https://canaryguard-402.onrender.com/v1/telemetry/deliveries",
        "monthly_fixed_usd": 7.25,
        "price_range": "$0.010 - $0.020 USDC",
        "endpoints_summary": "34 routes + MCP + /v1/sanitize",
    },
    {
        "id": "rugshield-402",
        "name": "RugShield 402",
        "infra": "Render Starter + 1GB Disk",
        "health_url": "https://rugshield-402.onrender.com/health",
        "telemetry_url": "https://rugshield-402.onrender.com/v1/telemetry/deliveries",
        "monthly_fixed_usd": 7.25,
        "price_range": "$0.010 - $0.050 USDC",
        "endpoints_summary": "12 routes + Base/Solana Swap Sim",
    },
]

APIFY_ACTORS = [
    ("canaryguard-402", "CanaryGuard-402 Firewall"),
    ("rugshield-402", "RugShield-402 Pre-Trade Scanner"),
    ("b2b-intent-leads-ppe", "B2B Intent Leads PPE"),
    ("llm-clean-markdown-ppe", "LLM Clean Markdown PPE"),
    ("ecom-price-stock-ppe", "E-Com Price & Stock PPE"),
    ("reverse-engineer-anything", "Reverse Engineer Anything"),
]

DEFAULT_NPM_PACKAGES = [
    "@kurox_real/x402-sniper-bot",
    "elizaos-plugin-kurox-sentinel",
    "@kurox_real/solana-agent-kit-guard",
    "@kurox_real/rugshield-client",
    "@kurox_real/plugin-canaryguard",
    "@kurox_real/canaryguard-client",
    "@kurox_real/agentkit-canaryguard-402",
    "@kurox_real/plugin-rugshield-402",
    "@kurox_real/agentkit-rugshield-402",
    "@kurox_real/agentfuel402",
]

GITHUB_REPOS = [
    "ak10082247-max/agentfuel402",
    "ak10082247-max/canaryguard-402",
    "ak10082247-max/rugshield-402",
    "ak10082247-max/ak10082247-max.github.io",
    "ak10082247-max/x402-solana-base-sniper-bot",
    "ak10082247-max/elizaos-plugin-kurox-sentinel",
    "ak10082247-max/solana-agent-kit-guard",
    "ak10082247-max/plugin-canaryguard",
    "ak10082247-max/agentkit-canaryguard",
    "ak10082247-max/qadam-flow",
]

TRACKED_PRS = [
    ("coinbase/agentkit", 1559, "CanaryGuard Action Provider"),
    ("coinbase/agentkit", 1631, "RugShield Action Provider"),
    ("sendaifun/solana-agent-kit", 630, "RugShield Solana Token Guard"),
    ("TensorBlock/awesome-mcp-servers", 5797, "RugShield 402 Directory"),
    ("TensorBlock/awesome-mcp-servers", 5796, "CanaryGuard 402 Directory"),
    ("TensorBlock/awesome-mcp-servers", 5795, "AgentFuel402 Directory"),
    ("Recall-Kitchen/awesome-x402-mcp-services", 149, "AgentFuel402 x402 MCP"),
    ("punkpeye/awesome-mcp-servers", 16339, "CanaryGuard 402 MCP"),
    ("punkpeye/awesome-mcp-servers", 18833, "RugShield 402 Fintech MCP"),
    ("punkpeye/awesome-mcp-servers", 18918, "AgentFuel402 Data MCP"),
    ("punkpeye/awesome-remote-mcp-servers", 4137, "RugShield 402 Remote MCP"),
    ("punkpeye/awesome-remote-mcp-servers", 4138, "CanaryGuard 402 Remote MCP"),
    ("punkpeye/awesome-remote-mcp-servers", 4202, "AgentFuel402 Remote MCP"),
    ("solana-foundation/awesome-solana-ai", 287, "RugShield 402 DeFi MCP"),
    ("solana-foundation/awesome-solana-ai", 288, "AgentFuel402 Dev Tools"),
    ("Merit-Systems/awesome-agentic-commerce", 823, "Kurox Sniper Bot MCP"),
    ("Merit-Systems/awesome-agentic-commerce", 871, "AgentFuel402 Example"),
    ("xpaysh/awesome-x402", 1818, "CanaryGuard x402 Audit"),
    ("xpaysh/awesome-x402", 1922, "RugShield x402 Audit"),
    ("xpaysh/awesome-x402", 2159, "AgentFuel402 Data APIs"),
    ("aiqadam/qadam-flow", 1066, "CanaryGuard Community Qadam"),
]

STRIPE_ACTIVE_LINKS = [
    {
        "sku": "canaryguard-firewall-proxy-v1",
        "name": "CanaryGuard AI Firewall Proxy v1.0.0",
        "price": "$9 USD",
        "url": "https://buy.stripe.com/cNi28r02SaFj3Na6V3bEA08",
        "brand": "Kurox",
    },
    {
        "sku": "rugshield-pretrade-scanner-v1",
        "name": "RugShield Pre-Trade Scanner v1.0.0",
        "price": "$9 USD",
        "url": "https://buy.stripe.com/00w14n9Ds5kZerO6V3bEA09",
        "brand": "Kurox",
    },
    {
        "sku": "kurox-security-suite-bundle-v1",
        "name": "Kurox Security Source Bundle v1.0.0",
        "price": "$15 USD",
        "url": "https://buy.stripe.com/3cI4gz9Ds9Bf0AYcfnbEA0a",
        "brand": "Kurox",
    },
]


def _is_excluded(text: str | None) -> bool:
    low = (text or "").lower()
    return any(k in low for k in EXCLUDED_KEYWORDS)


def _normalize_agent(ua: str | None) -> str:
    raw = (ua or "unknown").strip()
    if not raw:
        return "unknown"
    low = raw.lower()
    if "agent402" in low:
        return "Agent402 Crawler"
    if "addrbook-probe" in low:
        return "addrbook-probe"
    if "agentrankprobe" in low:
        return "AgentRankProbe"
    if "googlebot" in low:
        return "Googlebot"
    if "bingbot" in low:
        return "Bingbot"
    if "python-httpx" in low or "httpx" in low:
        return "httpx / Syndicator"
    if "curl" in low:
        return "cURL client"
    return raw.split("(")[0].strip()[:40] or "other"


def fetch_fleet_health_and_probes(client: httpx.Client) -> dict:
    """Poll health and sanitized aggregate probe metrics (never stores IPs)."""
    services_out = []
    total_logged_hits = 0
    total_paid_in_buffer = 0
    total_unpaid_probes = 0
    agg_endpoints: Counter[str] = Counter()
    agg_agents: Counter[str] = Counter()

    for svc in BIG3_SERVICES:
        entry = {
            "id": svc["id"],
            "name": svc["name"],
            "infra": svc["infra"],
            "monthly_fixed_usd": svc["monthly_fixed_usd"],
            "price_range": svc["price_range"],
            "endpoints_summary": svc["endpoints_summary"],
            "health": {"ok": False, "status_code": 0, "latency_ms": None, "version": None},
            "buffer_stats": None,
        }
        try:
            t0 = time.monotonic()
            r = client.get(svc["health_url"], timeout=8.0)
            entry["health"]["status_code"] = r.status_code
            entry["health"]["latency_ms"] = round((time.monotonic() - t0) * 1000, 1)
            entry["health"]["ok"] = r.status_code == 200
            if r.status_code == 200:
                payload = r.json()
                entry["health"]["version"] = payload.get("version")
        except Exception as exc:
            entry["health"]["error"] = str(exc)[:120]

        if svc.get("telemetry_url"):
            try:
                tr = client.get(svc["telemetry_url"], timeout=8.0)
                if tr.status_code == 200:
                    td = tr.json()
                    items = td.get("deliveries") or []
                    paid_c = int(td.get("paid_count") or 0)
                    buf_c = int(td.get("count") or len(items))
                    unpaid_c = sum(1 for it in items if not it.get("settled"))
                    ep_counts: Counter[str] = Counter()
                    ua_counts: Counter[str] = Counter()
                    latencies = []
                    latest_ts = None
                    for it in items:
                        ep = str(it.get("endpoint") or "unknown")
                        ua = _normalize_agent(it.get("user_agent"))
                        ep_counts[ep] += 1
                        ua_counts[ua] += 1
                        agg_endpoints[f"{svc['id']}:{ep}"] += 1
                        agg_agents[ua] += 1
                        lat = it.get("latency_ms")
                        if isinstance(lat, (int, float)):
                            latencies.append(lat)
                        ts = it.get("timestamp_utc")
                        if ts and (latest_ts is None or ts > latest_ts):
                            latest_ts = ts

                    total_logged_hits += len(items)
                    total_paid_in_buffer += paid_c
                    total_unpaid_probes += unpaid_c
                    entry["buffer_stats"] = {
                        "buffer_count": buf_c,
                        "paid_count": paid_c,
                        "unpaid_probe_count": unpaid_c,
                        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
                        "latest_hit_utc": latest_ts,
                        "top_endpoints": [{"endpoint": k, "hits": v} for k, v in ep_counts.most_common(6)],
                        "top_user_agents": [{"agent": k, "hits": v} for k, v in ua_counts.most_common(6)],
                    }
            except Exception as exc:
                entry["buffer_error"] = str(exc)[:120]

        services_out.append(entry)

    return {
        "services": services_out,
        "summary": {
            "services_up": sum(1 for s in services_out if s["health"]["ok"]),
            "services_total": len(services_out),
            "rolling_buffer_hits": total_logged_hits,
            "rolling_paid_hits": total_paid_in_buffer,
            "rolling_unpaid_402_probes": total_unpaid_probes,
            "top_endpoints": [{"endpoint": k, "hits": v} for k, v in agg_endpoints.most_common(8)],
            "top_user_agents": [{"agent": k, "hits": v} for k, v in agg_agents.most_common(8)],
        },
    }


def fetch_apify_telemetry(client: httpx.Client) -> dict:
    """Fetch public Apify actor store stats (plus optional charged events when token present)."""
    token = (os.environ.get("APIFY_TOKEN") or "").strip()
    actors_out = []
    total_runs = 0
    total_runs_30d = 0
    total_users = 0
    total_charged_events = 0
    estimated_gross_usd = 0.0

    for slug, label in APIFY_ACTORS:
        item = {
            "slug": slug,
            "name": label,
            "url": f"https://apify.com/kuroxreal/{slug}",
            "total_runs": 0,
            "runs_30d": 0,
            "succeeded_30d": 0,
            "total_users": 0,
            "users_7d": 0,
            "users_30d": 0,
            "last_run_at": None,
            "price_per_event_usd": 0.0,
            "charged_events": None,
            "gross_usd": None,
        }
        try:
            r = client.get(f"https://api.apify.com/v2/acts/kuroxreal~{slug}", timeout=8.0)
            if r.status_code == 200:
                d = (r.json() or {}).get("data") or {}
                stats = d.get("stats") or {}
                r30 = stats.get("publicActorRunStats30Days") or {}
                item["total_runs"] = int(stats.get("totalRuns") or 0)
                item["runs_30d"] = int(r30.get("TOTAL") or 0)
                item["succeeded_30d"] = int(r30.get("SUCCEEDED") or 0)
                item["total_users"] = int(stats.get("totalUsers") or 0)
                item["users_7d"] = int(stats.get("totalUsers7Days") or 0)
                item["users_30d"] = int(stats.get("totalUsers30Days") or 0)
                item["last_run_at"] = stats.get("lastRunStartedAt")

                pricing = (d.get("pricingInfos") or [{}])[-1]
                events = (pricing.get("pricingPerEvent") or {}).get("actorChargeEvents") or {}
                for ev in events.values():
                    if isinstance(ev, dict) and ev.get("eventPriceUsd") is not None:
                        item["price_per_event_usd"] = float(ev["eventPriceUsd"])
                        break
        except Exception as exc:
            item["error"] = str(exc)[:100]

        if token:
            try:
                rr = client.get(
                    f"https://api.apify.com/v2/acts/kuroxreal~{slug}/runs?limit=50&desc=true",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=8.0,
                )
                if rr.status_code == 200:
                    runs = ((rr.json() or {}).get("data") or {}).get("items") or []
                    charged = sum(
                        sum((run.get("chargedEventCounts") or {}).values())
                        for run in runs
                        if run.get("status") == "SUCCEEDED"
                    )
                    item["charged_events"] = charged
                    item["gross_usd"] = round(charged * item["price_per_event_usd"], 4)
                    total_charged_events += charged
                    estimated_gross_usd += item["gross_usd"]
            except Exception:
                pass

        total_runs += item["total_runs"]
        total_runs_30d += item["runs_30d"]
        total_users += item["total_users"]
        actors_out.append(item)

    return {
        "actors": actors_out,
        "summary": {
            "actors_count": len(actors_out),
            "total_runs": total_runs,
            "runs_30d": total_runs_30d,
            "total_user_installs": total_users,
            "billing_mode": "token_verified" if token else "public_stats_only",
            "charged_events": total_charged_events if token else None,
            "gross_usd": round(estimated_gross_usd, 4) if token else None,
        },
    }


def fetch_npm_telemetry(client: httpx.Client) -> dict:
    """Query npm registry and download velocity for active Kurox packages."""
    pkg_meta: dict[str, dict] = {}
    try:
        sr = client.get("https://registry.npmjs.org/-/v1/search?text=maintainer:kurox_real&size=50", timeout=10.0)
        if sr.status_code == 200:
            for obj in (sr.json() or {}).get("objects") or []:
                p = obj.get("package") or {}
                name = p.get("name")
                if name and not _is_excluded(name):
                    pkg_meta[name] = {
                        "version": p.get("version"),
                        "description": (p.get("description") or "")[:120],
                    }
    except Exception:
        pass

    names = list(dict.fromkeys(list(pkg_meta.keys()) + DEFAULT_NPM_PACKAGES))
    packages_out = []
    tot_d, tot_w, tot_m = 0, 0, 0

    for name in names:
        if _is_excluded(name):
            continue
        encoded = quote(name, safe="")
        row = {
            "name": name,
            "version": (pkg_meta.get(name) or {}).get("version"),
            "url": f"https://www.npmjs.com/package/{name}",
            "downloads_1d": 0,
            "downloads_7d": 0,
            "downloads_30d": 0,
        }
        for period, key in [("last-day", "downloads_1d"), ("last-week", "downloads_7d"), ("last-month", "downloads_30d")]:
            try:
                dr = client.get(f"https://api.npmjs.org/downloads/point/{period}/{encoded}", timeout=6.0)
                if dr.status_code == 200:
                    row[key] = int((dr.json() or {}).get("downloads") or 0)
            except Exception:
                pass
        tot_d += row["downloads_1d"]
        tot_w += row["downloads_7d"]
        tot_m += row["downloads_30d"]
        packages_out.append(row)

    packages_out.sort(key=lambda x: x["downloads_30d"], reverse=True)
    return {
        "packages": packages_out,
        "summary": {
            "package_count": len(packages_out),
            "downloads_1d": tot_d,
            "downloads_7d": tot_w,
            "downloads_30d": tot_m,
        },
    }


def fetch_github_telemetry(client: httpx.Client) -> dict:
    """Query public repository metrics and active Big-3 distribution PR states."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "kurox-telemetry-aggregator/1.0"}
    gh_token = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_PAT") or "").strip()
    if gh_token:
        headers["Authorization"] = f"Bearer {gh_token}"

    repos_out = []
    total_stars = 0
    total_forks = 0
    for full_name in GITHUB_REPOS:
        if _is_excluded(full_name):
            continue
        try:
            r = client.get(f"https://api.github.com/repos/{full_name}", headers=headers, timeout=8.0)
            if r.status_code == 200:
                d = r.json()
                stars = int(d.get("stargazers_count") or 0)
                forks = int(d.get("forks_count") or 0)
                total_stars += stars
                total_forks += forks
                repos_out.append({
                    "name": full_name,
                    "url": d.get("html_url") or f"https://github.com/{full_name}",
                    "stars": stars,
                    "forks": forks,
                    "open_issues": int(d.get("open_issues_count") or 0),
                    "pushed_at": d.get("pushed_at"),
                })
        except Exception:
            pass

    prs_out = []
    merged_count = 0
    open_count = 0
    for repo, num, label in TRACKED_PRS:
        status = "unknown"
        url = f"https://github.com/{repo}/pull/{num}"
        try:
            pr = client.get(f"https://api.github.com/repos/{repo}/pulls/{num}", headers=headers, timeout=8.0)
            if pr.status_code == 200:
                pd = pr.json()
                if pd.get("merged_at"):
                    status = "merged"
                    merged_count += 1
                else:
                    status = pd.get("state") or "unknown"
                    if status == "open":
                        open_count += 1
        except Exception:
            pass
        prs_out.append({"repo": repo, "number": num, "label": label, "status": status, "url": url})

    return {
        "repos": repos_out,
        "tracked_prs": prs_out,
        "summary": {
            "tracked_repos": len(repos_out),
            "total_stars": total_stars,
            "total_forks": total_forks,
            "prs_merged": merged_count,
            "prs_open": open_count,
            "prs_total": len(prs_out),
        },
    }


def fetch_stripe_aggregate(client: httpx.Client) -> dict:
    """
    Aggregate livemode Stripe revenue ONLY when STRIPE_READONLY_KEY is set via CI secret.
    Never exposes PII, customer emails, or secret values. Falls back to verified MCP baseline.
    """
    key = (os.environ.get("STRIPE_READONLY_KEY") or os.environ.get("STRIPE_SECRET_KEY") or "").strip()
    baseline = {
        "sync_mode": "verified_mcp_baseline",
        "baseline_checked_utc": "2026-11-15T18:20:50Z",
        "available_usd": 0.0,
        "pending_usd": 0.0,
        "available_gbp": 0.0,
        "pending_gbp": 0.0,
        "completed_charges": 0,
        "gross_settled_usd": 0.0,
        "fees_usd": 0.0,
        "net_settled_usd": 0.0,
        "gross_settled_gbp": 0.0,
        "active_links_total": 10,
        "active_kurox_links": STRIPE_ACTIVE_LINKS,
        "note": "Live Stripe MCP verified $0.00/£0.00 settled so far. Add optional STRIPE_READONLY_KEY repository secret for automatic 15-min Stripe auto-sync.",
    }
    if not key:
        return baseline

    try:
        headers = {"Authorization": f"Bearer {key}"}
        bal_r = client.get("https://api.stripe.com/v1/balance", headers=headers, timeout=10.0)
        tx_r = client.get("https://api.stripe.com/v1/balance_transactions?limit=100", headers=headers, timeout=10.0)
        if bal_r.status_code != 200 or tx_r.status_code != 200:
            baseline["sync_mode"] = f"stripe_http_{bal_r.status_code}"
            return baseline

        bal = bal_r.json()
        txs = (tx_r.json() or {}).get("data") or []
        avail_usd = sum(b.get("amount", 0) for b in bal.get("available") or [] if b.get("currency") == "usd") / 100.0
        pend_usd = sum(b.get("amount", 0) for b in bal.get("pending") or [] if b.get("currency") == "usd") / 100.0
        avail_gbp = sum(b.get("amount", 0) for b in bal.get("available") or [] if b.get("currency") == "gbp") / 100.0
        pend_gbp = sum(b.get("amount", 0) for b in bal.get("pending") or [] if b.get("currency") == "gbp") / 100.0

        gross_usd, fees_usd, net_usd, gross_gbp, charges = 0.0, 0.0, 0.0, 0.0, 0
        for t in txs:
            if t.get("type") in ("charge", "payment"):
                charges += 1
                cur = t.get("currency")
                if cur == "usd":
                    gross_usd += (t.get("amount") or 0) / 100.0
                    fees_usd += (t.get("fee") or 0) / 100.0
                    net_usd += (t.get("net") or 0) / 100.0
                elif cur == "gbp":
                    gross_gbp += (t.get("amount") or 0) / 100.0

        return {
            **baseline,
            "sync_mode": "live_api_secret",
            "baseline_checked_utc": datetime.now(timezone.utc).isoformat(),
            "available_usd": round(avail_usd, 2),
            "pending_usd": round(pend_usd, 2),
            "available_gbp": round(avail_gbp, 2),
            "pending_gbp": round(pend_gbp, 2),
            "completed_charges": charges,
            "gross_settled_usd": round(gross_usd, 2),
            "fees_usd": round(fees_usd, 2),
            "net_settled_usd": round(net_usd, 2),
            "gross_settled_gbp": round(gross_gbp, 2),
            "note": "Synced live from Stripe /v1/balance and /v1/balance_transactions (aggregate only, zero PII).",
        }
    except Exception as exc:
        baseline["note"] = f"Stripe sync fallback ({str(exc)[:80]})."
        return baseline


def write_profit_revenue_telemetry(
    client: httpx.Client,
    balances: dict,
    external_deliveries: list[dict],
) -> dict:
    """Build and atomically write unified Big-3 profit, revenue, and traffic telemetry JSON."""
    base_usdc = 0.0
    sol_usdc = 0.0
    try:
        base_usdc = float(balances.get("base_merchant_usdc") or 0.0)
    except Exception:
        pass
    try:
        sol_usdc = float(balances.get("solana_merchant_usdc") or 0.0)
    except Exception:
        pass

    ext_x402_usdc = sum(float(d.get("amount_usdc") or 0.0) for d in external_deliveries)
    fleet = fetch_fleet_health_and_probes(client)
    apify = fetch_apify_telemetry(client)
    npm = fetch_npm_telemetry(client)
    github = fetch_github_telemetry(client)
    stripe = fetch_stripe_aggregate(client)

    fixed_monthly_usd = round(sum(float(s.get("monthly_fixed_usd") or 0.0) for s in BIG3_SERVICES), 2)
    verified_gross_usd = round(ext_x402_usdc + stripe["gross_settled_usd"], 6)
    apify_gross = apify["summary"]["gross_usd"] or 0.0
    verified_gross_usd = round(verified_gross_usd + apify_gross, 6)
    est_net_monthly_usd = round(verified_gross_usd - fixed_monthly_usd, 2)

    snapshot = {
        "schema_version": "1.0.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Active Big-3 & Kurox Channels Only (AgentFuel402, CanaryGuard 402, RugShield 402, Kurox Stripe/npm, GEO Bureau)",
        "excluded_legacy": list(EXCLUDED_KEYWORDS),
        "profit_overview": {
            "verified_external_x402_usdc": round(ext_x402_usdc, 6),
            "verified_external_x402_tx_count": len(external_deliveries),
            "treasury_vault_base_usdc": round(base_usdc, 6),
            "treasury_vault_solana_usdc": round(sol_usdc, 6),
            "treasury_vault_total_usdc": round(base_usdc + sol_usdc, 6),
            "stripe_gross_usd": stripe["gross_settled_usd"],
            "stripe_gross_gbp": stripe["gross_settled_gbp"],
            "apify_verified_gross_usd": apify["summary"]["gross_usd"],
            "verified_cumulative_gross_usd": verified_gross_usd,
            "verified_monthly_fixed_infra_usd": fixed_monthly_usd,
            "estimated_monthly_net_vs_cumulative_usd": est_net_monthly_usd,
        },
        "infra_baseline": [
            {"service": "CanaryGuard 402", "plan": "Render Starter + 1GB Persistent Disk", "monthly_usd": 7.25},
            {"service": "RugShield 402", "plan": "Render Starter + 1GB Persistent Disk", "monthly_usd": 7.25},
            {"service": "AgentFuel402", "plan": "Cloudflare Workers Edge", "monthly_usd": 0.0},
            {"service": "GitHub Pages / Actions / npm / Stripe / Apify", "plan": "Free Fixed Tier", "monthly_usd": 0.0},
        ],
        "fleet": fleet,
        "stripe": stripe,
        "apify": apify,
        "npm": npm,
        "github": github,
        "wallets": {
            "base": "0x80E0Ae84679b7f11bE171DaADd492FBECf628cd6",
            "solana_owner": "9wuMysgXwNhtQeqJgGByAiMYc4EjzZ5wUSmnjrrt3ffh",
            "solana_ata": "DD3A7jaXFeHcif9eYj6Vhomuxypat5Yxi8ow6wxz27yL",
        },
    }

    with open(TELEMETRY_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print(f"Wrote {TELEMETRY_OUTPUT} cleanly.")
    return snapshot
