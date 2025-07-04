# Simulated Camera Fleet Backend

This project provides a scalable backend for managing a fleet of simulated camera devices, supporting patch distribution and device state tracking using FastAPI, Redis, and Kubernetes.

---

## Features

- **WebSocket API** for device communication
- **Patch distribution** to all connected devices
- **Stateless backend** using Redis for all shared state
- **Kubernetes-ready** for easy scaling and high availability

---

## Architecture

- **FastAPI** backend (Python)
- **Redis** for shared state (`patch_status`, `known_devices`, `in_flight_updates`, and patch file list)
- **Kubernetes** deployment with optional shared volume for patch files

---

## Quick Start (Local with Minikube)

### 1. Clone the Repository

```sh
git clone https://github.com/ataata107/simulated_camera_fleet.git
cd simulated_camera_fleet/server
```

### 2. Start Minikube and Use Its Docker Daemon

```sh
minikube start --driver=docker
eval $(minikube docker-env)
```

### 3. Build the Backend Docker Image

```sh
docker build -t simulated-camera-backend:latest .
```

### 4. Deploy Redis

```sh
kubectl apply -f redis.yaml
```

### 5. Deploy the Backend

```sh
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

### 6. Add Patch File Names to Redis

```sh
kubectl get pods -l app=redis
kubectl exec -it <redis-pod-name> -- redis-cli rpush patch_files patch1.txt patch2.txt
```


## Device Simulator

1. In a new terminal, **port-forward the backend service to your local machine**:

   ```sh
   kubectl port-forward service/camera-backend-service 31567:8000
   ```

2. Run the device simulator:

   ```sh
   python device.py cam_1
   ```
---

## Monitoring

- **Backend logs:**  
  ```sh
  kubectl logs -l app=camera-backend --follow
  ```
- **Redis CLI:**  
  ```sh
  kubectl exec -it <redis-pod-name> -- redis-cli
  ```

---

## Scaling

To scale the backend:
```sh
kubectl scale deployment camera-backend --replicas=3
```

---

## Notes

- Patch file names are managed in Redis (`patch_files` list).
- Actual patch files should be available in a shared volume or object store accessible by all backend pods and devices, right now it is just for testing.
- All device and patch state is stored in Redis for stateless scaling.

---

