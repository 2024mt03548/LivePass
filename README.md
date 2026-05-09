# LivePass

LivePass is a mini microservices-based event ticket booking system built for a Scalable Services assignment. It demonstrates a common asynchronous booking flow using FastAPI services, PostgreSQL persistence, Redis caching, RabbitMQ messaging, Docker, and Kubernetes.

## Project Overview

Users can browse events, submit booking requests, and have bookings processed asynchronously by a worker. The booking API validates requests against the event API before publishing a message to RabbitMQ. The worker consumes booking messages, locks the target event row, creates the booking, reduces available seats, and invalidates cached event data.

## Architecture

```text
Client
  |
  | HTTP
  v
booking-service
  |
  | REST: GET /events/{id}
  v
event-service ---- Redis
  |
  | PostgreSQL
  v
postgres

booking-service
  |
  | publish booking_queue
  v
rabbitmq
  |
  | consume booking_queue
  v
booking-worker ---- PostgreSQL
       |
       | invalidate cache
       v
     Redis
```

## Services

| Service | Responsibility | Local Port |
| --- | --- | --- |
| `event-service` | Event CRUD API, PostgreSQL access, Redis caching for event reads | `8001` |
| `booking-service` | Booking request API, event validation, RabbitMQ producer | `8002` |
| `booking-worker` | RabbitMQ consumer, transactional booking creation, seat updates, cache invalidation | none |
| `postgres` | Stores events and bookings | `5432` |
| `redis` | Caches event list and event details | `6379` |
| `rabbitmq` | Booking queue broker and management UI | `5672`, `15672` |

## Setup With Docker Compose

Prerequisites:

- Docker
- Docker Compose

Start all services:

```bash
docker compose up --build
```

Run in the background:

```bash
docker compose up --build -d
```

Check containers:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f event-service
docker compose logs -f booking-service
docker compose logs -f booking-worker
```

Stop the stack:

```bash
docker compose down
```

Stop and remove volumes:

```bash
docker compose down -v
```

Local URLs:

- Event service: `http://localhost:8001`
- Booking service: `http://localhost:8002`
- RabbitMQ management UI: `http://localhost:15672`
- RabbitMQ default login: `guest` / `guest`

## Run Locally Without Docker

For normal development, Docker Compose is recommended because it starts PostgreSQL, Redis, and RabbitMQ with the correct service names.

To run an individual service manually, install dependencies and provide environment variables from the service `.env.example`.

Event service:

```bash
cd event-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Booking service:

```bash
cd booking-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
```

Booking worker:

```bash
cd booking-worker
pip install -r requirements.txt
python -m app.worker
```

When running outside Docker, use host-based URLs in your environment, for example:

```env
DATABASE_URL=postgresql://livepass:livepass@localhost:5432/livepass_events
REDIS_URL=redis://localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
EVENT_SERVICE_URL=http://localhost:8001
```

## Kubernetes Deployment

Kubernetes manifests are stored in `k8s/`.

Apply infrastructure services first:

```bash
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/rabbitmq.yaml
```

Apply application services:

```bash
kubectl apply -f k8s/event-service.yaml
kubectl apply -f k8s/booking-service.yaml
kubectl apply -f k8s/booking-worker.yaml
```

Or apply all manifests:

```bash
kubectl apply -f k8s/
```

Check deployments and pods:

```bash
kubectl get deployments
kubectl get pods
kubectl get services
```

View logs:

```bash
kubectl logs deploy/event-service
kubectl logs deploy/booking-service
kubectl logs deploy/booking-worker
```

The `booking-service` manifest exposes a NodePort service on port `30082`.

For Minikube:

```bash
minikube service booking-service
```

Or access it through the node IP:

```bash
kubectl get nodes -o wide
```

Then call:

```text
http://<node-ip>:30082
```

## Scaling Commands

Scale event-service:

```bash
kubectl scale deployment event-service --replicas=3
```

Scale booking-service:

```bash
kubectl scale deployment booking-service --replicas=3
```

Scale booking-worker:

```bash
kubectl scale deployment booking-worker --replicas=2
```

Verify scaling:

```bash
kubectl get deployments
kubectl get pods -l app=event-service
kubectl get pods -l app=booking-service
kubectl get pods -l app=booking-worker
```

## Sample API Requests

Create an event:

```bash
curl -X POST http://localhost:8001/events \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cloud Native Summit",
    "venue": "Main Auditorium",
    "event_date": "2026-06-15T18:00:00Z",
    "price": 1499.0,
    "available_seats": 100,
    "status": "active"
  }'
```

List events:

```bash
curl http://localhost:8001/events
```

Get event by ID:

```bash
curl http://localhost:8001/events/1
```

Update an event:

```bash
curl -X PUT http://localhost:8001/events/1 \
  -H "Content-Type: application/json" \
  -d '{
    "venue": "Conference Hall A",
    "available_seats": 120
  }'
```

Delete an event:

```bash
curl -X DELETE http://localhost:8001/events/1
```

Create a booking request:

```bash
curl -X POST http://localhost:8002/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 101,
    "event_id": 1,
    "tickets": 2
  }'
```

Expected response:

```json
{
  "message": "Booking request accepted"
}
```

Health checks:

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
```

## Repository Structure

```text
LivePass/
  booking-service/
  booking-worker/
  event-service/
  k8s/
  docker-compose.yml
  README.md
```
