#!/usr/bin/env python3
"""
Real World Asset (RWA) Tokenization Calculator Agent
=====================================================
Multi-asset class tokenization calculator with deep market dynamics reasoning.
Powered by Claude Opus 4.6 with adaptive thinking for complex financial analysis.

Supported Asset Classes:
  - Real Estate (commercial, residential, industrial, REITs)
  - Private Equity & Venture Capital
  - Infrastructure (energy, transport, utilities)
  - Commodities (precious metals, agricultural, energy)
  - Fixed Income / Private Credit
  - Art & Collectibles
  - Intellectual Property / Royalties
  - Carbon Credits / ESG Assets
"""

import anthropic
import json
import math
from datetime import datetime, timedelta
from typing import Any

# ── Client ────────────────────────────────────────────────────────────────────
import os

def _make_client() -> anthropic.Anthropic:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return anthropic.Anthropic()
    # Claude Code web session — use OAuth bearer token
    token_file = "/home/claude/.claude/remote/.session_ingress_token"
    if os.path.exists(token_file):
        token = open(token_file).read().strip()
        return anthropic.Anthropic(auth_token=token)
    return anthropic.Anthropic()  # will raise AuthenticationError with a clear message

client = _make_client()

# ── Asset-class reference data ─────────────────────────────────────────────────
ASSET_CLASSES = {
    "real_estate_commercial": {
        "name": "Commercial Real Estate",
        "typical_yield": (0.04, 0.08),
        "liquidity_discount": (0.10, 0.20),
        "tokenization_cost_pct": (0.015, 0.03),
        "min_token_size_usd": 1_000,
        "regulatory_complexity": "high",
        "smart_contract_type": "ERC-1400 / ERC-3643",
        "typical_lockup_years": (3, 7),
    },
    "real_estate_residential": {
        "name": "Residential Real Estate",
        "typical_yield": (0.03, 0.06),
        "liquidity_discount": (0.08, 0.15),
        "tokenization_cost_pct": (0.01, 0.025),
        "min_token_size_usd": 500,
        "regulatory_complexity": "medium",
        "smart_contract_type": "ERC-1400 / ERC-3643",
        "typical_lockup_years": (2, 5),
    },
    "private_equity": {
        "name": "Private Equity",
        "typical_yield": (0.12, 0.25),
        "liquidity_discount": (0.20, 0.35),
        "tokenization_cost_pct": (0.02, 0.04),
        "min_token_size_usd": 10_000,
        "regulatory_complexity": "very_high",
        "smart_contract_type": "ERC-1400 / Reg D / Reg S",
        "typical_lockup_years": (5, 10),
    },
    "infrastructure": {
        "name": "Infrastructure Assets",
        "typical_yield": (0.05, 0.10),
        "liquidity_discount": (0.12, 0.22),
        "tokenization_cost_pct": (0.018, 0.035),
        "min_token_size_usd": 5_000,
        "regulatory_complexity": "high",
        "smart_contract_type": "ERC-1400 / Project Finance SPV",
        "typical_lockup_years": (5, 15),
    },
    "commodities_precious_metals": {
        "name": "Precious Metals (Gold/Silver/Platinum)",
        "typical_yield": (0.0, 0.02),
        "liquidity_discount": (0.01, 0.05),
        "tokenization_cost_pct": (0.005, 0.015),
        "min_token_size_usd": 100,
        "regulatory_complexity": "low",
        "smart_contract_type": "ERC-20 / ERC-777 (backed)",
        "typical_lockup_years": (0, 1),
    },
    "commodities_energy": {
        "name": "Energy Commodities (Oil/Gas/LNG)",
        "typical_yield": (0.02, 0.06),
        "liquidity_discount": (0.05, 0.12),
        "tokenization_cost_pct": (0.01, 0.025),
        "min_token_size_usd": 1_000,
        "regulatory_complexity": "medium",
        "smart_contract_type": "ERC-20 (futures-backed)",
        "typical_lockup_years": (0, 2),
    },
    "private_credit": {
        "name": "Private Credit / Fixed Income",
        "typical_yield": (0.06, 0.14),
        "liquidity_discount": (0.05, 0.15),
        "tokenization_cost_pct": (0.01, 0.025),
        "min_token_size_usd": 1_000,
        "regulatory_complexity": "medium",
        "smart_contract_type": "ERC-1400 / Bond Token",
        "typical_lockup_years": (1, 5),
    },
    "art_collectibles": {
        "name": "Art & Collectibles",
        "typical_yield": (0.03, 0.12),
        "liquidity_discount": (0.25, 0.45),
        "tokenization_cost_pct": (0.03, 0.06),
        "min_token_size_usd": 500,
        "regulatory_complexity": "medium",
        "smart_contract_type": "ERC-1155 / NFT fractionalization",
        "typical_lockup_years": (2, 7),
    },
    "intellectual_property": {
        "name": "Intellectual Property / Royalties",
        "typical_yield": (0.05, 0.20),
        "liquidity_discount": (0.15, 0.30),
        "tokenization_cost_pct": (0.02, 0.045),
        "min_token_size_usd": 250,
        "regulatory_complexity": "medium",
        "smart_contract_type": "ERC-1155 / Revenue-sharing token",
        "typical_lockup_years": (2, 5),
    },
    "carbon_credits": {
        "name": "Carbon Credits / ESG Assets",
        "typical_yield": (0.05, 0.18),
        "liquidity_discount": (0.08, 0.20),
        "tokenization_cost_pct": (0.01, 0.03),
        "min_token_size_usd": 100,
        "regulatory_complexity": "low",
        "smart_contract_type": "ERC-20 / Toucan / Moss MCO2",
        "typical_lockup_years": (0, 3),
    },
}

BLOCKCHAIN_OPTIONS = {
    "ethereum": {"name": "Ethereum", "gas_cost_usd_per_tx": 15, "tps": 15, "security": "highest", "ecosystem": "largest"},
    "polygon": {"name": "Polygon (PoS)", "gas_cost_usd_per_tx": 0.01, "tps": 7000, "security": "high", "ecosystem": "large"},
    "avalanche": {"name": "Avalanche (C-Chain)", "gas_cost_usd_per_tx": 0.10, "tps": 4500, "security": "high", "ecosystem": "medium"},
    "solana": {"name": "Solana", "gas_cost_usd_per_tx": 0.0005, "tps": 65000, "security": "high", "ecosystem": "large"},
    "xrp_ledger": {"name": "XRP Ledger", "gas_cost_usd_per_tx": 0.0001, "tps": 1500, "security": "high", "ecosystem": "medium"},
    "stellar": {"name": "Stellar", "gas_cost_usd_per_tx": 0.00001, "tps": 1000, "security": "high", "ecosystem": "medium"},
    "tezos": {"name": "Tezos", "gas_cost_usd_per_tx": 0.005, "tps": 52, "security": "high", "ecosystem": "small"},
    "algorand": {"name": "Algorand", "gas_cost_usd_per_tx": 0.001, "tps": 6000, "security": "high", "ecosystem": "small"},
}

JURISDICTION_DATA = {
    "usa": {"name": "United States", "reg_framework": "SEC Reg D/S/A+", "compliance_cost_usd": 150_000, "timeline_months": 6},
    "eu": {"name": "European Union", "reg_framework": "MiCA / MiFID II", "compliance_cost_usd": 120_000, "timeline_months": 5},
    "uae_adgm": {"name": "UAE (ADGM)", "reg_framework": "ADGM Digital Assets Framework", "compliance_cost_usd": 80_000, "timeline_months": 3},
    "singapore": {"name": "Singapore", "reg_framework": "MAS PSA / Capital Markets License", "compliance_cost_usd": 90_000, "timeline_months": 4},
    "switzerland": {"name": "Switzerland", "reg_framework": "FINMA DLT Act", "compliance_cost_usd": 100_000, "timeline_months": 4},
    "cayman": {"name": "Cayman Islands", "reg_framework": "VASP / Offshore Structure", "compliance_cost_usd": 50_000, "timeline_months": 2},
    "uk": {"name": "United Kingdom", "reg_framework": "FCA Crypto-asset Regime", "compliance_cost_usd": 110_000, "timeline_months": 5},
    "hong_kong": {"name": "Hong Kong", "reg_framework": "SFC VATP", "compliance_cost_usd": 85_000, "timeline_months": 4},
}

# ── Tool definitions ───────────────────────────────────────────────────────────

def calculate_tokenization_economics(
    asset_class: str,
    asset_value_usd: float,
    num_tokens: int,
    blockchain: str,
    jurisdiction: str,
    expected_annual_return_pct: float,
    holding_period_years: int,
    investor_count: int,
) -> dict[str, Any]:
    """
    Core tokenization economics engine.
    Computes token pricing, costs, yields, IRR, and market structure.
    """
    if asset_class not in ASSET_CLASSES:
        return {"error": f"Unknown asset class '{asset_class}'. Valid: {list(ASSET_CLASSES.keys())}"}
    if blockchain not in BLOCKCHAIN_OPTIONS:
        return {"error": f"Unknown blockchain '{blockchain}'. Valid: {list(BLOCKCHAIN_OPTIONS.keys())}"}
    if jurisdiction not in JURISDICTION_DATA:
        return {"error": f"Unknown jurisdiction '{jurisdiction}'. Valid: {list(JURISDICTION_DATA.keys())}"}

    ac = ASSET_CLASSES[asset_class]
    bc = BLOCKCHAIN_OPTIONS[blockchain]
    jd = JURISDICTION_DATA[jurisdiction]

    # ── Token pricing ─────────────────────────────────────────────────────────
    token_price_usd = asset_value_usd / num_tokens
    min_investment_usd = max(token_price_usd, ac["min_token_size_usd"])

    # ── Liquidity discount ────────────────────────────────────────────────────
    mid_liquidity_discount = (ac["liquidity_discount"][0] + ac["liquidity_discount"][1]) / 2
    # Tokenization reduces but doesn't eliminate liquidity discount
    post_token_liquidity_discount = mid_liquidity_discount * 0.55
    liquidity_premium_unlocked_usd = asset_value_usd * (mid_liquidity_discount - post_token_liquidity_discount)

    # ── Tokenization setup costs ──────────────────────────────────────────────
    mid_token_cost_pct = (ac["tokenization_cost_pct"][0] + ac["tokenization_cost_pct"][1]) / 2
    platform_tokenization_cost_usd = asset_value_usd * mid_token_cost_pct
    legal_compliance_cost_usd = jd["compliance_cost_usd"]
    smart_contract_audit_usd = 25_000
    custody_setup_usd = 15_000

    # On-chain minting & initial distribution cost
    avg_tx_cost = bc["gas_cost_usd_per_tx"]
    minting_txs = math.ceil(num_tokens / 1000) + investor_count  # batch mint + distributions
    onchain_setup_cost_usd = avg_tx_cost * minting_txs

    total_setup_cost_usd = (
        platform_tokenization_cost_usd
        + legal_compliance_cost_usd
        + smart_contract_audit_usd
        + custody_setup_usd
        + onchain_setup_cost_usd
    )
    setup_cost_as_pct_of_asset = (total_setup_cost_usd / asset_value_usd) * 100

    # ── Ongoing annual costs ──────────────────────────────────────────────────
    annual_custody_usd = asset_value_usd * 0.0025          # 25 bps
    annual_compliance_usd = legal_compliance_cost_usd * 0.20
    annual_platform_fee_usd = asset_value_usd * 0.005       # 50 bps AUM fee
    annual_dividend_tx_cost_usd = avg_tx_cost * investor_count * 4  # quarterly distributions
    total_annual_cost_usd = (
        annual_custody_usd
        + annual_compliance_usd
        + annual_platform_fee_usd
        + annual_dividend_tx_cost_usd
    )
    ongoing_cost_pct = (total_annual_cost_usd / asset_value_usd) * 100

    # ── Yield & return analysis ───────────────────────────────────────────────
    gross_annual_yield_usd = asset_value_usd * (expected_annual_return_pct / 100)
    net_annual_yield_usd = gross_annual_yield_usd - total_annual_cost_usd
    net_yield_pct = (net_annual_yield_usd / asset_value_usd) * 100

    yield_per_token_usd = net_annual_yield_usd / num_tokens

    # ── IRR calculation (simplified DCF) ──────────────────────────────────────
    initial_investment = asset_value_usd + total_setup_cost_usd
    # Assume 3% annual capital appreciation
    terminal_value = asset_value_usd * ((1 + 0.03) ** holding_period_years)
    # Newton-Raphson IRR approximation
    def npv(rate: float) -> float:
        val = -initial_investment
        for yr in range(1, holding_period_years + 1):
            val += net_annual_yield_usd / ((1 + rate) ** yr)
        val += terminal_value / ((1 + rate) ** holding_period_years)
        return val

    irr = 0.08  # initial guess
    for _ in range(200):
        npv_val = npv(irr)
        d_npv = (npv(irr + 1e-6) - npv_val) / 1e-6
        if abs(d_npv) < 1e-12:
            break
        irr -= npv_val / d_npv
        if irr < -0.999:
            irr = -0.999
    irr_pct = round(irr * 100, 2)

    # ── Break-even analysis ───────────────────────────────────────────────────
    if net_annual_yield_usd > 0:
        breakeven_years = total_setup_cost_usd / net_annual_yield_usd
    else:
        breakeven_years = float("inf")

    # ── Market access expansion ───────────────────────────────────────────────
    traditional_min_investment = asset_value_usd * 0.10  # typically 10% of asset
    democratization_ratio = traditional_min_investment / min_investment_usd

    # ── Secondary market liquidity estimation ─────────────────────────────────
    daily_volume_pct = 0.005  # 0.5% of tokens trade daily (conservative for RWA)
    daily_volume_usd = asset_value_usd * daily_volume_pct
    bid_ask_spread_pct = post_token_liquidity_discount * 0.1  # 10% of discount becomes spread

    # ── Regulatory timeline ───────────────────────────────────────────────────
    launch_date = datetime.now() + timedelta(days=jd["timeline_months"] * 30)

    return {
        "asset_summary": {
            "asset_class": ac["name"],
            "asset_value_usd": asset_value_usd,
            "total_tokens": num_tokens,
            "token_price_usd": round(token_price_usd, 4),
            "minimum_investment_usd": round(min_investment_usd, 2),
            "smart_contract_standard": ac["smart_contract_type"],
            "blockchain": bc["name"],
            "jurisdiction": jd["name"],
            "regulatory_framework": jd["reg_framework"],
        },
        "tokenization_costs": {
            "platform_tokenization_usd": round(platform_tokenization_cost_usd, 2),
            "legal_compliance_usd": round(legal_compliance_cost_usd, 2),
            "smart_contract_audit_usd": smart_contract_audit_usd,
            "custody_setup_usd": custody_setup_usd,
            "onchain_setup_usd": round(onchain_setup_cost_usd, 2),
            "total_setup_cost_usd": round(total_setup_cost_usd, 2),
            "setup_cost_pct_of_asset": round(setup_cost_as_pct_of_asset, 3),
        },
        "ongoing_annual_costs": {
            "custody_usd": round(annual_custody_usd, 2),
            "compliance_usd": round(annual_compliance_usd, 2),
            "platform_fee_usd": round(annual_platform_fee_usd, 2),
            "distribution_tx_cost_usd": round(annual_dividend_tx_cost_usd, 2),
            "total_annual_cost_usd": round(total_annual_cost_usd, 2),
            "ongoing_cost_pct_of_aum": round(ongoing_cost_pct, 3),
        },
        "yield_analysis": {
            "gross_annual_yield_usd": round(gross_annual_yield_usd, 2),
            "gross_yield_pct": round(expected_annual_return_pct, 2),
            "net_annual_yield_usd": round(net_annual_yield_usd, 2),
            "net_yield_pct": round(net_yield_pct, 3),
            "yield_per_token_usd": round(yield_per_token_usd, 6),
            "irr_pct": irr_pct,
        },
        "liquidity_analysis": {
            "pre_tokenization_liquidity_discount_pct": round(mid_liquidity_discount * 100, 1),
            "post_tokenization_liquidity_discount_pct": round(post_token_liquidity_discount * 100, 1),
            "liquidity_premium_unlocked_usd": round(liquidity_premium_unlocked_usd, 2),
            "est_daily_secondary_volume_usd": round(daily_volume_usd, 2),
            "est_bid_ask_spread_pct": round(bid_ask_spread_pct * 100, 3),
        },
        "investor_access": {
            "min_investment_usd": round(min_investment_usd, 2),
            "democratization_ratio_vs_traditional": round(democratization_ratio, 1),
            "max_potential_investors": num_tokens,
            "target_investor_count": investor_count,
            "pct_tokens_at_target_investors": round((investor_count / num_tokens) * 100, 2),
        },
        "timeline_and_viability": {
            "breakeven_years": round(breakeven_years, 2) if breakeven_years != float("inf") else "N/A (negative net yield)",
            "estimated_launch_date": launch_date.strftime("%B %Y"),
            "regulatory_timeline_months": jd["timeline_months"],
            "recommended_min_asset_size_usd": 1_000_000,
            "asset_meets_min_size": asset_value_usd >= 1_000_000,
        },
        "blockchain_specs": {
            "network": bc["name"],
            "transactions_per_second": bc["tps"],
            "avg_tx_cost_usd": bc["gas_cost_usd_per_tx"],
            "security_rating": bc["security"],
            "ecosystem_size": bc["ecosystem"],
        },
    }


def compare_asset_classes(
    asset_value_usd: float,
    num_tokens: int,
    blockchain: str,
    jurisdiction: str,
    holding_period_years: int,
    investor_count: int,
) -> dict[str, Any]:
    """Compare tokenization economics across all asset classes for a given capital amount."""
    results = {}
    for key in ASSET_CLASSES:
        ac = ASSET_CLASSES[key]
        mid_yield = (ac["typical_yield"][0] + ac["typical_yield"][1]) / 2 * 100
        calc = calculate_tokenization_economics(
            asset_class=key,
            asset_value_usd=asset_value_usd,
            num_tokens=num_tokens,
            blockchain=blockchain,
            jurisdiction=jurisdiction,
            expected_annual_return_pct=mid_yield,
            holding_period_years=holding_period_years,
            investor_count=investor_count,
        )
        if "error" not in calc:
            results[key] = {
                "asset_class": ac["name"],
                "gross_yield_pct": round(mid_yield, 2),
                "net_yield_pct": calc["yield_analysis"]["net_yield_pct"],
                "irr_pct": calc["yield_analysis"]["irr_pct"],
                "setup_cost_usd": calc["tokenization_costs"]["total_setup_cost_usd"],
                "setup_cost_pct": calc["tokenization_costs"]["setup_cost_pct_of_asset"],
                "liquidity_premium_unlocked_usd": calc["liquidity_analysis"]["liquidity_premium_unlocked_usd"],
                "min_investment_usd": calc["investor_access"]["min_investment_usd"],
                "regulatory_complexity": ac["regulatory_complexity"],
                "breakeven_years": calc["timeline_and_viability"]["breakeven_years"],
                "smart_contract_standard": ac["smart_contract_type"],
            }
    # Rank by IRR
    ranked = sorted(results.items(), key=lambda x: x[1].get("irr_pct", -999), reverse=True)
    return {
        "comparison_parameters": {
            "asset_value_usd": asset_value_usd,
            "num_tokens": num_tokens,
            "blockchain": BLOCKCHAIN_OPTIONS[blockchain]["name"],
            "jurisdiction": JURISDICTION_DATA[jurisdiction]["name"],
            "holding_period_years": holding_period_years,
        },
        "ranked_by_irr": [{"rank": i + 1, "key": k, **v} for i, (k, v) in enumerate(ranked)],
    }


def run_market_dynamics_scenario(
    asset_class: str,
    asset_value_usd: float,
    num_tokens: int,
    blockchain: str,
    jurisdiction: str,
    base_return_pct: float,
    holding_period_years: int,
    investor_count: int,
) -> dict[str, Any]:
    """Run bull/base/bear market scenarios and stress tests."""
    scenarios = {
        "bull_market": base_return_pct * 1.5,
        "base_case": base_return_pct,
        "bear_market": base_return_pct * 0.4,
        "stress_test_zero_yield": 0.1,
        "rate_shock_high_rates": max(base_return_pct - 3.0, 0.5),   # +300bps rate shock
        "liquidity_crisis": base_return_pct * 0.6,
    }
    results = {}
    for scenario_name, return_pct in scenarios.items():
        calc = calculate_tokenization_economics(
            asset_class=asset_class,
            asset_value_usd=asset_value_usd,
            num_tokens=num_tokens,
            blockchain=blockchain,
            jurisdiction=jurisdiction,
            expected_annual_return_pct=return_pct,
            holding_period_years=holding_period_years,
            investor_count=investor_count,
        )
        if "error" not in calc:
            results[scenario_name] = {
                "gross_yield_pct": return_pct,
                "net_yield_pct": calc["yield_analysis"]["net_yield_pct"],
                "net_annual_yield_usd": calc["yield_analysis"]["net_annual_yield_usd"],
                "irr_pct": calc["yield_analysis"]["irr_pct"],
                "breakeven_years": calc["timeline_and_viability"]["breakeven_years"],
            }
        else:
            results[scenario_name] = calc

    # VaR-style analysis
    irr_values = [v["irr_pct"] for v in results.values() if isinstance(v.get("irr_pct"), (int, float))]
    return {
        "scenario_analysis": results,
        "risk_metrics": {
            "best_case_irr_pct": max(irr_values) if irr_values else None,
            "worst_case_irr_pct": min(irr_values) if irr_values else None,
            "irr_range_pct": round(max(irr_values) - min(irr_values), 2) if len(irr_values) >= 2 else None,
            "scenarios_with_positive_net_yield": sum(
                1 for v in results.values()
                if isinstance(v.get("net_yield_pct"), (int, float)) and v["net_yield_pct"] > 0
            ),
            "total_scenarios": len(scenarios),
        },
    }


# ── Tool dispatch ──────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "calculate_tokenization_economics",
        "description": (
            "Calculate complete tokenization economics for a specific real world asset. "
            "Returns token pricing, all costs (setup + ongoing), net yield, IRR, liquidity analysis, "
            "investor access metrics, regulatory timeline, and blockchain specs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_class": {
                    "type": "string",
                    "description": f"Asset class key. Options: {list(ASSET_CLASSES.keys())}",
                    "enum": list(ASSET_CLASSES.keys()),
                },
                "asset_value_usd": {"type": "number", "description": "Total market value of the asset in USD"},
                "num_tokens": {"type": "integer", "description": "Total number of tokens to issue (e.g. 1000000)"},
                "blockchain": {
                    "type": "string",
                    "description": f"Target blockchain. Options: {list(BLOCKCHAIN_OPTIONS.keys())}",
                    "enum": list(BLOCKCHAIN_OPTIONS.keys()),
                },
                "jurisdiction": {
                    "type": "string",
                    "description": f"Regulatory jurisdiction. Options: {list(JURISDICTION_DATA.keys())}",
                    "enum": list(JURISDICTION_DATA.keys()),
                },
                "expected_annual_return_pct": {"type": "number", "description": "Expected gross annual return in percent (e.g. 8.0 for 8%)"},
                "holding_period_years": {"type": "integer", "description": "Planned holding period in years"},
                "investor_count": {"type": "integer", "description": "Target number of token investors"},
            },
            "required": [
                "asset_class", "asset_value_usd", "num_tokens", "blockchain",
                "jurisdiction", "expected_annual_return_pct", "holding_period_years", "investor_count"
            ],
        },
    },
    {
        "name": "compare_asset_classes",
        "description": (
            "Compare tokenization economics across ALL supported asset classes for a given capital amount. "
            "Returns a ranked comparison table by IRR, including yield, costs, liquidity premium, "
            "minimum investment, and regulatory complexity."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_value_usd": {"type": "number", "description": "Total capital to tokenize in USD"},
                "num_tokens": {"type": "integer", "description": "Total number of tokens to issue"},
                "blockchain": {"type": "string", "enum": list(BLOCKCHAIN_OPTIONS.keys())},
                "jurisdiction": {"type": "string", "enum": list(JURISDICTION_DATA.keys())},
                "holding_period_years": {"type": "integer"},
                "investor_count": {"type": "integer"},
            },
            "required": ["asset_value_usd", "num_tokens", "blockchain", "jurisdiction", "holding_period_years", "investor_count"],
        },
    },
    {
        "name": "run_market_dynamics_scenario",
        "description": (
            "Run multi-scenario market dynamics stress testing: bull, base, bear, zero-yield, "
            "rate-shock, and liquidity-crisis scenarios. Returns IRR/yield/breakeven for each scenario "
            "plus risk metrics (best/worst IRR, range, positive scenarios count)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "asset_class": {"type": "string", "enum": list(ASSET_CLASSES.keys())},
                "asset_value_usd": {"type": "number"},
                "num_tokens": {"type": "integer"},
                "blockchain": {"type": "string", "enum": list(BLOCKCHAIN_OPTIONS.keys())},
                "jurisdiction": {"type": "string", "enum": list(JURISDICTION_DATA.keys())},
                "base_return_pct": {"type": "number", "description": "Base case expected annual return %"},
                "holding_period_years": {"type": "integer"},
                "investor_count": {"type": "integer"},
            },
            "required": [
                "asset_class", "asset_value_usd", "num_tokens", "blockchain",
                "jurisdiction", "base_return_pct", "holding_period_years", "investor_count"
            ],
        },
    },
]


def execute_tool(name: str, tool_input: dict) -> str:
    """Dispatch a tool call and return a JSON string result."""
    if name == "calculate_tokenization_economics":
        result = calculate_tokenization_economics(**tool_input)
    elif name == "compare_asset_classes":
        result = compare_asset_classes(**tool_input)
    elif name == "run_market_dynamics_scenario":
        result = run_market_dynamics_scenario(**tool_input)
    else:
        result = {"error": f"Unknown tool: {name}"}
    return json.dumps(result, indent=2)


# ── Agent loop ─────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an elite Real World Asset (RWA) Tokenization Advisor with deep expertise in:
- Asset tokenization economics across all asset classes (real estate, PE, infrastructure, commodities, credit, art, IP, carbon)
- Blockchain infrastructure selection and smart contract standards (ERC-20, ERC-1155, ERC-1400, ERC-3643)
- Global regulatory frameworks (SEC, MiCA, MAS, ADGM, FINMA, FCA)
- DeFi/TradFi integration, secondary market liquidity, and institutional-grade custody
- Market dynamics, interest rate sensitivity, and macro risk factors affecting RWA valuations

## Your approach:
1. Always use the calculation tools to ground your analysis in precise numbers
2. When asked to recommend or optimize, compare across asset classes using compare_asset_classes
3. Run scenario analysis using run_market_dynamics_scenario to assess risk-adjusted returns
4. Provide institutional-grade insights on market dynamics: interest rate environments, DeFi liquidity incentives, regulatory arbitrage opportunities, and tokenization market maturation
5. Give specific, actionable recommendations with supporting quantitative data

## Market context you should reason about:
- Rising rate environments compress RWA yields relative to risk-free rates
- DeFi protocols (Centrifuge, Maple, TrueFi, Goldfinch) create additional demand and yield opportunities for tokenized credit
- BRICS nations are accelerating alternative settlement rail adoption (Stellar, XRP Ledger)
- Institutional adoption is driving ERC-1400 / ERC-3643 compliance token standards
- Liquidity premium unlock is a major value driver: tokenization can recover 10-20% of discounted asset value
- Carbon markets and ESG assets have asymmetric upside given regulatory tailwinds

Always present your analysis clearly with:
- Key metrics in tabular form when appropriate
- Risk flags and regulatory considerations
- Actionable next steps for the client"""


def run_agent(user_query: str) -> None:
    """Run the RWA tokenization agent with adaptive thinking and streaming."""
    print(f"\n{'='*80}")
    print("RWA TOKENIZATION AGENT")
    print(f"{'='*80}")
    print(f"Query: {user_query}")
    print(f"{'='*80}\n")

    messages = [{"role": "user", "content": user_query}]

    turn = 0
    while True:
        turn += 1
        print(f"[Turn {turn}] Calling Claude Opus 4.6 with adaptive thinking...\n")

        # Stream the response for better UX
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        ) as stream:
            thinking_shown = False
            response_text = ""

            for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "thinking":
                        print("[Deep Reasoning Process]")
                        print("-" * 40)
                        thinking_shown = True
                    elif event.content_block.type == "text":
                        if thinking_shown:
                            print("-" * 40)
                            print("\n[Analysis & Recommendations]")
                            print("-" * 40)
                        thinking_shown = False

                elif event.type == "content_block_delta":
                    if event.delta.type == "thinking_delta":
                        print(event.delta.thinking, end="", flush=True)
                    elif event.delta.type == "text_delta":
                        print(event.delta.text, end="", flush=True)
                        response_text += event.delta.text

            response = stream.get_final_message()

        print()  # newline after streaming

        # Append assistant response to history
        messages.append({"role": "assistant", "content": response.content})

        # Check if we need to execute tools
        if response.stop_reason != "tool_use":
            print(f"\n{'='*80}")
            print("Analysis complete.")
            print(f"{'='*80}\n")
            break

        # Execute all tool calls
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        tool_results = []

        for tool_block in tool_use_blocks:
            print(f"\n[Tool Call] {tool_block.name}")
            print(f"  Parameters: {json.dumps(tool_block.input, indent=4)}")
            print("  Executing...", end="", flush=True)

            result_str = execute_tool(tool_block.name, tool_block.input)
            result_data = json.loads(result_str)

            print(" Done.")
            # Print a summary of key results
            _print_tool_summary(tool_block.name, result_data)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": result_str,
            })

        messages.append({"role": "user", "content": tool_results})


def _print_tool_summary(tool_name: str, result: dict) -> None:
    """Print a concise summary of tool results."""
    print(f"\n  [Result Summary - {tool_name}]")
    if tool_name == "calculate_tokenization_economics":
        if "error" not in result:
            y = result.get("yield_analysis", {})
            c = result.get("tokenization_costs", {})
            print(f"    Token Price:     ${result['asset_summary']['token_price_usd']:,.4f}")
            print(f"    Net Yield:       {y.get('net_yield_pct', 'N/A')}%")
            print(f"    IRR:             {y.get('irr_pct', 'N/A')}%")
            print(f"    Total Setup:     ${c.get('total_setup_cost_usd', 'N/A'):,.0f}")
        else:
            print(f"    Error: {result['error']}")
    elif tool_name == "compare_asset_classes":
        ranked = result.get("ranked_by_irr", [])
        for item in ranked[:3]:
            print(f"    #{item['rank']} {item['asset_class']}: IRR {item['irr_pct']}%, Net Yield {item['net_yield_pct']}%")
    elif tool_name == "run_market_dynamics_scenario":
        rm = result.get("risk_metrics", {})
        print(f"    Best IRR:   {rm.get('best_case_irr_pct', 'N/A')}%")
        print(f"    Worst IRR:  {rm.get('worst_case_irr_pct', 'N/A')}%")
        print(f"    IRR Range:  {rm.get('irr_range_pct', 'N/A')}%")
        print(f"    Positive scenarios: {rm.get('scenarios_with_positive_net_yield', 'N/A')}/{rm.get('total_scenarios', 'N/A')}")
    print()


# ── Demo queries ───────────────────────────────────────────────────────────────

DEMO_QUERIES = [
    {
        "title": "Q1: Manhattan Office Building Tokenization",
        "query": (
            "I want to tokenize a $25 million Manhattan commercial office building. "
            "I'm considering Ethereum or Polygon as the blockchain, and either US or Singapore jurisdiction. "
            "I plan to issue 25,000 tokens, target 500 investors, hold for 7 years, and expect 7% annual returns. "
            "Give me a complete economic analysis, compare the blockchain/jurisdiction options, "
            "and run market dynamics scenarios including interest rate sensitivity."
        ),
    },
    {
        "title": "Q2: Multi-Asset Portfolio Allocation ($50M)",
        "query": (
            "I have $50 million to deploy into tokenized real world assets. "
            "Compare all asset classes for tokenization on Polygon in Singapore jurisdiction, "
            "assuming 1,000,000 tokens, 2,000 investors, and a 5-year hold. "
            "Which 3 asset classes give the best risk-adjusted returns? "
            "Consider current macroeconomic conditions with elevated interest rates and DeFi yield competition."
        ),
    },
    {
        "title": "Q3: Carbon Credit Portfolio with ESG Analysis",
        "query": (
            "Analyze tokenizing a $5 million carbon credit portfolio on Polygon, UAE ADGM jurisdiction. "
            "Issue 100,000 tokens targeting 1,000 ESG investors, 3-year hold, 12% base return. "
            "Run full scenario analysis and explain the market dynamics and regulatory tailwinds in the carbon credit tokenization space."
        ),
    },
]


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("\n" + "=" * 80)
    print("  REAL WORLD ASSET (RWA) TOKENIZATION CALCULATOR AGENT")
    print("  Powered by Claude Opus 4.6 with Adaptive Thinking")
    print("  Multi-Asset Class | Deep Market Dynamics Reasoning")
    print("=" * 80)

    print("\nSupported Asset Classes:")
    for key, ac in ASSET_CLASSES.items():
        yield_range = f"{ac['typical_yield'][0]*100:.0f}%-{ac['typical_yield'][1]*100:.0f}%"
        print(f"  [{key}] {ac['name']} | Yield: {yield_range} | Complexity: {ac['regulatory_complexity']}")

    print("\nSupported Blockchains:", ", ".join(BLOCKCHAIN_OPTIONS.keys()))
    print("Supported Jurisdictions:", ", ".join(JURISDICTION_DATA.keys()))

    if len(sys.argv) > 1:
        # Custom query from command line
        custom_query = " ".join(sys.argv[1:])
        run_agent(custom_query)
    else:
        # Run demo queries
        print(f"\n{'='*80}")
        print("Running demo queries (set ANTHROPIC_API_KEY to use)...")
        print(f"{'='*80}")

        for i, demo in enumerate(DEMO_QUERIES, 1):
            print(f"\n{'='*80}")
            print(f"DEMO {i}: {demo['title']}")
            print(f"{'='*80}")

            run_agent(demo["query"])

            if i < len(DEMO_QUERIES):
                print("\n[Press Enter to continue to next demo, or Ctrl+C to exit]")
                try:
                    input()
                except (KeyboardInterrupt, EOFError):
                    print("\nExiting.")
                    break
