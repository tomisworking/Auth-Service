from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from pydantic import BaseModel
from jose import JWTError, jwt
from datetime import datetime, timedelta
import time
import random

app = FastAPI(title="AuthZ Service", description="Authorization service with Prometheus metrics")
security = HTTPBearer()

# --- Konfiguracja JWT ---
SECRET_KEY = "super-secret-key-change-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30

# --- Metryki Prometheus ---
REQUEST_COUNT = Counter(
    "authz_requests_total",
    "Total number of AuthZ requests",
    ["method", "endpoint", "status_code"]
)

REQUEST_LATENCY = Histogram(
    "authz_request_duration_seconds",
    "Request latency in seconds",
    ["endpoint"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

AUTH_DECISIONS = Counter(
    "authz_decisions_total",
    "Total authorization decisions",
    ["decision", "resource"]  # decision: allow / deny
)

ACTIVE_TOKENS = Gauge(
    "authz_active_tokens",
    "Number of currently active tokens"
)

TOKEN_ISSUE_COUNT = Counter(
    "authz_tokens_issued_total",
    "Total tokens issued"
)

# --- Fake baza użytkowników ---
USERS = {
    "alice": {"password": "secret123", "roles": ["admin", "read"]},
    "bob":   {"password": "pass456",   "roles": ["read"]},
    "eve":   {"password": "hacker",    "roles": []},
}

# --- Fake zasoby i wymagane role ---
RESOURCES = {
    "database": "admin",
    "logs":     "read",
    "metrics":  "read",
    "config":   "admin",
}

# --- Middleware do mierzenia czasu i liczenia requestów ---
@app.middleware("http")
async def metrics_middleware(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    endpoint = request.url.path
    if endpoint != "/metrics":  # Nie mierz samego /metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=str(response.status_code)
        ).inc()
        REQUEST_LATENCY.labels(endpoint=endpoint).observe(duration)

    return response

# --- Modele ---
class LoginRequest(BaseModel):
    username: str
    password: str

class CheckRequest(BaseModel):
    resource: str

# --- Helpery JWT ---
def create_token(username: str, roles: list) -> str:
    payload = {
        "sub": username,
        "roles": roles,
        "exp": datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# --- Endpointy ---
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.post("/token")
def login(req: LoginRequest):
    """Wydaj token JWT po poprawnym logowaniu."""
    user = USERS.get(req.username)
    if not user or user["password"] != req.password:
        REQUEST_COUNT.labels(method="POST", endpoint="/token", status_code=401).inc()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token(req.username, user["roles"])
    ACTIVE_TOKENS.inc()
    TOKEN_ISSUE_COUNT.inc()
    return {"access_token": token, "token_type": "bearer", "expires_in": TOKEN_EXPIRE_MINUTES * 60}

@app.get("/check")
def check_access(resource: str, payload: dict = Depends(verify_token)):
    """Sprawdź czy użytkownik ma dostęp do zasobu."""
    username = payload.get("sub")
    roles = payload.get("roles", [])

    if resource not in RESOURCES:
        raise HTTPException(status_code=404, detail=f"Resource '{resource}' not found")

    required_role = RESOURCES[resource]
    allowed = required_role in roles

    decision = "allow" if allowed else "deny"
    AUTH_DECISIONS.labels(decision=decision, resource=resource).inc()

    if not allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: resource '{resource}' requires role '{required_role}'"
        )

    return {"allowed": True, "user": username, "resource": resource}

@app.get("/metrics")
def metrics():
    """Endpoint dla Prometheusa — eksponuje metryki."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/simulate")
def simulate_load():
    """Endpoint do generowania sztucznego ruchu (demo)."""
    users = list(USERS.keys())
    resources = list(RESOURCES.keys())

    results = []
    for _ in range(10):
        user = random.choice(users)
        resource = random.choice(resources)
        roles = USERS[user]["roles"]
        required = RESOURCES[resource]
        decision = "allow" if required in roles else "deny"
        AUTH_DECISIONS.labels(decision=decision, resource=resource).inc()
        results.append({"user": user, "resource": resource, "decision": decision})

    return {"simulated": len(results), "results": results}