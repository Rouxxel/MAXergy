/**
 * Railway Infrastructure as Code for MAXergy — one project, two services from this monorepo.
 *
 *   maxergy-api  FastAPI backend (backend/), Docker build from the repo root so the image
 *                contains the production engine (scripts/) and its data (data/).
 *   maxergy-mcp  MCP service (backend/mcp/), Railpack + uv.
 *
 * The services talk over Railway private networking:
 *   maxergy-mcp → maxergy-api  POST /plan, GET /assumptions   (bearer MAXERGY_SERVICE_TOKEN)
 *   maxergy-api → maxergy-mcp  enrichment tools via /mcp       (bearer MAXERGY_MCP_TOKEN)
 *
 * Secrets are `preserve()`d: set them once in Railway (see documentation/app/DEPLOYMENT.md);
 * the other service references them, so each secret lives in exactly one place.
 *
 * Usage (from the repo root): cd .railway && npm ci && cd .. && railway config plan
 * Type-check without Railway access: cd .railway && npx tsc --noEmit
 */
import { defineRailway, github, preserve, project, service, volume } from "railway/iac";

const REPO = "Rouxxel/MAXergy";
const BRANCH = "main";
const API_PORT = "8000";
const MCP_PORT = "8080";

export default defineRailway(() => {
  const branch = BRANCH;

  const mcpOauthState = volume("maxergy-mcp-oauth", { sizeMB: 512 });

  const api = service("maxergy-api", {
    source: github(REPO, { branch }),
    build: {
      builder: "DOCKERFILE",
      dockerfilePath: "backend/DOCKERFILE",
      watchPatterns: ["/backend/**", "/scripts/**", "/data/**", "!/backend/mcp/**"],
    },
    healthcheck: "/",
    healthcheckTimeout: 120,
    deploy: { restartPolicyType: "ON_FAILURE", restartPolicyMaxRetries: 3 },
    env: {
      PORT: API_PORT,
      ENVIRONMENT: "production",
      FORWARDED_ALLOW_IPS: "*",
      ALLOWED_HOSTS: "${{RAILWAY_PUBLIC_DOMAIN}},${{RAILWAY_PRIVATE_DOMAIN}},healthcheck.railway.app",
      CORS_ORIGINS: preserve(),
      GEMINI_API_KEY: preserve(),
      MCP_ENABLED: "true",
      MCP_BASE_URL: `http://\${{maxergy-mcp.RAILWAY_PRIVATE_DOMAIN}}:${MCP_PORT}`,
      MAXERGY_MCP_TOKEN: preserve(),
      MAXERGY_SERVICE_TOKEN: preserve(),
    },
  });

  const mcp = service("maxergy-mcp", {
    source: github(REPO, { branch, rootDirectory: "backend/mcp" }),
    build: {
      builder: "RAILPACK",
      watchPatterns: ["/backend/mcp/**"],
    },
    start: "uv run --no-dev maxergy-mcp",
    deploy: { restartPolicyType: "ON_FAILURE", restartPolicyMaxRetries: 3 },
    volumeMounts: { "/data": mcpOauthState },
    env: {
      PORT: MCP_PORT,
      MAXERGY_AUTH_MODE: "passphrase",
      MAXERGY_AUTH_PASSPHRASE: preserve(),
      MAXERGY_OAUTH_STATE_PATH: "/data/oauth.json",
      GOOGLE_MAPS_API_KEY: preserve(),
      MAXERGY_API_BASE_URL: `http://\${{maxergy-api.RAILWAY_PRIVATE_DOMAIN}}:${API_PORT}`,
      MAXERGY_SERVICE_TOKEN: api.env.MAXERGY_SERVICE_TOKEN,
      MAXERGY_INTERNAL_TOKENS: api.env.MAXERGY_MCP_TOKEN,
      LOG_LEVEL: "INFO",
    },
  });

  return project("maxergy", {
    resources: [api, mcp, mcpOauthState],
  });
});
