# Comedy Open Mic Manager

## Overview

Comedy Open Mic Manager is a comprehensive web application for managing comedy open mic events in the Boston area. Built with Flask, it serves both comedians and hosts with features for event management, signup systems, and live lineups.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

The application follows a classic three-tier architecture:

### Backend Architecture
- **Framework**: Flask web framework with SQLAlchemy ORM
- **Database**: PostgreSQL for production (SQLite for testing)
- **Authentication**: Flask-Login for session management
- **Forms**: Flask-WTF with WTForms for form handling and validation

### Frontend Architecture
- **UI Framework**: Bootstrap 5 with dark theme
- **JavaScript**: Vanilla JavaScript for interactive features
- **Icons**: Font Awesome for UI icons
- **Templates**: Jinja2 templating engine

### Database Design
The application uses a sophisticated data model with the following key entities:

- **User**: Stores user accounts with roles (comedian/host)
- **Show**: Represents recurring comedy shows (e.g., "Monday Night Comedy")
- **ShowInstance**: Specific occurrences of shows on particular dates
- **Signup**: Links comedians to specific show instances
- **ShowRunner/ShowHost**: Role-based associations for show management

## Key Components

### User Management
- Registration and login system with email verification
- Role-based access (comedians can sign up, hosts can manage events)
- Password hashing with Werkzeug security

### Event Management
- Show creation and management by hosts
- Recurring show templates with instance generation
- Event cancellation and rescheduling capabilities
- Calendar view for event visualization

### Signup System
- Comedian signup for available time slots
- Lineup management and reordering
- Real-time availability tracking
- Signup deadlines and restrictions

### Email Integration
- AWS SES integration for email notifications
- Email verification for new accounts
- Event notifications and reminders

## Data Flow

1. **User Registration**: Users register → Email verification → Account activation
2. **Show Creation**: Hosts create shows → Show instances generated → Available for signups
3. **Signup Process**: Comedians browse events → Sign up for slots → Confirmation
4. **Event Management**: Hosts manage lineups → Reorder performers → Handle cancellations
5. **Live Updates**: Real-time lineup display → Calendar integration → Notifications

## External Dependencies

### Production Services
- **AWS SES**: Email delivery service for notifications
- **PostgreSQL**: Primary database for data persistence
- **Gunicorn**: WSGI server for production deployment

### Development Tools
- **pytest**: Testing framework with coverage reporting
- **Black**: Code formatting and style enforcement
- **isort**: Import sorting and organization
- **flake8**: Code linting and quality checks

### Frontend Libraries
- **Bootstrap 5**: CSS framework for responsive design
- **Font Awesome**: Icon library for UI elements
- **JavaScript**: Native browser APIs for interactivity

## Deployment Strategy

### Environment Configuration
- Environment variables for sensitive data (DATABASE_URL, SESSION_SECRET)
- AWS credentials for email service integration
- Separate configurations for development/testing/production

### Database Management
- SQLAlchemy migrations for schema changes
- Connection pooling for performance
- Backup and recovery procedures

### Testing Strategy
- Unit tests for core functionality
- Integration tests for user workflows
- Coverage reporting for quality assurance
- CI/CD pipeline compatibility

The application is designed to be scalable and maintainable, with clear separation of concerns and comprehensive error handling throughout the system.