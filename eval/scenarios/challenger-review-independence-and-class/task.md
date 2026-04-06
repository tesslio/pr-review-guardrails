# Second-Opinion Review for an AI-Assisted Authentication Change

## Problem/Feature Description

Your organization uses an AI-assisted code review system with a two-pass architecture. A primary reviewer has already produced findings on a pull request that adds JWT-based session management to a Node.js API. Because this change was heavily AI-assisted and touches security-sensitive authentication logic, the team policy requires a second independent review pass to either corroborate or challenge the primary findings.

You are acting as the second reviewer. You have access to the evidence pack and the raw diff. You have NOT seen the primary reviewer's output and must not reference it. Your role is to produce your own independent set of findings — some may overlap with what the primary reviewer found, and some may be entirely new. Where you can identify that a concern is likely safe, say so.

## Output Specification

Produce the following files:

1. `challenger_findings.json` — your independent candidate findings. Each finding must follow the same schema as a primary finding, and must additionally include a `classification` field characterizing each finding's relationship to what a first-pass reviewer would likely discover.

2. `independence_check.md` — a brief statement (3–5 sentences) confirming the steps you took to ensure your review was independent, including whether you had access to primary review output and what your context isolation status is.

## Input Files

The following files are provided as inputs. Extract them before beginning.

=============== FILE: inputs/evidence-pack.json ===============
{
  "risk_lane": "red",
  "changed_files": ["src/auth/jwt.ts", "src/auth/session.ts", "src/middleware/auth.ts"],
  "subsystems": ["auth", "api"],
  "hotspots": [
    {"file": "src/auth/jwt.ts", "lines": "12-28", "category": "crypto"},
    {"file": "src/auth/session.ts", "lines": "44-71", "category": "auth_token_handling"},
    {"file": "src/middleware/auth.ts", "lines": "8-19", "category": "permission_checks"}
  ],
  "verifier_output": [
    {"verifier": "tsc", "status": "pass", "findings": []},
    {"verifier": "eslint", "status": "pass", "findings": []},
    {"verifier": "npm audit", "status": "pass", "findings": []},
    {"verifier": "semgrep", "status": "warn", "findings": [
      {"file": "src/auth/jwt.ts", "line": 14, "rule": "jwt-hardcoded-secret", "message": "JWT secret appears to have a hardcoded fallback value"}
    ]}
  ],
  "stated_intent": "Add JWT session management to replace cookie-based sessions. Tokens expire after 1 hour.",
  "authorship": {"ai_assisted": true, "ai_tools": ["GitHub Copilot"], "ai_commit_ratio": 0.78}
}

=============== FILE: inputs/pr.diff ===============
diff --git a/src/auth/jwt.ts b/src/auth/jwt.ts
index 1a2b3c4..5d6e7f8 100644
--- a/src/auth/jwt.ts
+++ b/src/auth/jwt.ts
@@ -10,6 +10,20 @@ import * as jwt from 'jsonwebtoken';
+const JWT_SECRET = process.env.JWT_SECRET ?? 'dev-only-insecure-secret-change-me';
+const JWT_EXPIRY = '1h';
+
+export function signToken(payload: object): string {
+  return jwt.sign(payload, JWT_SECRET, { expiresIn: JWT_EXPIRY });
+}
+
+export function verifyToken(token: string): object | null {
+  try {
+    return jwt.verify(token, JWT_SECRET) as object;
+  } catch {
+    return null;
+  }
+}

diff --git a/src/auth/session.ts b/src/auth/session.ts
index 2b3c4d5..6e7f8a9 100644
--- a/src/auth/session.ts
+++ b/src/auth/session.ts
@@ -42,10 +42,30 @@ export class SessionManager {
+  async createSession(userId: string, roles: string[]): Promise<string> {
+    const payload = { userId, roles, iat: Date.now() };
+    const token = signToken(payload);
+    await this.store.set(`session:${userId}`, token, { ttl: 3600 });
+    return token;
+  }
+
+  async validateSession(token: string): Promise<{ userId: string; roles: string[] } | null> {
+    const decoded = verifyToken(token);
+    if (!decoded) return null;
+    const stored = await this.store.get(`session:${decoded.userId}`);
+    if (stored !== token) return null;
+    return { userId: decoded.userId, roles: decoded.roles };
+  }

diff --git a/src/middleware/auth.ts b/src/middleware/auth.ts
index 3c4d5e6..7f8a9b0 100644
--- a/src/middleware/auth.ts
+++ b/src/middleware/auth.ts
@@ -6,4 +6,14 @@ import { SessionManager } from '../auth/session';
+export const requireAuth = (requiredRole?: string) => async (req: Request, res: Response, next: NextFunction) => {
+  const token = req.headers.authorization?.split(' ')[1];
+  if (!token) {
+    return res.status(401).json({ error: 'Unauthorized' });
+  }
+  const session = await sessionManager.validateSession(token);
+  if (!session) {
+    return res.status(401).json({ error: 'Invalid session' });
+  }
+  if (requiredRole && !session.roles.includes(requiredRole)) {
+    return res.status(403).json({ error: 'Forbidden' });
+  }
+  req.user = session;
+  next();
+};
