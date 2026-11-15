import asyncio
import httpx2
import os

from app.api.transaction import Transaction, generate_risk_evaluated_transaction
from httpx2 import Response
from openai import AsyncOpenAI, APITimeoutError, APIConnectionError
from pydantic import BaseModel
from typing import List

from app.inference.models.risk_sunmmary_model import to_risk_summary_requests


class ExplanationResponse(BaseModel):
    index: int
    content: str

URL = os.getenv("VLLM_URL")
API_KEY = os.getenv("VLLM_API_KEY")

def create_vllm_client() -> AsyncOpenAI:
    if not URL or not API_KEY:
        raise RuntimeError("VLLM_URL or VLLM_API_KEY is missing or empty")

    return AsyncOpenAI(
        base_url=f"{URL}/v1",
        api_key=API_KEY,
        timeout=3.0,
        max_retries=0,
    )

async def main():
    txn = generate_risk_evaluated_transaction()

    try:
        await health_check()
        client = create_vllm_client()
        async with client:
            models = await client.models.list()
            print("Available models:", [model.id for model in models.data])
            responses = await transaction_explainer(client, [(txn, "job_id")])
            print(f"Responses: {responses}")

    except (TimeoutError, APITimeoutError, APIConnectionError) as exc:
        raise RuntimeError("The transaction explanation service is unavailable right now.", exc)

async def health_check() -> int:
    try:
        async with httpx2.AsyncClient(timeout=3.0) as http:
            response: Response = await http.get(
                f"{URL}/health",
                headers={"Authorization": f"Bearer {API_KEY}"},
            )
            response.raise_for_status()
            print(f"Health HTTP {response.status_code}")
    except (httpx2.HTTPError, APIConnectionError) as exc:
        raise RuntimeError(
            "The transaction explanation service is unavailable right now."
        ) from exc

    return response.status_code


async def transaction_explainer(client: AsyncOpenAI, transactions_with_job_ids: list[tuple[Transaction, str]]) -> List[ExplanationResponse]:
    requests = to_risk_summary_requests(transactions_with_job_ids)

    conversations = [
        [
            {
                "role": "system",
                "content": "Explain this request using only the supplied facts.",
            },
            {"role": "user", "content": request.model_dump_json()},
        ]
        for request in requests
    ]

    async with client:
        result = await client.post(
            "/chat/completions/batch",
            cast_to=dict,
            body={
                "model": "request-explainer",
                "messages": conversations,
                "max_tokens": 1000,
                "temperature": 0,
                "stream": False,
            },
        )

    return [
        ExplanationResponse(
            index=choice["index"],
            content=choice["message"]["content"],
        )
        for choice in result["choices"]
    ]


if __name__ == "__main__":
   asyncio.run(main())

