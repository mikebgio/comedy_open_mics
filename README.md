# Comedy Open Mic Manager

A comprehensive web application for managing comedy open mic events in the Boston area. Built with Flask and designed for both comedians and hosts.

## Features

- **User Management**: Registration and authentication for comedians and hosts
- **Event Creation**: Hosts can create and manage open mic events
- **Signup System**: Comedians can sign up for available time slots
- **Live Lineups**: Real-time display of performer lineups
- **Lineup Management**: Hosts can reorder and manage performer lists
- **Dual Roles**: Users can be both comedians and hosts

## Technology Stack

- **Backend**: Flask, SQLAlchemy, PostgreSQL
- **Frontend**: Bootstrap 5, Vanilla JavaScript
- **Authentication**: Flask-Login
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Testing**: pytest, pytest-flask, pytest-cov

## Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL
- Git

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd comedy-open-mic-manager
```

2. Install dependencies:
```bash
make install
# or manually:
pip install -e .
pip install -r requirements-dev.txt
```

3. Set up environment variables:
```bash
export DATABASE_URL="postgresql://username:password@localhost/comedy_db"
export SESSION_SECRET="your-secret-key"
```

4. Initialize the database:
```bash
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

5. Seed with test data (optional):
```bash
make seed
```

6. Run the application:
```bash
make run
# or
python main.py
```

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Generate coverage report
make coverage
```

### Test Structure

- `test_app.py` - Unit tests for core functionality
- `tests/test_integration.py` - Integration tests for complete workflows
- `pytest.ini` - pytest configuration

## CI/CD Pipeline

The project includes a comprehensive GitHub Actions CI/CD pipeline:

### Pipeline Features
- **Automated Testing**: Runs unit and integration tests
- **Code Quality**: Linting with flake8, formatting with black
- **Security Scanning**: bandit and safety checks
- **Coverage Reports**: Code coverage analysis
- **Build Artifacts**: Creates deployment-ready packages

### GitHub Actions Workflows
- `.github/workflows/ci.yml` - Main CI pipeline
- Runs on push to main/develop branches
- Parallel jobs for testing, linting, and building

### Local Development Commands

```bash
# Development helpers
make help           # Show all available commands
make format         # Format code with black and isort
make lint          # Run code linting
make security      # Run security scans
make clean         # Clean temporary files
make db-reset      # Reset and reseed database
```

## Database Schema

### Tables
- **users**: User accounts (comedians/hosts)
- **events**: Open mic events
- **signups**: Comedian event registrations
- **event_cancellations**: Cancelled event dates

### Key Relationships
- Users can be both comedians and hosts
- Events belong to host users
- Signups link comedians to specific event dates
- Cancellations override normal event schedules

## API Endpoints

### Public Routes
- `GET /` - Homepage with upcoming events
- `GET /lineup/<event_id>` - Live lineup display
- `GET /event/<event_id>` - Event information

### Authentication Routes
- `POST /register` - User registration
- `POST /login` - User login
- `GET /logout` - User logout

### Comedian Routes
- `GET /dashboard` - Comedian dashboard
- `POST /comedian/signup/<event_id>` - Sign up for event

### Host Routes
- `GET /host/dashboard` - Host dashboard
- `POST /host/create_event` - Create new event
- `GET /host/manage_lineup/<event_id>` - Manage lineup
- `POST /host/reorder_lineup/<event_id>` - Reorder performers
- `POST /host/cancel_event/<event_id>` - Cancel event date

## Deployment

The application is designed for deployment on cloud platforms:

### Environment Variables Required
- `DATABASE_URL` - PostgreSQL connection string
- `SESSION_SECRET` - Flask session secret key

### Production Considerations
- Use a production WSGI server (gunicorn included)
- Set up proper database backups
- Configure SSL/TLS certificates
- Set up monitoring and logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Run linting: `make lint`
6. Submit a pull request

The CI pipeline will automatically run all tests and quality checks on your pull request.

## License

Built for the Boston Comedy Community © 2025