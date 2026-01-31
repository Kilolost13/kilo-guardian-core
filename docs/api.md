# AI Memory Assistant - API Documentation

Generated on: 2025-12-24 08:01:57

## Overview

The AI Memory Assistant provides a comprehensive REST API for managing memories, conversations, medications, reminders, and user data.

## Base URL
```
http://localhost:8000
```

## Authentication

All API endpoints require authentication via JWT token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

## API Endpoints

### /Venv/Libthon3/11/Site-Packages/Fastapi/Datastructures

#### POST /files/
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/files/
```

#### POST /uploadfile/
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/uploadfile/
```

### /Venv/Libthon3/11/Site-Packages/Fastapi/Applications

#### GET /users/
**Description:** 

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/users/
```

#### GET /items/
**Description:** 

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/items/
```

#### GET /items/
**Description:** 

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/items/
```

#### GET /items/
**Description:** 

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/items/
```

#### PUT /items/{item_id}
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/items/{item_id}
```

#### POST /items/
**Description:** 

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/items/
```

#### DELETE /items/{item_id}
**Description:** No description available

#### PATCH /items/
**Description:** 

### /Venv/Libthon3/11/Site-Packages/Fastapi/Param_Functions

#### GET /items/{item_id}
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/items/{item_id}
```

#### GET /items/
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/items/
```

#### GET /users/me/items/
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/users/me/items/
```

### /Venv/Libthon3/11/Site-Packages/Fastapi/Background

#### POST /send-notification/{email}
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/send-notification/{email}
```

### /Venv/Libthon3/11/Site-Packages/Fastapi/Exceptions

#### GET /items/{item_id}
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/items/{item_id}
```

### /Venv/Libthon3/11/Site-Packages/Fastapi/Security/Oauth2

#### POST /login
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/login
```

#### POST /login
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/login
```

### /Venv/Libthon3/11/Site-Packages/Fastapi/Security/Http

#### GET /users/me
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/users/me
```

#### GET /users/me
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/users/me
```

#### GET /users/me
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/users/me
```

### /Venv/Libthon3/11/Site-Packages/Fastapi/Security/Api_Key

#### GET /items/
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/items/
```

#### GET /items/
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/items/
```

#### GET /items/
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/items/
```

### Microservice/Meds/Main

#### GET /status
**Description:** Health check endpoint

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/status
```

#### GET /
**Description:** startup handled by lifespan

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/
```

#### POST /extract
**Description:** Convert back to PIL Image

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/extract
```

#### PUT /{med_id}
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/{med_id}
```

#### POST /add
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/add
```

#### DELETE /{med_id}
**Description:** No description available

### Microservice/Habits/Main

#### GET /status
**Description:** Health check endpoint

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/status
```

#### GET /
**Description:** startup handled by lifespan

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/
```

#### POST /
**Description:** startup handled by lifespan

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/
```

#### PUT /{habit_id}
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/{habit_id}
```

#### DELETE /{habit_id}
**Description:** No description available

#### POST /complete/{habit_id}
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/complete/{habit_id}
```

### Microservice/Reminder/Main

#### GET /status
**Description:** header provided but validation failed

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/status
```

#### GET /upcoming
**Description:** startup handled by lifespan; legacy on_event startup block removed

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/upcoming
```

#### GET /
**Description:** Attempt callback when a callback URL is configured (best-effort)

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/
```

#### GET /presets
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/presets
```

#### POST /presets
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/presets
```

#### PATCH /presets/{preset_id}
**Description:** No description available

#### POST /presets/{preset_id}/create
**Description:** fallback

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/presets/{preset_id}/create
```

#### GET /suggestions
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/suggestions
```

#### POST /
**Description:** Attempt callback when a callback URL is configured (best-effort)

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/
```

#### PUT /{reminder_id}
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/{reminder_id}
```

#### DELETE /{reminder_id}
**Description:** No description available

#### POST /{reminder_id}/mark_sent
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/{reminder_id}/mark_sent
```

#### POST /{reminder_id}/snooze
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/{reminder_id}/snooze
```

#### POST /{reminder_id}/trigger
**Description:** reschedule

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/{reminder_id}/trigger
```

### Microservice/Cam/Main

#### GET /status
**Description:** Model/or native deps not available; run in degraded mode.

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/status
```

#### GET /stream
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/stream
```

#### POST /ocr
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ocr
```

#### POST /analyze_pose
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/analyze_pose
```

#### POST /register_face
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/register_face
```

#### POST /recognize_face
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/recognize_face
```

#### POST /analyze_basket
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/analyze_basket
```

#### POST /detect_activity
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/detect_activity
```

#### POST /detect_objects
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/detect_objects
```

#### POST /cameras/register
**Description:** Get information about a registered camera

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/cameras/register
```

#### GET /cameras
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/cameras
```

#### POST /cameras/{camera_id}/activate
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/cameras/{camera_id}/activate
```

#### POST /cameras/{camera_id}/deactivate
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/cameras/{camera_id}/deactivate
```

#### POST /performance_stats
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/performance_stats
```

#### GET /performance_stats
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/performance_stats
```

#### POST /analyze_scene
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/analyze_scene
```

#### POST /compare_pose
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/compare_pose
```

#### POST /frame
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/frame
```

#### POST /ptz/start_tracking
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ptz/start_tracking
```

#### POST /ptz/stop_tracking
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ptz/stop_tracking
```

#### GET /ptz/status
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/ptz/status
```

#### POST /ptz/set_position
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ptz/set_position
```

#### POST /ptz/calibrate
**Description:** Manually set PTZ position

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ptz/calibrate
```

#### POST /ptz/connect
**Description:** Calibrate PTZ to center position

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ptz/connect
```

#### POST /ptz/disconnect
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ptz/disconnect
```

#### GET /ptz/hardware_status
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/ptz/hardware_status
```

#### POST /ptz/set_limits
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ptz/set_limits
```

#### POST /ptz/emergency_stop
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ptz/emergency_stop
```

#### GET /ptz/tracking_data
**Description:** Emergency stop all PTZ movement

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/ptz/tracking_data
```

### Microservice/Library_Of_Truth/Main

#### GET /status
**Description:** Health check endpoint

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/status
```

#### GET /books
**Description:** startup handled by lifespan

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/books
```

#### GET /books/{filename}
**Description:** Download a specific PDF

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/books/{filename}
```

#### POST /parse_books
**Description:** Endpoint to trigger parsing (admin only)

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/parse_books
```

#### GET /search
**Description:** --- Search Endpoint ---

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/search
```

#### POST /
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/
```

### Microservice/Ml_Engine/Main

#### GET /status
**Description:** Health check

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/status
```

#### POST /predict/habit_completion
**Description:** --- Prediction Endpoints ---

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/predict/habit_completion
```

#### POST /predict/reminder_timing
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/predict/reminder_timing
```

#### GET /insights/patterns
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/insights/patterns
```

#### POST /train/habits
**Description:** --- Training Endpoints ---

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/train/habits
```

#### POST /train/habit_completion
**Description:** 

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/train/habit_completion
```

#### GET /stats
**Description:** --- Stats Endpoint ---

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/stats
```

### Microservice/Financial/Main

#### GET /status
**Description:** Health check endpoint

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/status
```

#### GET /
**Description:** shutdown handled by lifespan

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/
```

#### GET /summary
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/summary
```

#### GET /shopping_habits
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/shopping_habits
```

#### GET /spending_trends
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/spending_trends
```

#### POST /
**Description:** shutdown handled by lifespan

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/
```

#### PUT /{transaction_id}
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/{transaction_id}
```

#### DELETE /{transaction_id}
**Description:** No description available

#### GET /budgets
**Description:** Budget endpoints

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/budgets
```

#### POST /budgets
**Description:** Budget endpoints

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/budgets
```

#### PUT /budgets/{budget_id}
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/budgets/{budget_id}
```

#### DELETE /budgets/{budget_id}
**Description:** No description available

#### GET /goals
**Description:** Goal endpoints

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/goals
```

#### POST /goals
**Description:** Goal endpoints

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/goals
```

#### PUT /goals/{goal_id}
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/goals/{goal_id}
```

#### DELETE /goals/{goal_id}
**Description:** No description available

#### POST /receipt
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/receipt
```

#### POST /admin/recalculate_categories
**Description:** model_dump()/dict() behavior can vary across SQLModel versions; serialize explicitly

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/admin/recalculate_categories
```

#### GET /admin/migration_status
**Description:** schedule background job

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/admin/migration_status
```

### Microservice/Financial/Gateway/Main

#### POST /admin/tokens
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/admin/tokens
```

#### GET /admin/tokens
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/admin/tokens
```

#### POST /admin/tokens/{token_id}/revoke
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/admin/tokens/{token_id}/revoke
```

#### POST /admin/validate
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/admin/validate
```

#### GET /status
**Description:** Health check endpoint (alias for /health)

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/status
```

#### GET /health
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/health
```

### Microservice/Microservice/Meds/Main

#### GET /status
**Description:** Health check endpoint

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/status
```

#### GET /
**Description:** startup handled by lifespan

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/
```

#### POST /extract
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/extract
```

#### POST /add
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/add
```

### Microservice/Microservice/Habits/Main

#### GET /status
**Description:** Health check endpoint

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/status
```

#### GET /
**Description:** startup handled by lifespan

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/
```

#### POST /
**Description:** startup handled by lifespan

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/
```

#### POST /complete/{habit_id}
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/complete/{habit_id}
```

### Microservice/Microservice/Reminder/Main

#### GET /status
**Description:** Health check endpoint

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/status
```

#### GET /upcoming
**Description:** startup handled by lifespan; legacy on_event startup block removed

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/upcoming
```

#### GET /
**Description:** send callback to ai_brain if configured; add simple retry

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/
```

#### GET /presets
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/presets
```

#### POST /presets
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/presets
```

#### PATCH /presets/{preset_id}
**Description:** No description available

#### POST /presets/{preset_id}/create
**Description:** fallback

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/presets/{preset_id}/create
```

#### GET /suggestions
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/suggestions
```

#### POST /
**Description:** send callback to ai_brain if configured; add simple retry

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/
```

#### PUT /{reminder_id}
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/{reminder_id}
```

#### DELETE /{reminder_id}
**Description:** No description available

#### POST /{reminder_id}/mark_sent
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/{reminder_id}/mark_sent
```

#### POST /{reminder_id}/snooze
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/{reminder_id}/snooze
```

#### POST /{reminder_id}/trigger
**Description:** reschedule

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/{reminder_id}/trigger
```

### Microservice/Microservice/Library_Of_Truth/Main

#### GET /status
**Description:** Health check endpoint

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/status
```

#### GET /books
**Description:** startup handled by lifespan

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/books
```

#### GET /books/{filename}
**Description:** Download a specific PDF

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/books/{filename}
```

#### POST /parse_books
**Description:** Endpoint to trigger parsing (admin only)

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/parse_books
```

#### GET /search
**Description:** --- Search Endpoint ---

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/search
```

#### POST /
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/
```

### Microservice/Microservice/Financial/Main

#### GET /status
**Description:** Health check endpoint

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/status
```

#### GET /
**Description:** shutdown handled by lifespan

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/
```

#### GET /summary
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/summary
```

### Microservice/Gateway/Main

#### POST /admin/tokens
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/admin/tokens
```

#### GET /admin/tokens
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/admin/tokens
```

#### POST /admin/tokens/{token_id}/revoke
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/admin/tokens/{token_id}/revoke
```

#### POST /admin/validate
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/admin/validate
```

#### GET /status
**Description:** Health check endpoint (alias for /health)

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/status
```

#### GET /health
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/health
```

### Microservice/Ai_Brain/Main

#### GET /status
**Description:** Health check endpoint

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/status
```

#### POST /chat
**Description:** JSON chat endpoint with RAG (Retrieval Augmented Generation)

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/chat
```

#### POST /chat/voice
**Description:** Form/multipart chat endpoint for voice or form-based input

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/chat/voice
```

#### POST /ingest/meds
**Description:** mount background tasks to run after response

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ingest/meds
```

#### POST /ingest/finance
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ingest/finance
```

#### POST /ingest/receipt
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ingest/receipt
```

#### POST /ingest/cam
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ingest/cam
```

#### POST /ingest/habit
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ingest/habit
```

#### POST /ingest/habit_completion
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ingest/habit_completion
```

#### POST /ingest/budget
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ingest/budget
```

#### POST /ingest/goal
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ingest/goal
```

#### POST /ingest/cam_activity
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/ingest/cam_activity
```

#### POST /reminder/ack
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/reminder/ack
```

#### POST /voice/activate
**Description:** --- Voice Stubs ---

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/voice/activate
```

#### POST /voice/speak
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/voice/speak
```

#### GET /analytics/habits
**Description:** --- Analytics and Feedback Endpoints ---

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/analytics/habits
```

#### GET /feedback/habits
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/feedback/habits
```

#### GET /tts/{fname}
**Description:** schedule background write

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/tts/{fname}
```

#### POST /analyze/prescription
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/analyze/prescription
```

#### GET /api/v1/scalability/status
**Description:** Orchestration router is mounted above if available (guarded)

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/api/v1/scalability/status
```

#### POST /api/v1/async/embeddings
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/api/v1/async/embeddings
```

#### POST /api/v1/async/indexing
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/api/v1/async/indexing
```

#### POST /api/v1/async/consolidation
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/api/v1/async/consolidation
```

#### GET /api/v1/predictive/insights
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/api/v1/predictive/insights
```

#### GET /api/v1/knowledge/graph/stats
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/api/v1/knowledge/graph/stats
```

#### POST /api/v1/knowledge/graph/build
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/api/v1/knowledge/graph/build
```

#### GET /api/v1/knowledge/reason/{entity_id}
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/api/v1/knowledge/reason/{entity_id}
```

#### POST /api/v1/conversation/start
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/api/v1/conversation/start
```

#### POST /api/v1/conversation/{conversation_id}/turn
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/api/v1/conversation/{conversation_id}/turn
```

#### POST /api/v1/conversation/{conversation_id}/goals
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/api/v1/conversation/{conversation_id}/goals
```

#### GET /api/v1/conversation/{conversation_id}/context
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/api/v1/conversation/{conversation_id}/context
```

#### GET /api/v1/conversation/{conversation_id}/suggestions
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/api/v1/conversation/{conversation_id}/suggestions
```

#### GET /api/v1/user/{user_id}/insights
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/api/v1/user/{user_id}/insights
```

#### POST /api/v1/goals/suggest
**Description:** No description available

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/api/v1/goals/suggest
```

#### GET /api/v1/goals/templates
**Description:** No description available

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/api/v1/goals/templates
```

### Microservice/Voice/Main

#### GET /status
**Description:** Health check

```bash
curl -H 'Authorization: Bearer <token>' \
     http://localhost:8000/status
```

#### POST /stt
**Description:** Speech-to-Text (STT)

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/stt
```

#### POST /tts
**Description:** Text-to-Speech (TTS)

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/tts
```

#### POST /vad
**Description:** Voice activity detection (future feature)

```bash
curl -X {route['method']} \
     -H 'Authorization: Bearer <token>' \
     -H 'Content-Type: application/json' \
     -d '{...}' \
     http://localhost:8000/vad
```

