# Kubernetes Deployment Example

This guide provides example Kubernetes manifests for deploying TradingAgents.

## Prerequisites

- Kubernetes cluster (1.24+)
- kubectl configured
- Persistent volume provisioner
- Ingress controller (nginx, traefik, etc.)

## Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tradingagents
```

## ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tradingagents-config
  namespace: tradingagents
data:
  TRADINGAGENTS_LLM_PROVIDER: "openai"
  TRADINGAGENTS_DEEP_THINK_LLM: "o4-mini"
  TRADINGAGENTS_QUICK_THINK_LLM: "gpt-4o-mini"
  DATABASE_ECHO: "false"
  REDIS_ENABLED: "true"
  REDIS_HOST: "redis"
  REDIS_PORT: "6379"
  REDIS_DB: "0"
  STREAMING_ENABLED: "true"
  MONITORING_ENABLED: "true"
  METRICS_ENABLED: "true"
  WATCHDOG_ENABLED: "true"
  DEBUG: "false"
```

## Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: tradingagents-secrets
  namespace: tradingagents
type: Opaque
stringData:
  OPENAI_API_KEY: "your-openai-key"
  ALPHA_VANTAGE_API_KEY: "your-alpha-vantage-key"
  POSTGRES_PASSWORD: "secure-password"
  REDIS_PASSWORD: "secure-password"
  DATABASE_URL: "postgresql+asyncpg://tradingagents:secure-password@postgres:5432/tradingagents"
```

## PostgreSQL

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: tradingagents
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: tradingagents
spec:
  ports:
    - port: 5432
  selector:
    app: postgres
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: tradingagents
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        env:
        - name: POSTGRES_DB
          value: tradingagents
        - name: POSTGRES_USER
          value: tradingagents
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: tradingagents-secrets
              key: POSTGRES_PASSWORD
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 10Gi
```

## Redis

```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: tradingagents
spec:
  ports:
    - port: 6379
  selector:
    app: redis
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: tradingagents
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        args:
          - redis-server
          - --requirepass
          - $(REDIS_PASSWORD)
          - --maxmemory
          - 512mb
          - --maxmemory-policy
          - allkeys-lru
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: tradingagents-secrets
              key: REDIS_PASSWORD
        ports:
        - containerPort: 6379
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## Backend

```yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: tradingagents
spec:
  type: ClusterIP
  ports:
    - port: 8000
      targetPort: 8000
  selector:
    app: backend
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: tradingagents
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      initContainers:
      - name: migrate
        image: your-registry/tradingagents-backend:latest
        command: ['alembic', 'upgrade', 'head']
        envFrom:
        - configMapRef:
            name: tradingagents-config
        - secretRef:
            name: tradingagents-secrets
      containers:
      - name: backend
        image: your-registry/tradingagents-backend:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: tradingagents-config
        - secretRef:
            name: tradingagents-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
```

## Frontend

```yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: tradingagents
spec:
  type: ClusterIP
  ports:
    - port: 3000
      targetPort: 3000
  selector:
    app: frontend
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: tradingagents
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: your-registry/tradingagents-frontend:latest
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_API_URL
          value: "http://backend:8000"
        - name: NODE_ENV
          value: "production"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

## Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tradingagents-ingress
  namespace: tradingagents
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - tradingagents.example.com
    secretName: tradingagents-tls
  rules:
  - host: tradingagents.example.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
      - path: /sessions
        pathType: Prefix
        backend:
          service:
            name: backend
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 3000
```

## HorizontalPodAutoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: tradingagents
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Deployment Commands

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Create ConfigMap and Secrets
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml

# Deploy infrastructure
kubectl apply -f postgres.yaml
kubectl apply -f redis.yaml

# Wait for infrastructure to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n tradingagents --timeout=120s
kubectl wait --for=condition=ready pod -l app=redis -n tradingagents --timeout=60s

# Deploy application
kubectl apply -f backend.yaml
kubectl apply -f frontend.yaml

# Configure ingress
kubectl apply -f ingress.yaml

# Enable autoscaling
kubectl apply -f hpa.yaml

# Check status
kubectl get all -n tradingagents
```

## Monitoring

```bash
# View logs
kubectl logs -f -l app=backend -n tradingagents

# Check pod status
kubectl get pods -n tradingagents

# Describe service
kubectl describe service backend -n tradingagents

# Port forward for testing
kubectl port-forward -n tradingagents service/backend 8000:8000

# Execute command in pod
kubectl exec -it -n tradingagents deployment/backend -- /bin/sh
```

## Scaling

```bash
# Manual scaling
kubectl scale deployment backend -n tradingagents --replicas=5

# Check HPA status
kubectl get hpa -n tradingagents

# View HPA details
kubectl describe hpa backend-hpa -n tradingagents
```

## Updates

```bash
# Update image
kubectl set image deployment/backend -n tradingagents backend=your-registry/tradingagents-backend:v2

# Rolling restart
kubectl rollout restart deployment/backend -n tradingagents

# Check rollout status
kubectl rollout status deployment/backend -n tradingagents

# Rollback
kubectl rollout undo deployment/backend -n tradingagents
```

## Notes

- Replace `your-registry` with your container registry
- Update secrets with actual values
- Configure persistent volumes according to your storage class
- Adjust resource limits based on your workload
- Set up cert-manager for automatic SSL certificates
- Consider using Helm for easier management
