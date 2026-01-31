#!/bin/bash
# Import Docker images into k3s containerd

echo "Importing Docker images into k3s..."

sudo k3s ctr images import ~/k3s-images/kilo-images-1.tar
sudo k3s ctr images import ~/k3s-images/kilo-images-2.tar
sudo k3s ctr images import ~/k3s-images/kilo-images-3.tar
sudo k3s ctr images import ~/k3s-images/ollama.tar

echo "Done! Checking imported images..."
sudo k3s ctr images ls | grep -E "kilo|ollama"
