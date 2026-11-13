import asyncio
import json
import httpx2
import os

from httpx2 import Response
from openai import AsyncOpenAI, APITimeoutError, APIConnectionError
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletion
from pydantic import BaseModel
from typing import List

class ExplanationsResponse(BaseModel):
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
    transactions= [
        {"amount": 150, "currency": "AUD", "customer_tier": "FREE"},
        {"amount": 500, "currency": "AUD", "customer_tier": "VIP"},
    ]

    try:
        await health_check()
        client = create_vllm_client()
        async with client:
            models = await client.models.list()
            print("Available models:", [model.id for model in models.data])
            responses = await transactions_explainer(client, transactions)
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


async def transaction_explainer(client: AsyncOpenAI, transaction: dict) -> str:
    async with client:
        response: ChatCompletion = await client.chat.completions.create(
            model="transaction-explainer",
            messages= [ChatCompletionSystemMessageParam(
                role="system",
                content=(
                    "Describe the supplied transaction in two sentences. "
                    "Do not invent details. Amount and customer tier alone "
                    "cannot establish whether it is anomalous."
                ),
                name=f"role: user, content: {json.dumps(transaction)}",
            ),
            ],
            temperature=0,
            max_tokens=100,
        )

        explanation: str | None = response.choices[0].message.content
        print(f"Explanation: {explanation}")
        return explanation


async def transactions_explainer(client: AsyncOpenAI, transactions:List[dict]) -> List[ExplanationsResponse]:
    conversations = [
        [
            {
                "role": "system",
                "content": "Explain this transaction using only the supplied facts.",
            },
            {"role": "user", "content": json.dumps(transaction)},
        ]
        for transaction in transactions
    ]

    async with client:
        result = await client.post(
            "/chat/completions/batch",
            cast_to=dict,
            body={
                "model": "transaction-explainer",
                "messages": conversations,
                "max_tokens": 1000,
                "temperature": 0,
                "stream": False,
            },
        )

    return [
        ExplanationsResponse(
            index=choice["index"],
            content=choice["message"]["content"],
        )
        for choice in result["choices"]
    ]


if __name__ == "__main__":
   asyncio.run(main())

