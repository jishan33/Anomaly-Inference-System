import json
import httpx2
import unittest
from app.inference.clients import vllm_client
from openai import APITimeoutError
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace

VLLM_URL = "https://vllm.example.test"
API_KEY = "test-key"
MODEL = "transaction-explainer"

class TestHealthCheck(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(
            patch.multiple(vllm_client, URL=VLLM_URL, API_KEY=API_KEY)
        )
        self.client_factory = self.enterContext(
            patch.object(vllm_client.httpx2, "AsyncClient")
        )
        http_client = self.client_factory.return_value.__aenter__.return_value
        self.get = http_client.get = AsyncMock()
        self.request = httpx2.Request("GET", f"{VLLM_URL}/health")

    async def test_returns_200_when_healthy(self):
        self.get.return_value = httpx2.Response(200, request=self.request)

        status = await vllm_client.health_check()

        self.assertEqual(status, 200)
        self.client_factory.assert_called_once_with(timeout=3.0)
        self.get.assert_awaited_once_with(
            str(self.request.url),
            headers={"Authorization": f"Bearer {API_KEY}"},
        )

    async def test_wraps_503_as_runtime_error(self):
        self.get.return_value = httpx2.Response(503, request=self.request)

        with self.assertRaisesRegex(RuntimeError, "service is unavailable") as raised:
            await vllm_client.health_check()

        cause = raised.exception.__cause__
        self.assertIsInstance(cause, httpx2.HTTPStatusError)
        self.assertEqual(cause.response.status_code, 503)

    async def test_wraps_read_timeout_as_runtime_error(self):
        timeout = httpx2.ReadTimeout("Read timed out", request=self.request)
        self.get.side_effect = timeout

        with self.assertRaisesRegex(RuntimeError, "service is unavailable") as raised:
            await vllm_client.health_check()

        self.assertIs(raised.exception.__cause__, timeout)


class TestTransactionExplainer(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.transaction = {
            "amount": 150,
            "currency": "AUD",
            "customer_tier": "FREE",
        }
        self.client = MagicMock()
        self.create_completion = AsyncMock()
        self.client.chat.completions.create = self.create_completion

    async def test_sends_transaction_and_returns_completion(self):
        explanation = "A FREE-tier customer made a transaction of 150 AUD."
        self.create_completion.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=explanation))]
        )

        result = await vllm_client.transaction_explainer(
            self.client, self.transaction
        )

        self.assertEqual(result, explanation)
        self.create_completion.assert_awaited_once()

        request = self.create_completion.await_args.kwargs
        self.assertEqual(request["model"], MODEL)

        system_message = request["messages"][0]
        self.assertEqual(system_message["role"], "system")

        prefix = "role: user, content: "
        name = system_message["name"]
        self.assertTrue(name.startswith(prefix))
        self.assertEqual(json.loads(name.removeprefix(prefix)), self.transaction)

    async def test_propagates_timeout_to_caller(self):
        timeout = APITimeoutError(
            request=httpx2.Request("POST", f"{VLLM_URL}/v1/chat/completions")
        )
        self.create_completion.side_effect = timeout

        with self.assertRaises(APITimeoutError) as raised:
            await vllm_client.transaction_explainer(self.client, self.transaction)

        self.assertIs(raised.exception, timeout)


class TestTransactionsExplainer(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = MagicMock()
        self.client.post = AsyncMock()
        self.transactions = [
            {"amount": 150, "currency": "AUD", "customer_tier": "FREE"},
            {"amount": 500, "currency": "AUD", "customer_tier": "VIP"},
        ]

    async def test_sends_one_conversation_per_transaction(self):
        self.client.post.return_value = {
            "choices": [
                {"index": 1, "message": {"content": "VIP explanation"}},
                {"index": 0, "message": {"content": "FREE explanation"}},
            ]
        }

        responses = await vllm_client.transactions_explainer(
            self.client, self.transactions
        )

        self.client.post.assert_awaited_once()
        call = self.client.post.await_args
        self.assertEqual(call.args, ("/chat/completions/batch",))
        self.assertIs(call.kwargs["cast_to"], dict)

        body = call.kwargs["body"]
        self.assertEqual(body["model"], MODEL)
        self.assertIs(body["stream"], False)

        conversations = body["messages"]
        self.assertEqual(len(conversations), len(self.transactions))

        for index, (conversation, transaction) in enumerate(
                zip(conversations, self.transactions)
        ):
            with self.subTest(transaction_index=index):
                system_message, user_message = conversation
                self.assertEqual(system_message["role"], "system")
                self.assertEqual(user_message["role"], "user")
                self.assertEqual(json.loads(user_message["content"]), transaction)

        self.assertEqual(
            [(response.index, response.content) for response in responses],
            [(1, "VIP explanation"), (0, "FREE explanation")],
        )

    async def test_propagates_timeout_to_caller(self):
        timeout = APITimeoutError(
            request=httpx2.Request(
                "POST", f"{VLLM_URL}/v1/chat/completions/batch"
            )
        )
        self.client.post.side_effect = timeout

        with self.assertRaises(APITimeoutError) as raised:
            await vllm_client.transactions_explainer(
                self.client, self.transactions
            )

        self.assertIs(raised.exception, timeout)