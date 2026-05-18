import sys
from pathlib import Path

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent / "AGENT"))

from query_agent import run_query
from graph import run_report

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str


class ReportRequest(BaseModel):
    request: str


@app.post("/api/query")
async def query_endpoint(body: QueryRequest):
    result = await run_query(body.question)
    return {"result": result}


@app.post("/api/report")
async def report_endpoint(body: ReportRequest):
    result = await run_report(body.request)
    return {"result": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
