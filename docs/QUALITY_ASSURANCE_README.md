# AI Memory Assistant - Quality Assurance Tools

This directory contains air-gapped compatible quality assurance tools for the AI Memory Assistant system. All tools work entirely offline without external dependencies.

## 🛠️ Available Tools

### 1. Comprehensive Test Suite (`test_suite.py`)
- **Purpose**: Runs unit, integration, performance, and security tests
- **Usage**: `python3 microservice/test_suite.py`
- **Features**:
  - Unit tests for all models and utilities
  - Integration tests for API endpoints
  - Performance benchmarks
  - Security validation tests
  - Mock data generation for testing

### 2. Offline Analytics Dashboard (`analytics_dashboard.py`)
- **Purpose**: Generates comprehensive analytics and insights from your data
- **Usage**: `python3 microservice/analytics_dashboard.py`
- **Features**:
  - Memory and conversation analytics
  - Usage pattern analysis
  - Content theme detection
  - Personalized insights and recommendations
  - Data visualizations (charts and graphs)
  - Engagement scoring

### 3. Automated Documentation Generator (`generate_docs.py`)
- **Purpose**: Creates comprehensive documentation from codebase analysis
- **Usage**: `python3 microservice/generate_docs.py`
- **Features**:
  - API documentation
  - Model documentation
  - Deployment guides
  - User guides
  - Developer guides
  - Troubleshooting guides

### 4. Local CI/CD Pipeline (`local_ci.sh`)
- **Purpose**: Runs automated quality checks and builds
- **Usage**: `./microservice/local_ci.sh`
- **Features**:
  - Dependency validation
  - Code quality checks
  - Test execution
  - Build artifact creation
  - Security scanning

### 5. Quality Assurance Runner (`run_quality_checks.sh`)
- **Purpose**: Orchestrates all quality tools in sequence
- **Usage**: `./run_quality_checks.sh [command]`
- **Commands**:
  - `all` - Run all quality checks (default)
  - `test` - Run test suite only
  - `analytics` - Generate analytics only
  - `docs` - Generate documentation only
  - `ci` - Run CI/CD pipeline only
  - `health` - Check system health only

## 🚀 Quick Start

### Run All Quality Checks
```bash
./run_quality_checks.sh
```

### Run Individual Tools
```bash
# Run tests only
./run_quality_checks.sh test

# Generate analytics only
./run_quality_checks.sh analytics

# Generate documentation only
./run_quality_checks.sh docs
```

### Manual Execution
```bash
# Test suite
python3 microservice/test_suite.py

# Analytics dashboard
python3 microservice/analytics_dashboard.py

# Documentation generator
python3 microservice/generate_docs.py

# Local CI/CD
./microservice/local_ci.sh
```

## 📊 Generated Outputs

After running the quality tools, you'll find these files in your project root:

- `analytics_report.json` - Raw analytics data
- `analytics_report.md` - Human-readable analytics report
- `docs/` - Complete documentation directory
- `test_results/` - Test execution results (if applicable)
- `build_artifacts/` - Build outputs from CI/CD (if applicable)

## 🔧 System Requirements

- Python 3.8+
- Bash shell
- SQLite/PostgreSQL (for database operations)
- Docker (optional, for containerized testing)
- Matplotlib (optional, for analytics visualizations)

## 📈 Analytics Dashboard Features

The analytics dashboard provides:

### Key Metrics
- Total memories and conversations
- Activity patterns and trends
- Content analysis and themes
- User engagement scoring
- Peak usage times

### Insights & Recommendations
- Personalized improvement suggestions
- Usage pattern analysis
- Content diversity recommendations
- Health and wellness insights

### Visualizations
- Memory type distribution charts
- Activity timeline graphs
- Usage pattern visualizations

## 🧪 Testing Framework

The test suite includes:

### Unit Tests
- Model validation
- Utility function testing
- Business logic verification

### Integration Tests
- API endpoint testing
- Database operations
- Service interactions

### Performance Tests
- Response time benchmarks
- Memory usage monitoring
- Load testing simulations

### Security Tests
- Input validation
- Authentication checks
- Data sanitization verification

## 📚 Documentation Generator

Creates comprehensive documentation including:

- **API Reference**: All endpoints with parameters and responses
- **Model Documentation**: Database schemas and relationships
- **Deployment Guide**: Step-by-step setup instructions
- **User Guide**: Feature explanations and usage examples
- **Developer Guide**: Code structure and contribution guidelines
- **Troubleshooting**: Common issues and solutions

## 🔄 CI/CD Pipeline

The local CI/CD pipeline performs:

- **Dependency Checks**: Validate all required packages
- **Code Quality**: Lint and format validation
- **Testing**: Execute full test suite
- **Security Scanning**: Check for vulnerabilities
- **Build Process**: Create deployable artifacts
- **Documentation**: Generate updated docs

## 🔒 Air-Gapped Compatibility

All tools are designed to work completely offline:

- ✅ No external API calls
- ✅ No cloud service dependencies
- ✅ Local data analysis only
- ✅ Self-contained testing
- ✅ Offline documentation generation

## 🎯 Best Practices

1. **Run Daily**: Execute `./run_quality_checks.sh` daily for ongoing monitoring
2. **Review Analytics**: Check `analytics_report.md` weekly for insights
3. **Update Documentation**: Regenerate docs after significant changes
4. **Monitor Tests**: Ensure all tests pass before deployments
5. **Backup Reports**: Keep analytics reports for trend analysis

## 🆘 Troubleshooting

### Common Issues

**Tests Failing**
- Check database connectivity
- Ensure all dependencies are installed
- Review error messages for specific failures

**Analytics Not Generating**
- Verify database has data
- Check file permissions for output directories
- Ensure matplotlib is installed for visualizations

**Documentation Errors**
- Check code syntax and imports
- Verify all required modules are available
- Review error logs for specific issues

**CI/CD Pipeline Issues**
- Ensure all required tools are installed
- Check file permissions
- Verify Docker is running (if using containers)

### Getting Help

1. Check the generated `troubleshooting.md` in the docs directory
2. Review test output for specific error messages
3. Check system logs for underlying issues
4. Run individual tools to isolate problems

## 📝 Customization

### Adding New Tests
Edit `test_suite.py` to add new test cases following the existing patterns.

### Custom Analytics
Modify `analytics_dashboard.py` to add new metrics or insights.

### Documentation Templates
Update `generate_docs.py` to customize documentation output formats.

### CI/CD Stages
Modify `local_ci.sh` to add new validation steps or build processes.

---

*These tools ensure your AI Memory Assistant remains reliable, performant, and well-documented while operating completely offline.*