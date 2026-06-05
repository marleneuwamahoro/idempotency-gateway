import threading
import time
import unittest

from app import create_app


class PaymentApiTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_first_payment_success(self):
        response = self.client.post(
            "/process-payment",
            headers={"Idempotency-Key": "first-key-123"},
            json={"amount": 100, "currency": "GHS"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["message"], "Charged 100 GHS")
        self.assertEqual(response.json["amount"], 100)
        self.assertEqual(response.json["currency"], "GHS")
        self.assertEqual(response.json["status"], "success")

    def test_duplicate_request_returns_cached_response(self):
        headers = {"Idempotency-Key": "duplicate-key-456"}
        payload = {"amount": 150, "currency": "GHS"}

        first = self.client.post("/process-payment", headers=headers, json=payload)
        second = self.client.post("/process-payment", headers=headers, json=payload)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.headers.get("X-Cache-Hit"), "true")
        self.assertEqual(first.json, second.json)

    def test_conflicting_body_for_same_key(self):
        headers = {"Idempotency-Key": "conflict-key-789"}

        first = self.client.post(
            "/process-payment",
            headers=headers,
            json={"amount": 200, "currency": "GHS"},
        )
        second = self.client.post(
            "/process-payment",
            headers=headers,
            json={"amount": 500, "currency": "GHS"},
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)
        self.assertIn("Idempotency key already used for a different request body.", second.json["error"])

    def test_inflight_duplicate_request_waits_for_result(self):
        headers = {"Idempotency-Key": "inflight-key-101"}
        payload = {"amount": 250, "currency": "GHS"}
        responses = []

        def send_request():
            responses.append(
                self.client.post("/process-payment", headers=headers, json=payload)
            )

        thread_a = threading.Thread(target=send_request)
        thread_b = threading.Thread(target=send_request)

        thread_a.start()
        time.sleep(0.1)
        thread_b.start()

        thread_a.join()
        thread_b.join()

        self.assertEqual(len(responses), 2)
        first_response = responses[0]
        second_response = responses[1]

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertEqual(second_response.headers.get("X-Cache-Hit"), "true")
        self.assertEqual(first_response.json, second_response.json)


if __name__ == "__main__":
    unittest.main()
