import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from pydantic import ValidationError
from redis.exceptions import RedisError
from app.api import transaction as txn_module


CUSTOMER_TOKEN = "C_ABCDEFGHIJKLM"
TRANSACTION_TOKEN = "TXN_A1B2C3D4E5F60789"
REQUEST_ID = "test-request"
NOW = 1_000.0


def make_transaction(token=TRANSACTION_TOKEN):
    return txn_module.Transaction(
        amount=150.0,
        created_at="2026-11-12T03:00:00+00:00",
        type="PAYMENT",
        customer_token=CUSTOMER_TOKEN,
        transaction_token=token,
    )


class TestTransaction(unittest.TestCase):
    def test_accepts_minimum_and_maximum_token_lengths(self):
        for suffix_length in (16, 76):
            token = f"TXN_{'A' * suffix_length}"
            with self.subTest(token_length=len(token)):
                self.assertEqual(make_transaction(token).transaction_token, token)

    def test_rejects_invalid_transaction_tokens(self):
        invalid_tokens = (
            "TXN_" + "A" * 15,
            "TXN_" + "A" * 77,
            "BAD_" + "A" * 16,
            "TXN_" + "A" * 15 + "-",
        )

        for token in invalid_tokens:
            with self.subTest(token=token):
                with self.assertRaises(ValidationError) as raised:
                    make_transaction(token)

                self.assertEqual(
                    raised.exception.errors()[0]["loc"],
                    ("transaction_token",),
                )

    def test_generates_valid_transaction(self):
        transaction = txn_module.generate_random_transaction()

        self.assertIsInstance(transaction, txn_module.Transaction)
        self.assertGreater(transaction.amount, 0)
        self.assertIn(transaction.type, {"PAYMENT", "REFUND", "TRANSFER"})
        self.assertRegex(transaction.transaction_token, r"^TXN_[A-F0-9]{26}$")
        self.assertEqual(
            datetime.fromisoformat(transaction.created_at).utcoffset(),
            timedelta(0),
        )


class TestTransactionRedis(unittest.TestCase):
    def setUp(self):
        self.redis_client = self.enterContext(
            patch.object(txn_module, "redis_client")
        )
        self.breaker = self.enterContext(
            patch.object(txn_module, "redis_circuit_breaker")
        )
        self.retry = self.enterContext(
            patch.object(txn_module, "retry_with_backoff")
        )
        self.gauge = self.enterContext(
            patch.object(txn_module, "VOLUME_GAUGE")
        )
        self.enterContext(
            patch.object(txn_module.time, "time", return_value=NOW)
        )

        # Execute the real Redis operation callback through both mocked layers.
        self.breaker.call.side_effect = lambda operation, **kwargs: operation()
        self.retry.side_effect = lambda operation, **kwargs: operation()

    def test_append_stores_details_and_updates_both_indexes(self):
        transaction = make_transaction()
        data_key = f"txn:{TRANSACTION_TOKEN}"
        customer_key = f"customer_index:{CUSTOMER_TOKEN}"
        entry = {TRANSACTION_TOKEN: NOW}

        txn_module.append_to_redis([transaction], request_id=REQUEST_ID)

        self.redis_client.hset.assert_called_once_with(
            data_key, mapping=transaction.model_dump()
        )
        self.redis_client.expire.assert_called_once_with(data_key, 60)
        self.redis_client.zadd.assert_any_call("transactions", entry)
        self.redis_client.zadd.assert_any_call(customer_key, entry)
        self.redis_client.zremrangebyscore.assert_any_call(customer_key, 0, 940.0)
        self.redis_client.zremrangebyscore.assert_any_call("transactions", 0, 940.0)
        self.gauge.inc.assert_called_once_with()

    def test_append_logs_redis_failure_without_incrementing_gauge(self):
        self.redis_client.hset.side_effect = RedisError(
            "Redis unavailable"
        )

        with self.assertLogs(txn_module.logger, level="ERROR") as logs:
            txn_module.append_to_redis([make_transaction()], request_id=REQUEST_ID)

        self.assertEqual(logs.records[0].extra_data["request_id"], REQUEST_ID)
        self.gauge.inc.assert_not_called()

    def test_get_volume_counts_transactions_in_last_60_seconds(self):
        self.redis_client.zcount.return_value = 7

        self.assertEqual(txn_module.get_volume(REQUEST_ID), 7)

        self.redis_client.zcount.assert_called_once_with(
            "transactions", 940.0, NOW
        )

    def test_get_customer_volume_counts_only_that_customer(self):
        self.redis_client.zcount.return_value = 3

        result = txn_module.get_customer_transaction_volume(
            CUSTOMER_TOKEN, REQUEST_ID
        )

        self.assertEqual(result, 3)
        self.redis_client.zcount.assert_called_once_with(
            f"customer_index:{CUSTOMER_TOKEN}", 940.0, NOW
        )

    def test_volume_queries_return_zero_when_redis_fails(self):
        self.redis_client.zcount.side_effect = RedisError(
            "Redis unavailable"
        )
        queries = (
            (txn_module.get_volume, (REQUEST_ID,)),
            (
                txn_module.get_customer_transaction_volume,
                (CUSTOMER_TOKEN, REQUEST_ID),
            ),
        )

        for query, args in queries:
            with self.subTest(query=query.__name__):
                with self.assertLogs(txn_module.logger, level="ERROR"):
                    self.assertEqual(query(*args), 0)


class TestSafeVolumeWrappers(unittest.TestCase):
    def test_safe_get_volume_returns_zero_when_underlying_call_raises(self):
        with patch.object(
                txn_module, "get_volume", side_effect=RuntimeError("unexpected error")
        ) as get_volume:
            self.assertEqual(txn_module.safe_get_volume(), 0)

        get_volume.assert_called_once_with("unknown")

    def test_safe_get_customer_volume_forwards_arguments_and_result(self):
        with patch.object(
                txn_module, "get_customer_transaction_volume", return_value=4
        ) as get_customer_volume:
            result = txn_module.safe_get_customer_transaction_volume(
                CUSTOMER_TOKEN, REQUEST_ID
            )

        self.assertEqual(result, 4)
        get_customer_volume.assert_called_once_with(CUSTOMER_TOKEN, REQUEST_ID)

    def test_safe_get_customer_volume_returns_zero_on_exception(self):
        with patch.object(
                txn_module,
                "get_customer_transaction_volume",
                side_effect=RuntimeError("unexpected error"),
        ):
            self.assertEqual(
                txn_module.safe_get_customer_transaction_volume(CUSTOMER_TOKEN), 0
            )