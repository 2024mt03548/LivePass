# LivePass

LivePass is a small microservices-based event ticket booking system. It uses FastAPI services, PostgreSQL, Redis, RabbitMQ, Docker Compose, and Kubernetes to demonstrate an asynchronous booking flow with clear service ownership.

## Project Overview

Users can browse events, submit booking requests, and check their booking history. Booking requests are accepted immediately by the public API, processed asynchronously by a worker, and finalized only after event-service reserves inventory.

The key service boundary is:

- `event-service` owns events and inventory.
- `booking-worker` owns booking writes.
- `booking-service` owns the public booking API and reads booking history.
- Redis is only used by event-service for public event read caching.
- RabbitMQ is only used for `booking.requested` messages.

## Architecture

```text
Client
  |
  | GET /events, GET /events/{id}
  v
event-service ---- Redis
  |
  | owns events + inventory
  v
event-postgres

Client
  |
  | POST /bookings
  v
booking-service
  |
  | publish booking.requested
  v
rabbitmq
  |
  | consume booking.requested
  v
booking-worker
  |
  | POST /internal/inventory/reserve
  v
event-service
  |
  | write final booking status
  v
booking-postgres

Client
  |
  | GET /bookings/users/{user_id}
  v
booking-service
  |
  | read booking history
  v
booking-postgres
```

## Services

| Service | Responsibility | Local Port |
| --- | --- | --- |
| `event-service` | Public event reads, internal event management, internal inventory reservation, event DB access, Redis cache management | `8001` |
| `booking-service` | Public booking API, RabbitMQ producer, booking history reads | `8002` |
| `booking-worker` | RabbitMQ consumer, event inventory reservation client, final booking persistence | none |
| `event-postgres` | Stores events and inventory state | `5432` |
| `booking-postgres` | Stores booking records and final booking status | `5433` |
| `redis` | Caches `events:list` and `event:{id}` for event-service | `6379` |
| `rabbitmq` | Broker for `booking.requested`; management UI on `15672` | `5672`, `15672` |

## Public APIs

Event discovery:

```text
GET /events
GET /events/{event_id}
```

Booking:

```text
POST /bookings
GET /bookings/users/{user_id}
```

Health checks:

```text
GET /health
```

## Internal APIs

Event management:

```text
POST /internal/events
PUT /internal/events/{event_id}
DELETE /internal/events/{event_id}
```

Inventory reservation:

```text
POST /internal/inventory/reserve
```

The inventory reservation endpoint bypasses Redis, locks the event row in PostgreSQL, validates event status and seat availability, decrements seats atomically, marks events as `SOLD_OUT` when seats reach zero, and invalidates affected Redis cache keys after a successful update.

## Async Booking Flow

1. Client calls `POST /bookings`.
2. `booking-service` validates the request shape and checks event-service reachability.
3. `booking-service` publishes a `booking.requested` message to RabbitMQ.
4. `booking-worker` consumes the message.
5. `booking-worker` calls `event-service` at `POST /internal/inventory/reserve`.
6. If reservation succeeds, `booking-worker` writes a `CONFIRMED` booking.
7. If reservation fails, `booking-worker` writes a `FAILED` booking.
8. Client can check final status with `GET /bookings/users/{user_id}`.

RabbitMQ message shape:

```json
{
  "user_id": 101,
  "event_id": 1,
  "tickets": 2,
  "requested_at": "2026-05-10T10:00:00Z"
}
```

## Docker Compose

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
- RabbitMQ login: `guest` / `guest`

Compose builds these app images, matching the Kubernetes manifests:

```text
livepass/event-service:latest
livepass/booking-service:latest
livepass/booking-worker:latest
```

## Local Development Without Docker

Docker Compose is recommended because it starts PostgreSQL, Redis, and RabbitMQ with the same service names used by the containers. To run services manually, start the infrastructure dependencies first and use host-based URLs.

Event service:

```bash
cd event-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Example environment:

```env
DATABASE_URL=postgresql://livepass:livepass@localhost:5432/livepass_events
REDIS_URL=redis://localhost:6379/0
```

Booking service:

```bash
cd booking-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
```

Example environment:

```env
EVENT_SERVICE_URL=http://localhost:8001
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
BOOKING_QUEUE=booking.requested
BOOKING_DATABASE_URL=postgresql://livepass:livepass@localhost:5433/livepass_bookings
```

Booking worker:

```bash
cd booking-worker
pip install -r requirements.txt
python -m app.worker
```

Example environment:

```env
DATABASE_URL=postgresql://livepass:livepass@localhost:5433/livepass_bookings
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
BOOKING_QUEUE=booking.requested
EVENT_SERVICE_URL=http://localhost:8001
```

## Kubernetes Deployment

Kubernetes manifests are stored in `k8s/`.

Apply infrastructure first:

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

Or apply everything:

```bash
kubectl apply -f k8s/
```

Kubernetes resources include:

- `event-service`: 2 replicas, ClusterIP
- `booking-service`: 2 replicas, NodePort `30082`
- `booking-worker`: 2 replicas
- `event-postgres`: 1 replica, PVC, init ConfigMap
- `booking-postgres`: 1 replica, PVC, init ConfigMap
- `redis`: 1 replica
- `rabbitmq`: 1 replica

Check resources:

```bash
kubectl get deployments
kubectl get pods
kubectl get services
kubectl get pvc
```

View logs:

```bash
kubectl logs deploy/event-service
kubectl logs deploy/booking-service
kubectl logs deploy/booking-worker
```

Access `booking-service` through the NodePort:

```text
http://<node-ip>:30082
```

For Minikube:

```bash
minikube service booking-service
```

## Sample API Requests

List events:

```bash
curl http://localhost:8001/events
```

Get event by ID:

```bash
curl http://localhost:8001/events/1
```

Create an event internally:

```bash
curl -X POST http://localhost:8001/internal/events \
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

Update an event internally:

```bash
curl -X PUT http://localhost:8001/internal/events/1 \
  -H "Content-Type: application/json" \
  -d '{
    "venue": "Conference Hall A",
    "available_seats": 120
  }'
```

Delete an event internally:

```bash
curl -X DELETE http://localhost:8001/internal/events/1
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
  "message": "Booking request accepted for processing"
}
```

Check bookings for a user:

```bash
curl http://localhost:8002/bookings/users/101
```

Health checks:

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
```

## Cache Keys

event-service uses Redis for public event reads:

```text
events:list
event:{event_id}
```

These keys are invalidated after successful internal event management changes and successful inventory reservation.

## Repository Structure

```text
LivePass/
  booking-service/
  booking-worker/
  db/
    booking-init/
    event-init/
  event-service/
  k8s/
  docker-compose.yml
  README.md
```
