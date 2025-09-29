# Contributing to Bean Bot

Thank you for your interest in contributing to Bean Bot! This document provides guidelines and information for contributors.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Create a virtual environment
4. Install dependencies: `pip install -r requirements.txt`
5. Create a `.env` file based on `env.example`
6. Make your changes
7. Test your changes
8. Submit a pull request

## Development Setup

### Prerequisites
- Python 3.8 or higher
- Discord bot token
- Google Cloud Project with Sheets API enabled

### Environment Setup
1. Copy `env.example` to `.env`
2. Fill in your Discord bot token and Google Sheets configuration
3. Place your Google credentials JSON file in the project root

## Code Style

- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and single-purpose
- Use type hints where appropriate

## Adding New Features

### Cogs
- Place new cogs in the `cogs/` directory
- Follow the existing cog structure
- Include proper error handling
- Add command descriptions and help text

### Commands
- Use both slash commands and traditional commands when appropriate
- Include permission checks
- Provide clear error messages
- Add confirmation messages for destructive actions

## Testing

- Test your changes thoroughly before submitting
- Test with different permission levels
- Test error conditions
- Verify slash commands work correctly

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Test thoroughly
4. Update documentation if needed
5. Submit a pull request with a clear description

## Reporting Issues

When reporting issues, please include:
- Description of the problem
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (Python version, OS, etc.)

## Questions?

Feel free to open an issue for questions or discussions about the project.
