# K8s Deployment

## Prerequisites

- A Kubernetes cluster (minikube, kind, or a cloud provider)
- `kubectl` configured to point at your cluster
- Images built and pushed to Docker Hub (see step 1 below)

---

## Deployment Steps

### 1. Build and push images

Run from the project root. Repeat for each service:

```bash
docker build -t edvardj/hikeapp-trips:latest     services/trips
docker build -t edvardj/hikeapp-gear:latest      services/gear
docker build -t edvardj/hikeapp-reminders:latest services/reminders
# docker build -t edvardj/hikeapp-ui:latest        services/ui

docker push edvardj/hikeapp-trips:latest
docker push edvardj/hikeapp-gear:latest
docker push edvardj/hikeapp-reminders:latest
# docker push edvardj/hikeapp-ui:latest
```

### 2. Create the PostgreSQL Secret

The secret is **not** stored in git. Create it from `storage.env` at the project root:

```bash
kubectl create secret generic postgres-secret \ --from-env-file=storage.env \ --dry-run=client yaml | kubectl apply -f -
```

`storage.env` must define `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`.
See `k8s/.env.example` for the required keys. Do not commit `storage.env`.

### 3. Apply manifests

Apply in dependency order (postgres must exist before the services that use it):

```bash
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/trips.yaml
kubectl apply -f k8s/gear.yaml
kubectl apply -f k8s/reminders.yaml
kubectl apply -f k8s/ui.yaml
```

Or apply the whole directory at once (Kubernetes handles ordering via readiness probes):

```bash
kubectl apply -f k8s/
```

### 4. Reach the app

- **Cloud cluster with LoadBalancer:**
  ```bash
  kubectl get svc ui
  # Open the EXTERNAL-IP in a browser
  ```
- **minikube:**
  ```bash
  minikube service ui
  ```
- **No external LoadBalancer:** change `ui`'s type to `NodePort` in `k8s/ui.yaml`.

---

## Service Name Reference

Kubernetes Service names act as internal DNS hostnames. All inter-service URLs use these names on port 8000 (or 5432 for postgres). These match the docker-compose service names exactly.

| Manifest | K8s Service name | Used by |
|---|---|---|
| `postgres.yaml` | `database` | trips, gear (`DATABASE_HOST=database`) |
| `trips.yaml` | `trips` | gear, reminders (`TRIPS_SERVICE_URL=http://trips:8000`) |
| `gear.yaml` | `gear` | reminders (`GEAR_SERVICE_URL=http://gear:8000`) |
| `reminders.yaml` | `reminders` | ui (`REMINDERS_SERVICE_URL=http://reminders:8000`) |
| `ui.yaml` | `ui` | external browser (LoadBalancer) |

---

## Environment Variables per Service

| Service | Source | Variables |
|---|---|---|
| `database` | `postgres-secret` | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` |
| `trips` | `postgres-secret` + env | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DATABASE_HOST=database` |
| `gear` | `postgres-secret` + env | same as trips + `TRIPS_SERVICE_URL=http://trips:8000` |
| `reminders` | env only | `TRIPS_SERVICE_URL=http://trips:8000`, `GEAR_SERVICE_URL=http://gear:8000` |
| `ui` | env only | `TRIPS_SERVICE_URL`, `GEAR_SERVICE_URL`, `REMINDERS_SERVICE_URL` |

Note: reminders has **no database** — it is a stateless aggregation service and takes no DB credentials.

---

## Assignment Criteria Checklist

| Criterion | Where satisfied |
|---|---|
| 1. Deployable on Kubernetes | all files under `k8s/` |
| 2. ≥2 microservice types + DB | trips, gear, reminders (3 types) + postgres |
| 3. Each microservice has a REST API | trips/gear/reminders are FastAPI with full CRUD |
| 4. Accessible from outside | each service exposed via NodePort/LoadBalancer; `/docs` Swagger UI in browser |
| 5. Independently horizontally scalable | separate Deployment + HPA per service |
| 6. Images on Docker Hub | `edvardj/hikeapp-<service>:latest` |
| 7. DB as separate microservice | `postgres.yaml` — own Deployment and Service |
| 8. Persistent storage | `postgres-pvc` (PVC) mounted into the postgres pod |
| 9. DB does not need to scale | `replicas: 1`, `strategy: Recreate` |

---

## Notes

- `storage.env` is local-only and gitignored. Use a strong password before any real deployment.
- `Base.metadata.create_all()` in trips and gear creates tables on first startup — no migration tool needed for initial deploy, but Alembic should be added for schema changes in production.
- If the `gear_list` table was previously created with a single `id` primary key, it must be dropped and recreated before the composite `(gear_id, trip_id)` primary key takes effect. Wipe the volume: `docker compose down -v && docker compose up --build`, or in K8s delete and reapply the PVC.
