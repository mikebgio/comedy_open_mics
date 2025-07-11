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
- Show creation and management by hosts through modal interfaces
- Recurring show templates with instance generation
- Event cancellation and rescheduling capabilities
- Calendar view with color-coded events based on user relationship
- Modal-based "View Upcoming Lineups" functionality

### Signup System
- Comedian signup for available time slots
- Lineup management and reordering
- Real-time availability tracking
- Signup deadlines and restrictions

### Email Integration
- AWS SES integration for email notifications
- Email verification for new accounts
- Event notifications and reminders

### Calendar Features
- Color-coded events: gray (available), green (signed up), red (owned)
- Compact legend for visual reference
- Modal-based event details and management

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

## Recent Changes (July 2025)

### Google Maps Address Autocomplete Implementation (July 11, 2025)
- ✅ Successfully implemented Google Maps Places API autocomplete functionality
- ✅ Fixed deprecated PlaceAutocompleteElement issues by using classic Autocomplete API
- ✅ Added proper dark theme styling for autocomplete dropdown suggestions
- ✅ Enhanced timezone detection with real coordinates from selected addresses
- ✅ Resolved form submission issues to properly capture autocomplete-selected addresses
- ✅ Added comprehensive debugging and error handling for Maps API integration
- ✅ Fixed database timeout issues in event creation by optimizing show instance generation
- ✅ Implemented efficient batch insertion for show instances (limited to 20 instances)
- ✅ Complete end-to-end functionality: address autocomplete → timezone detection → event creation

### Create Event Form Completion (July 11, 2025)
- ✅ Fixed all form validation issues allowing 0 as valid value for signup close timing
- ✅ Resolved missing required field error for deprecated signup_deadline_hours field
- ✅ Added proper hidden field handling for backward compatibility
- ✅ Enhanced session cookie configuration for better cross-tab authentication
- ✅ Confirmed working Google Maps autocomplete with timezone detection
- ✅ Full event creation workflow now functional with all timing controls
- ✅ Form successfully creates events with proper signup timing configurations
- ✅ Fixed modal form in host dashboard to include missing signup_deadline_hours field
- ✅ Updated JavaScript form submission to include all required API fields
- ✅ **CONFIRMED WORKING**: Both standalone create event page and host dashboard modal now fully functional

### Timezone and Address Management Enhancement
- Implemented intelligent timezone detection based on event addresses
- Added address autocomplete with location-based timezone mapping for US/Canada
- Enhanced event creation to store times in UTC while displaying in local timezone
- Added comprehensive timezone support for all North American time zones
- Fixed database constraints to allow guest performers (null comedian_id)
- Improved form validation with real-time timezone feedback

## Previous Changes (July 2025)

### Host Dashboard Overhaul
- Implemented modal-based event creation and editing
- Added change tracking with visual indicators (yellow highlighting)
- Replaced "View Lineup" with "View Upcoming Lineups" functionality
- Removed unnecessary Settings button for cleaner interface
- Fixed JavaScript conflicts and template errors

### Calendar Enhancement
- Added color-coded events based on user relationship
- Implemented compact legend below calendar
- Enhanced visual feedback for event ownership and participation

### Code Cleanup & CI/CD Enhancement
- Consolidated routes files: `routes_simple.py` → `routes.py`
- Removed backup files: `routes_old.py`, `models_backup.py`, `models_new.py`
- Cleaned up test files to single `test_integration.py`
- Removed migration files and intermediate artifacts
- Applied Black formatting and isort organization across entire codebase
- Enhanced GitHub Actions CI/CD pipeline with comprehensive linting and testing:
  - Integrated Black, isort, and flake8 checks in main test job
  - Added dedicated lint job with security scanning (bandit, safety)
  - Included build job with deployment artifact creation
  - Fixed build environment configuration with proper database URL
  - Added comprehensive error handling and environment validation
  - Resolved API endpoint test failures (403 response handling)
  - Added informative job summaries and workflow reliability improvements
  - Enhanced .gitignore with build artifacts and deployment file exclusions
  - Fixed Codecov action parameter from deprecated 'file' to 'files'

## Technical Architecture

The application is designed to be scalable and maintainable, with clear separation of concerns and comprehensive error handling throughout the system. The modal-based interface provides a modern user experience while maintaining server-side validation and security.