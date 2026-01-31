#!/bin/bash
# Remove Docker and related packages

echo "Stopping Docker service..."
sudo systemctl stop docker.service docker.socket containerd.service

echo "Removing Docker packages..."
sudo apt-get purge -y \
  containerd.io \
  docker-buildx-plugin \
  docker-ce \
  docker-ce-cli \
  docker-ce-rootless-extras \
  docker-compose \
  docker-compose-plugin \
  python3-docker \
  python3-dockerpty

echo "Removing Docker data directories..."
sudo rm -rf /var/lib/docker
sudo rm -rf /var/lib/containerd

echo "Cleaning up APT..."
sudo apt-get autoremove -y
sudo apt-get autoclean

echo "Docker removed successfully!"
