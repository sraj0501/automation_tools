/**
 * DevTrack anonymous usage ping worker.
 *
 * POST /ping  — record an install or active event
 * GET  /stats — return { installs, active_30d }
 *
 * KV layout:
 *   INSTALLS:fp:<fingerprint>  → { id, first_seen, last_seen, version, os, arch }
 *   ACTIVE:fp:<fingerprint>    → 1  (TTL 30 days — counts active installs)
 *
 * Rate limiting: per-IP, tracked in memory (resets per isolate restart).
 * Max MAX_NEW_FP_PER_IP_PER_HOUR new fingerprints per IP per hour.
 * Excess silently returns 200 — do not reveal the limit to clients.
 */

const ACTIVE_TTL_SECONDS = 30 * 24 * 60 * 60; // 30 days

// In-memory rate limit map: ip → { count, resetAt }
// Resets naturally when isolate restarts (typically every few hours).
const rateLimitMap = new Map();

function isRateLimited(ip, maxPerHour) {
  const now = Date.now();
  const entry = rateLimitMap.get(ip);
  if (!entry || now > entry.resetAt) {
    rateLimitMap.set(ip, { count: 1, resetAt: now + 3_600_000 });
    return false;
  }
  if (entry.count >= maxPerHour) return true;
  entry.count++;
  return false;
}

function validatePayload(body) {
  const { id, fingerprint, event, version, os, arch } = body;
  if (typeof id !== "string" || id.length > 64) return "invalid id";
  if (typeof fingerprint !== "string" || fingerprint.length > 128) return "invalid fingerprint";
  if (event !== "installed" && event !== "active") return "invalid event";
  if (typeof version !== "string" || version.length > 32) return "invalid version";
  if (typeof os !== "string" || os.length > 16) return "invalid os";
  if (typeof arch !== "string" || arch.length > 16) return "invalid arch";
  return null;
}

async function handlePing(request, env) {
  let body;
  try {
    body = await request.json();
  } catch {
    return new Response("bad json", { status: 400 });
  }

  const err = validatePayload(body);
  if (err) return new Response(err, { status: 400 });

  const { id, fingerprint, event, version, os, arch } = body;
  const fpKey = `fp:${fingerprint}`;
  const now = new Date().toISOString();
  const maxPerHour = parseInt(env.MAX_NEW_FP_PER_IP_PER_HOUR ?? "5", 10);
  const ip = request.headers.get("CF-Connecting-IP") ?? "unknown";

  // Check if this fingerprint is new (first install from this machine)
  const existing = await env.INSTALLS.get(fpKey);
  if (!existing) {
    // Rate-limit new fingerprints per IP to block VM farms
    if (isRateLimited(ip, maxPerHour)) {
      // Return 200 silently — do not reveal the limit
      return new Response(JSON.stringify({ ok: true }), {
        headers: { "Content-Type": "application/json" },
      });
    }
    await env.INSTALLS.put(
      fpKey,
      JSON.stringify({ id, first_seen: now, last_seen: now, version, os, arch })
    );
  } else {
    // Update last_seen and version
    const rec = JSON.parse(existing);
    rec.last_seen = now;
    rec.version = version;
    await env.INSTALLS.put(fpKey, JSON.stringify(rec));
  }

  // Always refresh the active TTL (30-day sliding window)
  await env.ACTIVE.put(fpKey, "1", { expirationTtl: ACTIVE_TTL_SECONDS });

  return new Response(JSON.stringify({ ok: true }), {
    headers: { "Content-Type": "application/json" },
  });
}

async function handleStats(env) {
  // List all keys in each namespace and count them.
  // Workers KV list is eventually consistent but good enough for badge counts.
  const [installsList, activeList] = await Promise.all([
    env.INSTALLS.list(),
    env.ACTIVE.list(),
  ]);
  return new Response(
    JSON.stringify({
      installs: installsList.keys.length,
      active_30d: activeList.keys.length,
    }),
    { headers: { "Content-Type": "application/json" } }
  );
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "POST" && url.pathname === "/ping") {
      return handlePing(request, env);
    }
    if (request.method === "GET" && url.pathname === "/stats") {
      return handleStats(env);
    }
    return new Response("not found", { status: 404 });
  },
};
