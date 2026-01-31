# AI Memory Assistant - Developer Guide

Generated on: 2025-12-24 08:01:57

## Overview

This guide helps developers understand, modify, and extend the AI Memory Assistant.

## Architecture

### Backend Architecture
```
ai_brain/
├── main.py              # FastAPI application entry point
├── db.py                # Database connection and session management
├── models.py            # SQLAlchemy data models
├── orchestrator.py      # Main business logic coordinator
├── memory_search.py     # Memory retrieval and search
├── rag.py              # Retrieval-Augmented Generation
├── embeddings.py       # Text embeddings and vector operations
├── encryption.py       # Data encryption utilities
└── startup_checks.py   # Application startup validation
```

### Frontend Architecture
```
front end/kilo-react-frontend/
├── src/
│   ├── components/      # Reusable React components
│   ├── pages/          # Page components
│   ├── services/       # API service layer
│   ├── types/          # TypeScript type definitions
│   └── utils/          # Utility functions
├── public/             # Static assets
└── package.json       # Dependencies and scripts
```

## Development Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- PostgreSQL 12+
- Git

### Backend Development
```bash
# Clone repository
git clone <repository-url>
cd ai-memory-assistant

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup database
createdb ai_memory_db

# Run migrations
alembic upgrade head

# Start development server
python3 ai_brain/main.py
```

### Frontend Development
```bash
cd front\ end/kilo-react-frontend

# Install dependencies
npm install

# Start development server
npm start
```

## Code Organization

### Backend Modules

#### Core Modules
- **main.py**: FastAPI application with route definitions
- **db.py**: Database connection pooling and session management
- **models.py**: SQLAlchemy models with relationships

#### Business Logic
- **orchestrator.py**: Coordinates AI responses and memory operations
- **memory_search.py**: Implements vector search and retrieval
- **rag.py**: Handles retrieval-augmented generation
- **embeddings.py**: Text embedding generation and management

#### Utilities
- **encryption.py**: Data encryption/decryption functions
- **startup_checks.py**: Validates system requirements on startup

### Frontend Structure

#### Components
- **shared/**: Reusable UI components (Card, Button, etc.)
- **KnowledgeGraphVisualization.tsx**: Interactive knowledge graph
- **ProgressTracker.tsx**: Progress visualization and tracking
- **VoiceInteraction.tsx**: Voice input and processing

#### Pages
- **EnhancedDashboard.tsx**: Main dashboard with real-time features
- **KnowledgeGraph.tsx**: Knowledge graph exploration page
- **Progress.tsx**: Goal and progress management

## API Design

### RESTful Endpoints

#### Memory Management
```
GET    /memory/          # List memories
POST   /memory/          # Create memory
GET    /memory/{id}     # Get specific memory
PUT    /memory/{id}     # Update memory
DELETE /memory/{id}     # Delete memory
GET    /memory/search/   # Search memories
```

#### Conversation Management
```
GET    /conversation/    # List conversations
POST   /conversation/    # Create conversation
GET    /conversation/{id} # Get conversation
POST   /conversation/{id}/message # Add message
```

#### Medication Management
```
GET    /medications/     # List medications
POST   /medications/     # Add medication
PUT    /medications/{id} # Update medication
DELETE /medications/{id} # Delete medication
```

### Authentication
```python
# JWT token required for protected endpoints
headers = {
    "Authorization": f"Bearer {jwt_token}"
}
```

## Database Schema

### Core Tables
- **memory**: Stores user memories with embeddings
- **conversation**: Chat conversations with AI
- **medication**: Medication tracking and schedules
- **reminder**: User reminders and notifications
- **user**: User accounts and authentication

### Indexes
- Full-text search index on memory content
- Vector index on memory embeddings (if using pgvector)
- Date indexes on timestamp columns
- Foreign key indexes for relationships

## Testing Strategy

### Unit Tests
```python
# Example unit test
def test_memory_creation():
    memory = Memory(
        content="Test content",
        memory_type="conversation",
        importance=5
    )
    assert memory.content == "Test content"
```

### Integration Tests
```python
# Example integration test
def test_memory_api(client):
    response = client.post("/memory/", json={
        "content": "Test memory",
        "memory_type": "conversation"
    })
    assert response.status_code == 200
```

### Running Tests
```bash
# Run all tests
python3 test_suite.py

# Run unit tests only
python3 -m pytest tests/unit_tests.py

# Run with coverage
python3 -m pytest --cov=ai_brain tests/
```

## Adding New Features

### Backend Feature Development
1. **Define Data Model**: Add to `models.py`
2. **Create Database Migration**: Use Alembic
3. **Add Business Logic**: Implement in appropriate module
4. **Add API Endpoint**: Add route in `main.py`
5. **Add Tests**: Create unit and integration tests
6. **Update Documentation**: Update API docs

### Frontend Feature Development
1. **Design Component**: Create in `components/`
2. **Add State Management**: Use React hooks
3. **Add API Integration**: Use service layer
4. **Add Routing**: Update `App.tsx`
5. **Add Styling**: Use Tailwind CSS
6. **Add Tests**: Create component tests

## Performance Optimization

### Database Optimization
- Use database indexes for frequent queries
- Implement query result caching
- Use connection pooling
- Optimize complex queries

### Application Optimization
- Implement Redis caching for API responses
- Use async/await for I/O operations
- Optimize bundle size for frontend
- Implement lazy loading for components

### Monitoring
- Add performance metrics
- Monitor memory usage
- Track response times
- Log slow queries

## Security Best Practices

### Input Validation
```python
from pydantic import BaseModel, validator

class MemoryCreate(BaseModel):
    content: str
    memory_type: str

    @validator('memory_type')
    def validate_memory_type(cls, v):
        allowed_types = ['conversation', 'medication', 'habit']
        if v not in allowed_types:
            raise ValueError(f'Memory type must be one of: {allowed_types}')
        return v
```

### Authentication & Authorization
- Use JWT tokens with expiration
- Implement role-based access control
- Validate all user inputs
- Use parameterized queries

### Data Protection
- Encrypt sensitive data at rest
- Use HTTPS in production
- Implement proper session management
- Regular security audits

## Deployment

### Local Deployment
```bash
# Run CI/CD pipeline
./local_ci.sh

# Start services
docker-compose up -d
```

### Production Deployment
```bash
# Build production images
docker build -t ai-memory:latest .

# Deploy with docker-compose
docker-compose -f docker-compose.prod.yml up -d
```

## Contributing

### Code Standards
- Follow PEP 8 for Python code
- Use TypeScript for frontend code
- Write comprehensive tests
- Add documentation for new features

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/new-feature
```

### Pull Request Process
1. Ensure all tests pass
2. Update documentation
3. Get code review approval
4. Merge to main branch

## Troubleshooting Development Issues

### Common Backend Issues
- **Import Errors**: Check Python path and virtual environment
- **Database Errors**: Verify connection string and migrations
- **API Errors**: Check request/response format

### Common Frontend Issues
- **Build Errors**: Clear node_modules and reinstall
- **Runtime Errors**: Check browser console for errors
- **API Connection**: Verify backend is running and CORS is configured

### Debug Tools
- **Backend**: Use `pdb` or `ipdb` for debugging
- **Frontend**: Use React DevTools and browser debugger
- **Database**: Use pgAdmin or psql for database inspection

---

*This guide is continuously updated. Check back regularly for new information!*
