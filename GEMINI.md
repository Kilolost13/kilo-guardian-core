# Project Overview: Kilo - A Personal Assistant System

This project, named Kilo, is a personal assistant system built with a microservices architecture. It integrates various functionalities to help users manage their daily lives, health, finances, and interactions with their environment. The system comprises a set of Python-based backend microservices, a central AI Brain, and a React-based frontend.

## Technologies Used:
*   **Backend:** Python 3, FastAPI, uvicorn, httpx, Pydantic
*   **Frontend:** React, TypeScript, npm (or yarn)
*   **Containerization:** Docker, Docker Compose

## Architecture:

The project follows a microservices architecture orchestrated by Docker Compose.

1.  **Microservices:**
    *   **AI Brain (`ai_brain`):** The central intelligence service. It handles chat interactions, integrates with a "Library of Truth" for information retrieval, ingests data from other services (meds, finance, camera, habits), manages reminders, and provides analytics/feedback.
    *   **Camera (`cam`):** Likely handles camera-related functionalities, potentially for observations or posture analysis, feeding data to the AI Brain.
    *   **Financial (`financial`):** Manages financial data and events, with data being ingested by the AI Brain for potential budgeting or suggestions.
    *   **Habits (`habits`):** Manages user habits and their completion, providing data for analytics and feedback via the AI Brain.
    *   **Library of Truth (`library_of_truth`):** A service for storing and searching information, used by the AI Brain to answer user queries.
    *   **Meds (`meds`):** Manages medication schedules and dosages, with data ingested by the AI Brain to set proactive reminders.
    *   **Reminder (`reminder`):** Manages general reminders for the user.
    *   **Gateway (`gateway`):** An API Gateway that acts as a single entry point for all client requests, routing them to the appropriate backend microservice.

2.  **Frontend (`kilo-react-frontend`):** A React application built with TypeScript, providing a web-based user interface to interact with the backend services via the API Gateway. It features a modular structure, dynamically rendering different components for Dashboard, Camera, Financial, Habits, Meds, and Reminders.

## Building and Running:

The entire application can be built and run using Docker Compose.

### Prerequisites:
*   Docker and Docker Compose installed.
*   Node.js and npm (or yarn) if you plan to develop the frontend directly without Docker.

### 1. Build and Run with Docker Compose:

Navigate to the `microservice` directory and run:

```bash
docker-compose up --build
```

This command will:
*   Build Docker images for each service (backend microservices and frontend).
*   Start all services as defined in `docker-compose.yml`.
*   The API Gateway will be accessible on port `8001`.
*   The Frontend will be accessible on port `3000`.

### 2. Individual Service Information:

Each microservice in the `microservice/` directory (e.g., `ai_brain`, `cam`, `gateway`, etc.) has its own `Dockerfile` for building. Python services typically use `uvicorn` to run their FastAPI applications.

The frontend is a standard Create React App project. You can build it separately by navigating to `microservice/frontend/kilo-react-frontend` and running:

```bash
npm install
npm run build
```

Or to run it in development mode:

```bash
npm start
```

## Development Conventions:

*   **Backend:** Python 3, FastAPI for building RESTful APIs. `Pydantic` models are used for data validation and serialization.
*   **Frontend:** React with TypeScript for component-based UI development. `react-scripts` is used for development tooling.
*   **Code Style:** Adherence to standard Python and JavaScript/TypeScript best practices is expected.
*   **Environment Variables:** Service URLs and other configurations are managed via environment variables, especially in `docker-compose.yml` and within individual service code (e.g., `os.getenv`).
*   **Testing:** Each Python service directory contains `test_integration.py` for integration tests. The frontend uses `@testing-library/react` for testing.
