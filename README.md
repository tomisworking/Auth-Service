# AuthZ Service & Monitoring Stack

This is a mock **Authorization Service** built with Python and FastAPI, fully integrated with a modern monitoring stack (**Prometheus** & **Grafana**). Everything is containerized using Docker.

## Quick Start

1. **Prerequisites**: Make sure you have [Docker](https://www.docker.com/) installed.
2. **Start the stack**:
   Open your terminal in the project directory where `docker-compose.yml` is located and run:
   ```bash
   docker compose up -d
   ```
3. The following services will be available:
   - **AuthZ Application**: [http://localhost:8000](http://localhost:8000)
   - **Prometheus (Metrics)**: [http://localhost:9090](http://localhost:9090)
   - **Grafana (Dashboards)**: [http://localhost:3000](http://localhost:3000) *(Login: `admin` / Password: `admin123`)*

---

## How to Use the Application

This API simulates an authorization backend. It has a fake user database built-in:
- **alice** (password: `secret123`) - Roles: `admin`, `read`
- **bob** (password: `pass456`) - Roles: `read`
- **eve** (password: `hacker`) - Roles: none

### Available Endpoints

You can interact with these endpoints directly or explore them via the beautifully generated Swagger UI at **[http://localhost:8000/docs](http://localhost:8000/docs)**.

* `GET /health` : Returns system health status. Use this to verify if the app is running.
* `POST /token` : Log in and get a JWT Access Token. Provide `username` and `password`.
* `GET /check?resource={name}` : Checks if you have access to a specific resource (e.g., `database`, `logs`, `metrics`, `config`). **Requires the Bearer token** you got from `/token`.
* `GET /simulate` : **Highly recommended!** Clicking this endpoint will simulate random traffic internally. This is the absolute best way to generate fake traffic so you have something to watch on your monitoring dashboards!

---

## Monitoring & Dashboards

As people use the application (or as you hit the `/simulate` endpoint), the app generates metrics in the background. 

**Prometheus** automatically scrapes these metrics every 15 seconds. You can go to [http://localhost:9090/targets](http://localhost:9090/targets) to ensure Prometheus is successfully talking to the application.

**Grafana** is where you draw your charts. To set it up:
1. Go to [http://localhost:3000](http://localhost:3000).
2. Go to **Connections -> Data sources -> Add data source**.
3. Select **Prometheus**.
4. In the URL field, type: `http://prometheus:9090` (because Grafana communicates within the Docker network, it shouldn't be localhost!).
5. Click **Save & test**.
6. Go to **Dashboards** -> **New Dashboard** -> **Add Visualization**.
7. Now you can design dashboards using PromQL metrics like `authz_requests_total`, `authz_decisions_total`, or `authz_active_tokens`!

---

## Cloud Deployment & CI/CD

This project is built for the cloud and includes a fully automated CI/CD pipeline powered by **GitHub Actions**. Upon any push to the `main` branch, the workflow automatically:
1. **Tests the code:** Runs Python test suites to ensure stability.
2. **Builds & Pushes:** Creates a new Docker image and pushes it to **Azure Container Registry (ACR)**.
3. **Deploys to Azure:** Connects securely via SSH to an **Azure Virtual Machine**, pulls the latest Docker images, and restarts the live `docker-compose` stack with zero manual intervention.

---

## Stopping the Stack
To stop the services without deleting your Grafana dashboards, run:
```bash
docker compose stop
```
If you want to completely tear it down and wipe the metrics off your disk:
```bash
docker compose down -v
```
