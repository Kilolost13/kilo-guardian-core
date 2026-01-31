#!/bin/bash
# Fix imagePullPolicy for all deployments

kubectl patch deployment kilo-gateway -n kilo-guardian -p '{"spec":{"template":{"spec":{"containers":[{"name":"gateway","imagePullPolicy":"Never"}]}}}}'
kubectl patch deployment kilo-ai-brain -n kilo-guardian -p '{"spec":{"template":{"spec":{"containers":[{"name":"ai-brain","imagePullPolicy":"Never"}]}}}}'
kubectl patch deployment kilo-frontend -n kilo-guardian -p '{"spec":{"template":{"spec":{"containers":[{"name":"frontend","imagePullPolicy":"Never"}]}}}}'
kubectl patch deployment kilo-ollama -n kilo-guardian -p '{"spec":{"template":{"spec":{"containers":[{"name":"ollama","imagePullPolicy":"Never"}]}}}}'
kubectl patch deployment kilo-meds -n kilo-guardian -p '{"spec":{"template":{"spec":{"containers":[{"name":"meds","imagePullPolicy":"Never"}]}}}}'
kubectl patch deployment kilo-reminder -n kilo-guardian -p '{"spec":{"template":{"spec":{"containers":[{"name":"reminder","imagePullPolicy":"Never"}]}}}}'
kubectl patch deployment kilo-habits -n kilo-guardian -p '{"spec":{"template":{"spec":{"containers":[{"name":"habits","imagePullPolicy":"Never"}]}}}}'
kubectl patch deployment kilo-financial -n kilo-guardian -p '{"spec":{"template":{"spec":{"containers":[{"name":"financial","imagePullPolicy":"Never"}]}}}}'
kubectl patch deployment kilo-ml-engine -n kilo-guardian -p '{"spec":{"template":{"spec":{"containers":[{"name":"ml-engine","imagePullPolicy":"Never"}]}}}}'
kubectl patch deployment kilo-usb-transfer -n kilo-guardian -p '{"spec":{"template":{"spec":{"containers":[{"name":"usb-transfer","imagePullPolicy":"Never"}]}}}}'
kubectl patch deployment kilo-library -n kilo-guardian -p '{"spec":{"template":{"spec":{"containers":[{"name":"library","imagePullPolicy":"Never"}]}}}}'
kubectl patch deployment kilo-cam -n kilo-guardian -p '{"spec":{"template":{"spec":{"containers":[{"name":"cam","imagePullPolicy":"Never"}]}}}}'
kubectl patch deployment kilo-voice -n kilo-guardian -p '{"spec":{"template":{"spec":{"containers":[{"name":"voice","imagePullPolicy":"Never"}]}}}}'

echo "Waiting for pods to restart..."
sleep 10
kubectl get pods -n kilo-guardian
