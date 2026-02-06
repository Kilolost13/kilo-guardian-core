# Kilo Guardian: Architectural Overview

## 1. Core Philosophy
Kilo Guardian is built as a **decentralized intelligent assistant** running on a **K3s (Kubernetes)** cluster. Unlike traditional monoliths, it distributes specialized tasks across independent microservices while maintaining a **Unified Memory** and **Unified Intelligence** layer.

## 2. Infrastructure (The "Skeleton")
*   **Platform:** K3s (Lightweight Kubernetes) running on a dedicated Linux node (`pop-os`).
*   **Orchestration:** Managed via `kubectl` with custom YAML manifests. Services are containerized using Docker.
*   **Hardware Awareness:** The system is optimized for local execution (Ollama) and is sensitive to power stability (voltage spike protection).

## 3. Intelligence Layer (The "Brain")
The intelligence is split into two primary tiers:
*   **Kilo AI Brain:** A high-level reasoning engine powered by **Ollama**. It handles complex natural language processing, intent extraction, and long-term planning.
*   **Guardian Core:** The primary interface that handles user interaction and delegates "deep thinking" tasks to the AI Brain via high-speed internal API calls.

## 4. Shared State & Memory (The "Consciousness")
To prevent "split-brain" behavior, all services share a single source of truth:
*   **Shared PVC:** A Persistent Volume Claim (`shared-kilo-data`) is mounted across all critical pods at `/app/kilo_data`.
*   **Unified Database:** A centralized SQLite database (`kilo_guardian.db`) resides on the PVC. This ensures that if you add a medication in the `Meds` service, the `Habits` and `Reminder` services see it instantly.
*   **Shared Library:** A centralized `shared/` Python package contains unified `SQLModel` definitions and utilities (like OCR logic), ensuring data structures are identical across the entire cluster.

## 5. Microservice Ecosystem (The "Limbs")
Specialized modules handle specific real-world functions:
*   **Drone FPV & Mesh Tracking:** Manages hardware-level integration for drone control and Meshtastic network monitoring.
*   **Financial Service:** Processes transactions and performs OCR on receipts to track budgets.
*   **Meds & Habits:** Synchronized services that track health adherence, extracting data from prescription labels using Tesseract/OpenCV.
*   **Reminder Service:** A background scheduler (`APScheduler`) that triggers alerts based on the unified database state.
*   **Unified Agent:** Acts as the cluster's internal router and proactive monitor, providing a single entry point for the frontend.

## 6. Frontend & Oversight
*   **Kilo Portal:** An Angular 21 / React hybrid dashboard that communicates with the **Unified Agent**.
*   **Proactive Monitoring:** The system monitors its own health (disk pressure, pod status) and reports it to the Admin Panel in real-time.

## 7. Data Flow Example: Adding a Medication
1.  **User** uploads a photo via the Portal.
2.  **Meds Service** receives the image, saves it to the **Shared PVC**.
3.  **Meds Service** uses the **Shared OCR Utility** to extract text.
4.  Data is written to the **Unified SQLite DB**.
5.  **Reminder Service** detects the new entry in the DB and automatically schedules a notification job.
6.  **AI Brain** indexes the new med into long-term memory for future reasoning.
