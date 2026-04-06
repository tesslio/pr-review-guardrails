# Code Review for Payment Processing Refactor

## Problem/Feature Description

A backend engineer on your team submitted a pull request that refactors the payment processing module to support a new payment gateway. The change touches authentication token handling, SQL query construction, and retry logic. The team uses an automated review pipeline and you have been given the evidence pack it produced. Your job is to perform an independent code review and produce a set of candidate findings based solely on the evidence pack and the raw diff provided below.

The team's review process has had problems in the past with reviewers producing vague, style-focused comments that developers ignore. You need to produce findings that are specific, grounded in evidence, and explain real impact — not just describe what the code does differently.

## Output Specification

Produce a file `findings.json` containing an array of candidate findings from your review. Each finding must be a JSON object. The file should contain all findings that pass your evidence threshold, and must also include any findings you considered but chose to suppress (with reasons).

Do not produce a general summary — only the structured findings file.

## Input Files

The following files are provided as inputs. Extract them before beginning.

=============== FILE: inputs/evidence-pack.json ===============
{
  "risk_lane": "yellow",
  "changed_files": ["src/payments/gateway.py", "src/payments/retry.py", "src/db/queries.py"],
  "subsystems": ["payments", "database"],
  "hotspots": [
    {"file": "src/payments/gateway.py", "lines": "45-67", "category": "auth_token_handling"},
    {"file": "src/db/queries.py", "lines": "112-134", "category": "sql_construction"},
    {"file": "src/payments/retry.py", "lines": "23-41", "category": "retries"}
  ],
  "verifier_output": [
    {"verifier": "pytest", "status": "pass", "findings": []},
    {"verifier": "mypy", "status": "pass", "findings": []},
    {"verifier": "bandit", "status": "warn", "findings": [
      {"file": "src/db/queries.py", "line": 118, "issue": "B608: Possible SQL injection via string-based query construction", "severity": "medium"}
    ]},
    {"verifier": "pip-audit", "status": "pass", "findings": []}
  ],
  "stated_intent": "Refactor payment gateway integration to support Stripe and PayPal simultaneously. Adds retry logic with exponential backoff for transient failures.",
  "authorship": {"ai_assisted": false}
}

=============== FILE: inputs/pr.diff ===============
diff --git a/src/payments/gateway.py b/src/payments/gateway.py
index a1b2c3d..e4f5a6b 100644
--- a/src/payments/gateway.py
+++ b/src/payments/gateway.py
@@ -43,8 +43,25 @@ class PaymentGateway:
     def authenticate(self, provider: str):
-        token = self.config.get("api_key")
+        token = os.environ.get("PAYMENT_API_KEY") or self.config.get("api_key")
         if not token:
             raise ValueError("No API key configured")
+        self.session_token = token
+        self._last_auth_time = time.time()
+        return token
+
+    def _is_token_valid(self):
+        if not hasattr(self, '_last_auth_time'):
+            return False
+        return time.time() - self._last_auth_time < 3600
+
+    def charge(self, amount: float, currency: str, customer_id: str):
+        if not self._is_token_valid():
+            self.authenticate(self.current_provider)
+        payload = {
+            "amount": amount,
+            "currency": currency,
+            "customer": customer_id,
+            "idempotency_key": str(uuid.uuid4())
+        }
+        return self._post("/charge", payload)

diff --git a/src/db/queries.py b/src/db/queries.py
index b2c3d4e..f5a6b7c 100644
--- a/src/db/queries.py
+++ b/src/db/queries.py
@@ -110,8 +110,10 @@ class QueryBuilder:
     def get_payment_history(self, customer_id: str, status_filter: str = None):
-        query = "SELECT * FROM payments WHERE customer_id = %s"
-        params = [customer_id]
+        query = "SELECT * FROM payments WHERE customer_id = '" + customer_id + "'"
         if status_filter:
-            query += " AND status = %s"
-            params.append(status_filter)
-        return self.db.execute(query, params)
+            query += " AND status = '" + status_filter + "'"
+        return self.db.execute(query)

diff --git a/src/payments/retry.py b/src/payments/retry.py
index c3d4e5f..a6b7c8d 100644
--- a/src/payments/retry.py
+++ b/src/payments/retry.py
@@ -21,10 +21,19 @@ class RetryHandler:
     def execute_with_retry(self, fn, *args, **kwargs):
         attempts = 0
-        while attempts < self.max_retries:
+        while True:
             try:
                 return fn(*args, **kwargs)
             except TransientError as e:
                 attempts += 1
-                time.sleep(self.backoff_seconds)
+                time.sleep(self.backoff_seconds * attempts)
+                if attempts >= self.max_retries:
+                    raise
             except Exception:
                 raise
