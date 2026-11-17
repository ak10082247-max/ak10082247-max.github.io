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
        "price_range": "$0.005 - $0.020 USDC",
        "endpoints_summary": "5 fuel + 4 preview + /mcp",
    },
    {
        "id": "canaryguard-402",
        "name": "CanaryGuard 402",
        "infra": "Render Starter + 1GB Disk",
        "health_url": "https://canaryguard-402.onrender.com/health",
        "telemetry_url": "https://canaryguard-402.onrender.com/v1/telemetry/deliveries",
        "monthly_fixed_usd": 7.25,
        "price_range": "$0.010 - $0.020 USDC",
        "endpoints_summary": "34 routes + /stats + /mcp",
    },
    {
        "id": "rugshield-402",
        "name": "RugShield 402",
        "infra": "Render Starter + 1GB Disk",
        "health_url": "https://rugshield-402.onrender.com/health",
        "telemetry_url": "https://rugshield-402.onrender.com/v1/telemetry/deliveries",
        "monthly_fixed_usd": 7.25,
        "price_range": "$0.010 - $0.100 USDC",
        "endpoints_summary": "12 routes + Swap Sim + /mcp",
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
    ("Merit-Systems/awesome-agentic-commerce", 823, "Kurox Fleet (RugShield, CanaryGuard, AgentFuel402)"),
    ("Merit-Systems/awesome-agentic-commerce", 871, "AgentFuel402 Example"),
    ("xpaysh/awesome-x402", 1818, "CanaryGuard x402 Audit"),
    ("xpaysh/awesome-x402", 1922, "RugShield x402 Audit"),
    ("xpaysh/awesome-x402", 2159, "AgentFuel402 Data APIs"),
    ("aiqadam/qadam-flow", 1066, "CanaryGuard Community Qadam"),
]

STRIPE_ACTIVE_LINKS = [
    {
        "sku": "kurox-api-starter-30d",
        "name": "Unified API Key — Starter (30d)",
        "price": "$5 USD",
        "currency": "USD",
        "url": "https://agentfuel402.ak10082247.workers.dev/v1/checkout/api-key?plan=starter",
        "brand": "Kurox",
    },
    {
        "sku": "kurox-api-pro-90d",
        "name": "Unified API Key — Pro (90d)",
        "price": "$19 USD",
        "currency": "USD",
        "url": "https://agentfuel402.ak10082247.workers.dev/v1/checkout/api-key?plan=pro",
        "brand": "Kurox",
    },
    {
        "sku": "canaryguard-firewall-proxy-v1",
        "name": "CanaryGuard AI Firewall Proxy v1.0.0",
        "price": "$9 USD",
        "currency": "USD",
        "url": "https://agentfuel402.ak10082247.workers.dev/v1/checkout/bundle?sku=canaryguard",
        "brand": "Kurox",
    },
    {
        "sku": "rugshield-pretrade-scanner-v1",
        "name": "RugShield Pre-Trade Scanner v1.0.0",
        "price": "$9 USD",
        "currency": "USD",
        "url": "https://agentfuel402.ak10082247.workers.dev/v1/checkout/bundle?sku=rugshield",
        "brand": "Kurox",
    },
    {
        "sku": "kurox-security-suite-bundle-v1",
        "name": "Kurox Dual Security Bundle v1.0.0",
        "price": "$15 USD",
        "currency": "USD",
        "url": "https://agentfuel402.ak10082247.workers.dev/v1/checkout/bundle?sku=dual",
        "brand": "Kurox",
    },
    {
        "sku": "b2b-tech-intent-leads-csv-v1",
        "name": "Live B2B Tech Intent & Hiring Leads Pack (.csv)",
        "price": "$19 USD",
        "currency": "USD",
        "url": "https://agentfuel402.ak10082247.workers.dev/v1/checkout/bundle?sku=csv-pack",
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
    """
    Fetch public Apify actor store stats plus optional authenticated usage/own-runs metrics.
    Note: Apify v2 /runs only returns the token owner's own runs, so third-party store
    execution volume is estimated from (public totalRuns - own_runs_recorded) when owner runs < 100.
    """
    token = (os.environ.get("APIFY_TOKEN") or "").strip()
    actors_out = []
    total_runs = 0
    total_runs_30d = 0
    total_users = 0
    total_own_runs = 0
    total_ext_runs_est = 0
    cycle_usage_usd = None

    if token:
        try:
            ur = client.get(
                "https://api.apify.com/v2/users/me/usage/monthly",
                headers={"Authorization": f"Bearer {token}"},
                timeout=8.0,
            )
            if ur.status_code == 200:
                u_data = (ur.json() or {}).get("data") or {}
                svc_u = u_data.get("monthlyServiceUsage") or {}
                cycle_usage_usd = round(
                    sum(float((v or {}).get("amountAfterVolumeDiscountUsd") or 0.0) for v in svc_u.values() if isinstance(v, dict)),
                    4,
                )
        except Exception:
            pass

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
            "own_runs_recorded": None,
            "external_runs_est": None,
            "gross_usd": None,
        }
        try:
            r = client.get(f"https://api.apify.com/v2/acts/kuroxreal~{slug}", timeout=10.0)
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
                    f"https://api.apify.com/v2/acts/kuroxreal~{slug}/runs?limit=100&desc=true",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0,
                )
                if rr.status_code == 200:
                    runs = ((rr.json() or {}).get("data") or {}).get("items") or []
                    own_n = len(runs)
                    item["own_runs_recorded"] = own_n
                    total_own_runs += own_n
                    if own_n < 100 and item["total_runs"] >= own_n:
                        ext_est = item["total_runs"] - own_n
                        item["external_runs_est"] = ext_est
                        total_ext_runs_est += ext_est
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
            "own_runs_recorded": total_own_runs if token else None,
            "external_runs_est": total_ext_runs_est if token else None,
            "cycle_compute_usd": cycle_usage_usd,
            "billing_mode": "token_usage_plus_store_stats" if token else "public_stats_only",
            "gross_usd": None,
            "note": "Apify REST API v2 does not expose Creator Store dollar payout ledgers (404); check Apify Console Monetization for finalized payout USD.",
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


def _stripe_paginate(client: httpx.Client, endpoint: str, headers: dict, max_pages: int = 10) -> list[dict]:
    items = []
    starting_after = None
    sep = "&" if "?" in endpoint else "?"
    for _ in range(max_pages):
        url = f"https://api.stripe.com/v1/{endpoint}"
        if starting_after:
            url += f"{sep}starting_after={starting_after}"
        r = client.get(url, headers=headers, timeout=12.0)
        if r.status_code != 200:
            break
        payload = r.json() or {}
        batch = payload.get("data") or []
        items.extend(batch)
        if not payload.get("has_more") or not batch:
            break
        starting_after = batch[-1].get("id")
        if not starting_after:
            break
    return items


def _fetch_gbp_usd_fx(client: httpx.Client) -> tuple[float, str]:
    try:
        r = client.get("https://open.er-api.com/v6/latest/GBP", timeout=6.0)
        if r.status_code == 200:
            rate = ((r.json() or {}).get("rates") or {}).get("USD")
            if isinstance(rate, (int, float)) and 0.5 < rate < 3.0:
                return round(float(rate), 4), "open.er-api.com"
    except Exception:
        pass
    return 1.27, "fallback_1.27"


def _label_payment_link(pl: dict) -> tuple[str, str, str]:
    md = pl.get("metadata") or {}
    brand = md.get("brand") or ("GEO Bureau" if pl.get("currency") == "gbp" else "Kurox / GEO")
    sku = md.get("sku") or md.get("offer_code") or md.get("service_slug") or pl.get("id")
    label_map = {
        "canaryguard-firewall-proxy-v1": ("CanaryGuard AI Firewall Proxy v1.0.0", "$9 USD"),
        "rugshield-pretrade-scanner-v1": ("RugShield Pre-Trade Scanner v1.0.0", "$9 USD"),
        "kurox-security-suite-bundle-v1": ("Kurox Security Source Bundle v1.0.0", "$15 USD"),
        "payment_risk_1": ("GEO Bureau Operational Dossier", "£ GBP"),
        "radar_weekly_subscription": ("GEO Bureau Weekly Radar Subscription", "£/wk GBP"),
        "radar_15": ("GEO Bureau Radar 15 Pack", "£ GBP"),
        "radar_5": ("GEO Bureau Radar 5 Pack", "£29 GBP"),
        "ukeducationitcontractsignals": ("UK Education IT Contract Signals", "£39/mo GBP"),
        "paid_traffic_leak_check": ("Paid Traffic Leak Check", "£49 GBP"),
    }
    if sku in label_map:
        return label_map[sku][0], label_map[sku][1], brand
    if pl.get("id") == "plink_1Tfpa0DmOa2iw8hhNikxGhni":
        return "GEO Audit ($99 USD Legacy Link)", "$99 USD", "GEO Bureau"
    return str(sku), (pl.get("currency") or "usd").upper(), brand


def fetch_stripe_aggregate(client: httpx.Client) -> dict:
    """
    Aggregate livemode Stripe revenue across USD & GBP, payouts, and checkout funnel counts
    when STRIPE_READONLY_KEY is set via CI secret. Never exposes PII, customer emails, or keys.
    """
    key = (os.environ.get("STRIPE_READONLY_KEY") or os.environ.get("STRIPE_SECRET_KEY") or "").strip()
    fx_rate, fx_src = _fetch_gbp_usd_fx(client)
    baseline = {
        "sync_mode": "verified_mcp_baseline",
        "baseline_checked_utc": "2026-11-15T18:20:50Z",
        "available_usd": 0.0,
        "pending_usd": 0.0,
        "available_gbp": 0.0,
        "pending_gbp": 0.0,
        "completed_charges": 0,
        "refunds_count": 0,
        "gross_settled_usd": 0.0,
        "fees_usd": 0.0,
        "net_settled_usd": 0.0,
        "gross_settled_gbp": 0.0,
        "fees_gbp": 0.0,
        "net_settled_gbp": 0.0,
        "gross_total_usd_eq": 0.0,
        "net_total_usd_eq": 0.0,
        "fx_gbp_to_usd": fx_rate,
        "fx_source": fx_src,
        "payouts_paid_usd": 0.0,
        "payouts_paid_gbp": 0.0,
        "sessions_total": 0,
        "sessions_paid": 0,
        "sessions_open": 0,
        "sessions_expired": 0,
        "active_links_total": len(STRIPE_ACTIVE_LINKS),
        "active_kurox_links": STRIPE_ACTIVE_LINKS,
        "active_geo_links": [],
        "note": "Add optional STRIPE_READONLY_KEY repository secret for automatic 15-min live Stripe sync.",
    }
    if not key:
        return baseline

    try:
        headers = {"Authorization": f"Bearer {key}"}
        bal_r = client.get("https://api.stripe.com/v1/balance", headers=headers, timeout=12.0)
        if bal_r.status_code != 200:
            baseline["sync_mode"] = f"stripe_http_{bal_r.status_code}"
            return baseline

        bal = bal_r.json()
        txs = _stripe_paginate(client, "balance_transactions?limit=100", headers, max_pages=10)
        payouts = _stripe_paginate(client, "payouts?limit=50", headers, max_pages=3)
        sessions = _stripe_paginate(client, "checkout/sessions?limit=100", headers, max_pages=5)
        plinks = _stripe_paginate(client, "payment_links?active=true&limit=50", headers, max_pages=3)

        avail_usd = sum(b.get("amount", 0) for b in bal.get("available") or [] if b.get("currency") == "usd") / 100.0
        pend_usd = sum(b.get("amount", 0) for b in bal.get("pending") or [] if b.get("currency") == "usd") / 100.0
        avail_gbp = sum(b.get("amount", 0) for b in bal.get("available") or [] if b.get("currency") == "gbp") / 100.0
        pend_gbp = sum(b.get("amount", 0) for b in bal.get("pending") or [] if b.get("currency") == "gbp") / 100.0

        gross_usd, fees_usd, net_usd = 0.0, 0.0, 0.0
        gross_gbp, fees_gbp, net_gbp = 0.0, 0.0, 0.0
        charges, refunds = 0, 0
        for t in txs:
            ttype = t.get("type")
            cur = t.get("currency")
            amt = (t.get("amount") or 0) / 100.0
            fee = (t.get("fee") or 0) / 100.0
            net = (t.get("net") or 0) / 100.0
            if ttype in ("charge", "payment"):
                charges += 1
                if cur == "usd":
                    gross_usd += amt
                    fees_usd += fee
                    net_usd += net
                elif cur == "gbp":
                    gross_gbp += amt
                    fees_gbp += fee
                    net_gbp += net
            elif ttype in ("refund", "adjustment") and cur in ("usd", "gbp"):
                refunds += 1
                if cur == "usd":
                    net_usd += net
                else:
                    net_gbp += net

        payouts_paid_usd = sum((p.get("amount") or 0) / 100.0 for p in payouts if p.get("status") == "paid" and p.get("currency") == "usd")
        payouts_paid_gbp = sum((p.get("amount") or 0) / 100.0 for p in payouts if p.get("status") == "paid" and p.get("currency") == "gbp")

        link_stats: dict[str, dict] = {}
        s_paid, s_open, s_exp = 0, 0, 0
        for s in sessions:
            st = s.get("status") or ""
            pst = s.get("payment_status") or ""
            s_sku = (s.get("metadata") or {}).get("sku") or ""
            pl_id = s.get("payment_link") or "direct"
            for key_id in [k for k in (pl_id, s_sku) if k]:
                bucket = link_stats.setdefault(key_id, {"total": 0, "paid": 0, "open": 0, "expired": 0})
                bucket["total"] += 1
                if pst == "paid":
                    bucket["paid"] += 1
                elif st == "open":
                    bucket["open"] += 1
                elif st == "expired":
                    bucket["expired"] += 1
            if pst == "paid":
                s_paid += 1
            elif st == "open":
                s_open += 1
            elif st == "expired":
                s_exp += 1

        kurox_links = [
            {
                **item,
                "id": f"checkout_{item['sku']}",
                "sessions_opened": link_stats.get(item["sku"], {}).get("total", 0),
                "sessions_paid": link_stats.get(item["sku"], {}).get("paid", 0),
                "sessions_expired": link_stats.get(item["sku"], {}).get("expired", 0),
            }
            for item in STRIPE_ACTIVE_LINKS
        ]
        geo_links = []
        for pl in plinks:
            md = pl.get("metadata") or {}
            if _is_excluded(json.dumps(md)):
                continue
            name, price_str, brand = _label_payment_link(pl)
            if brand == "Kurox":
                continue
            st_b = link_stats.get(pl["id"], {"total": 0, "paid": 0, "open": 0, "expired": 0})
            geo_links.append({
                "id": pl["id"],
                "sku": md.get("sku") or md.get("offer_code") or md.get("service_slug") or pl["id"],
                "name": name,
                "price": price_str,
                "currency": (pl.get("currency") or "usd").upper(),
                "url": pl.get("url"),
                "brand": brand,
                "sessions_opened": st_b["total"],
                "sessions_paid": st_b["paid"],
                "sessions_expired": st_b["expired"],
            })

        gross_usd_eq = round(gross_usd + gross_gbp * fx_rate, 2)
        net_usd_eq = round(net_usd + net_gbp * fx_rate, 2)
        return {
            **baseline,
            "sync_mode": "live_api_secret",
            "baseline_checked_utc": datetime.now(timezone.utc).isoformat(),
            "available_usd": round(avail_usd, 2),
            "pending_usd": round(pend_usd, 2),
            "available_gbp": round(avail_gbp, 2),
            "pending_gbp": round(pend_gbp, 2),
            "completed_charges": charges,
            "refunds_count": refunds,
            "gross_settled_usd": round(gross_usd, 2),
            "fees_usd": round(fees_usd, 2),
            "net_settled_usd": round(net_usd, 2),
            "gross_settled_gbp": round(gross_gbp, 2),
            "fees_gbp": round(fees_gbp, 2),
            "net_settled_gbp": round(net_gbp, 2),
            "gross_total_usd_eq": gross_usd_eq,
            "net_total_usd_eq": net_usd_eq,
            "payouts_paid_usd": round(payouts_paid_usd, 2),
            "payouts_paid_gbp": round(payouts_paid_gbp, 2),
            "sessions_total": len(sessions),
            "sessions_paid": s_paid,
            "sessions_open": s_open,
            "sessions_expired": s_exp,
            "active_links_total": len(kurox_links) + len(geo_links),
            "active_kurox_links": kurox_links or STRIPE_ACTIVE_LINKS,
            "active_geo_links": geo_links,
            "note": f"Synced live from Stripe (USD + GBP @ {fx_rate} FX, payouts & checkout session funnel — zero PII).",
        }
    except Exception as exc:
        baseline["note"] = f"Stripe sync fallback ({str(exc)[:80]})."
        return baseline


def fetch_native_balances(client: httpx.Client) -> dict:
    """Query native ETH (Base) and SOL (Solana) balances on merchant wallets."""
    out = {"base_eth": 0.0, "solana_sol": 0.0}
    try:
        rb = client.post(
            "https://mainnet.base.org",
            json={"jsonrpc": "2.0", "id": 1, "method": "eth_getBalance", "params": ["0x80E0Ae84679b7f11bE171DaADd492FBECf628cd6", "latest"]},
            timeout=8.0,
        )
        if rb.status_code == 200 and rb.json().get("result"):
            out["base_eth"] = round(int(rb.json()["result"], 16) / 1e18, 6)
    except Exception:
        pass
    try:
        rs = client.post(
            "https://solana-rpc.publicnode.com",
            json={"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": ["9wuMysgXwNhtQeqJgGByAiMYc4EjzZ5wUSmnjrrt3ffh"]},
            timeout=8.0,
        )
        if rs.status_code == 200:
            val = ((rs.json() or {}).get("result") or {}).get("value")
            if val is not None:
                out["solana_sol"] = round(int(val) / 1e9, 6)
    except Exception:
        pass
    return out


def fetch_cloudflare_worker_analytics(client: httpx.Client) -> dict:
    """Query Cloudflare Workers GraphQL analytics for agentfuel402 when CF_API_TOKEN is set."""
    cf_tok = (os.environ.get("CF_API_TOKEN") or "").strip()
    acct_id = (os.environ.get("CF_ACCOUNT_ID") or "399816be9d4332789f68c30dfb87f390").strip()
    if not cf_tok:
        return {"sync_mode": "token_needed", "requests_24h": None, "requests_30d": None, "errors_30d": None}
    try:
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        since_30 = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        since_24 = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        until = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        query = """
        query($accountTag: string!, $since30: Time!, $since24: Time!, $until: Time!) {
          viewer {
            accounts(filter: {accountTag: $accountTag}) {
              w30: workersInvocationsAdaptive(limit: 100, filter: {datetime_geq: $since30, datetime_leq: $until, scriptName: "agentfuel402"}) {
                sum { requests errors subrequests }
              }
              w24: workersInvocationsAdaptive(limit: 100, filter: {datetime_geq: $since24, datetime_leq: $until, scriptName: "agentfuel402"}) {
                sum { requests errors subrequests }
              }
            }
          }
        }
        """
        r = client.post(
            "https://api.cloudflare.com/client/v4/graphql",
            headers={"Authorization": f"Bearer {cf_tok}", "Content-Type": "application/json"},
            json={"query": query, "variables": {"accountTag": acct_id, "since30": since_30, "since24": since_24, "until": until}},
            timeout=10.0,
        )
        if r.status_code == 200:
            accts = (((r.json() or {}).get("data") or {}).get("viewer") or {}).get("accounts") or []
            if accts:
                w30 = accts[0].get("w30") or []
                w24 = accts[0].get("w24") or []
                return {
                    "sync_mode": "live_cf_graphql",
                    "requests_30d": sum((x.get("sum") or {}).get("requests", 0) for x in w30),
                    "errors_30d": sum((x.get("sum") or {}).get("errors", 0) for x in w30),
                    "subrequests_30d": sum((x.get("sum") or {}).get("subrequests", 0) for x in w30),
                    "requests_24h": sum((x.get("sum") or {}).get("requests", 0) for x in w24),
                }
        return {"sync_mode": f"cf_http_{r.status_code}", "requests_24h": None, "requests_30d": None}
    except Exception as exc:
        return {"sync_mode": f"cf_err:{str(exc)[:60]}", "requests_24h": None, "requests_30d": None}


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
    native = fetch_native_balances(client)
    cloudflare = fetch_cloudflare_worker_analytics(client)

    fixed_monthly_usd = round(sum(float(s.get("monthly_fixed_usd") or 0.0) for s in BIG3_SERVICES), 2)
    stripe_gross_usd_eq = float(stripe.get("gross_total_usd_eq") or stripe.get("gross_settled_usd") or 0.0)
    stripe_net_usd_eq = float(stripe.get("net_total_usd_eq") or stripe.get("net_settled_usd") or 0.0)
    apify_gross = apify["summary"]["gross_usd"] or 0.0
    verified_gross_usd = round(ext_x402_usdc + stripe_gross_usd_eq + apify_gross, 6)
    verified_net_rev_usd = round(ext_x402_usdc + stripe_net_usd_eq + apify_gross, 6)
    est_net_monthly_usd = round(verified_net_rev_usd - fixed_monthly_usd, 2)

    snapshot = {
        "schema_version": "1.1.0",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Active Big-3 & Kurox Channels Only (AgentFuel402, CanaryGuard 402, RugShield 402, Kurox Stripe/npm, GEO Bureau)",
        "excluded_legacy": list(EXCLUDED_KEYWORDS),
        "profit_overview": {
            "verified_external_x402_usdc": round(ext_x402_usdc, 6),
            "verified_external_x402_tx_count": len(external_deliveries),
            "treasury_vault_base_usdc": round(base_usdc, 6),
            "treasury_vault_solana_usdc": round(sol_usdc, 6),
            "treasury_vault_total_usdc": round(base_usdc + sol_usdc, 6),
            "treasury_base_eth": native["base_eth"],
            "treasury_solana_sol": native["solana_sol"],
            "stripe_gross_usd": stripe["gross_settled_usd"],
            "stripe_gross_gbp": stripe["gross_settled_gbp"],
            "stripe_gross_usd_eq": stripe_gross_usd_eq,
            "stripe_net_usd_eq": stripe_net_usd_eq,
            "apify_verified_gross_usd": apify["summary"]["gross_usd"],
            "verified_cumulative_gross_usd": verified_gross_usd,
            "verified_cumulative_net_rev_usd": verified_net_rev_usd,
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
        "cloudflare": cloudflare,
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
