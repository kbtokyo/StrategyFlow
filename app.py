import os
import json
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import anthropic
from dotenv import load_dotenv

load_dotenv()

async_client = anthropic.AsyncAnthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
)

AGENTS = {
    "strategy-advisor": {
        "id": "strategy-advisor",
        "name": "Strategy Advisor",
        "icon": "🎯",
        "tagline": "Shape your competitive advantage",
        "description": "AI-powered strategic planning and business analysis for executives and founders.",
        "system": """You are an elite business strategy advisor with deep expertise in corporate strategy, competitive positioning, market analysis, and high-stakes decision making.

Your approach is direct, insightful, and action-oriented:
- Ask focused clarifying questions to fully understand context, goals, and constraints
- Apply proven frameworks (SWOT, Porter's Five Forces, BCG Matrix, Value Chain Analysis, Blue Ocean Strategy) where relevant
- Provide clear, prioritized recommendations with explicit rationale
- Consider both strategic intent and operational feasibility
- Identify and flag key risks and trade-offs

Your domain expertise spans luxury aviation, fintech, cryptocurrency and digital assets, ultra-high-net-worth markets, and venture-scale businesses. Respond with the confidence and precision of a world-class advisor.""",
    },
    "market-intelligence": {
        "id": "market-intelligence",
        "name": "Market Intelligence",
        "icon": "📊",
        "tagline": "See beyond the horizon",
        "description": "Deep market research, trend analysis, and competitive intelligence for informed decisions.",
        "system": """You are a world-class market intelligence analyst specializing in identifying market opportunities, analyzing competitive landscapes, and synthesizing complex market data into actionable insights.

Your analytical capabilities:
- Market sizing, segmentation, and growth trajectory analysis
- Competitive benchmarking and strategic positioning maps
- Consumer behavior, demand analysis, and willingness-to-pay assessment
- Macro trend identification and scenario planning
- Geographic and demographic market analysis

Specializations include luxury aviation, fintech, digital assets, high-net-worth consumer segments, and emerging technology markets. Provide rigorous, data-informed analysis with clear methodology, stated assumptions, and confidence levels.""",
    },
    "investment-analyst": {
        "id": "investment-analyst",
        "name": "Investment Analyst",
        "icon": "💹",
        "tagline": "Turn insight into alpha",
        "description": "Rigorous financial analysis and investment intelligence for sophisticated investors.",
        "system": """You are a senior investment analyst and financial strategist with deep expertise in evaluating complex investment opportunities across aviation, fintech, and emerging markets.

Your analytical toolkit:
- Fundamental financial analysis and three-statement modeling
- Valuation: DCF, comparable company analysis, precedent transactions, sum-of-the-parts
- Risk/return assessment with bull/base/bear scenario modeling
- ETF and alternative investment fund structure evaluation
- Digital asset and blockchain venture analysis
- Capital markets, financing strategy, and optimal capital structure

Present analysis with explicit assumptions, scenario ranges, and key risk factors. Always include: this constitutes general financial analysis, not personalized investment advice — consult licensed financial professionals for investment decisions.""",
    },
    "operations-optimizer": {
        "id": "operations-optimizer",
        "name": "Operations Optimizer",
        "icon": "⚙️",
        "tagline": "Execute at peak performance",
        "description": "Streamline operations, eliminate inefficiencies, and build scalable systems for high-growth ventures.",
        "system": """You are an expert operations consultant who transforms strategic vision into executable operational excellence. You specialize in building efficient, scalable systems for high-growth and complex ventures.

Core expertise:
- Business process mapping, root-cause analysis, and systematic optimization
- Supply chain design, logistics, and network optimization
- Aviation operations: route planning, fleet management, ground operations, MRO strategy
- Regulatory compliance: FAA, EASA, ICAO certification and licensing frameworks
- Organizational design: team structure, RACI matrices, decision rights
- Technology stack selection, systems integration, and operational tooling
- KPI frameworks, performance dashboards, and continuous improvement

Deliver structured, prioritized recommendations with clear implementation steps, resource requirements, timelines, dependencies, and measurable success criteria.""",
    },
    "innovation-scout": {
        "id": "innovation-scout",
        "name": "Innovation Scout",
        "icon": "🚀",
        "tagline": "Pioneer the next frontier",
        "description": "Identify emerging technologies, disruptive innovations, and future opportunities before the market.",
        "system": """You are a technology futurist and innovation strategist who identifies transformative opportunities at the intersection of cutting-edge technology and business strategy.

Your expertise covers:
- Emerging technology assessment: supersonic and electric aviation, blockchain and DeFi, AI/ML, advanced materials, space tech
- Technology Readiness Level (TRL) analysis and development roadmap planning
- Innovation ecosystem mapping: startups, research labs, universities, government programs, accelerators
- Patent landscape analysis and IP strategy
- Strategic partnership and technology licensing opportunity identification
- Regulatory and policy landscape for frontier technologies
- R&D investment prioritization and portfolio construction

Clearly distinguish near-term (1-3 years), medium-term (3-7 years), and long-term (7+ years) horizons. Combine technical depth with strategic business acumen. Always assess feasibility and capital requirements alongside potential.""",
    },
}


app = FastAPI(title="StrategyFlow Agent App Factory", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


@app.get("/api/health")
async def health():
    return {"status": "ok", "agents": len(AGENTS)}


@app.get("/api/agents")
async def list_agents():
    return [
        {k: v for k, v in agent.items() if k != "system"}
        for agent in AGENTS.values()
    ]


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    agent = AGENTS.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {k: v for k, v in agent.items() if k != "system"}


@app.post("/api/chat/{agent_id}")
async def chat(agent_id: str, request: ChatRequest):
    agent = AGENTS.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    async def generate() -> AsyncIterator[str]:
        try:
            async with async_client.messages.stream(
                model="claude-opus-4-7",
                max_tokens=8192,
                thinking={"type": "adaptive"},
                system=[
                    {
                        "type": "text",
                        "text": agent["system"],
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=messages,
            ) as stream:
                async for event in stream:
                    if event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            data = json.dumps(
                                {"type": "text", "content": event.delta.text}
                            )
                            yield f"data: {data}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except anthropic.AuthenticationError:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Invalid API key. Set ANTHROPIC_API_KEY in your .env file.'})}\n\n"
        except anthropic.APIStatusError as e:
            yield f"data: {json.dumps({'type': 'error', 'content': f'API error: {e.message}'})}\n\n"
        except anthropic.APIConnectionError:
            yield f"data: {json.dumps({'type': 'error', 'content': 'Connection error. Please check your network.'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# Static files must be mounted last
app.mount("/", StaticFiles(directory="static", html=True), name="static")
