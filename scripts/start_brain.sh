#!/bin/bash
cd ~/llama.cpp
./build/bin/llama-server \
  -m DeepSeek-Coder-V2-Lite-Instruct-Q4_K_M.gguf \
  -c 8192 \
  -t 8 \
  -ngl 15 \
  --port 8080