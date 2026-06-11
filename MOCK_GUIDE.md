# Mock API System Guide

This project includes a production-grade Mock API system that simulates the backend behavior without requiring a running Django server.

## 🚀 Components

1.  **`openapi.mock.json`**: An enriched OpenAPI 3.0 specification with realistic examples and standardized response structures.
2.  **`mock-server/`**: A Node.js Express-based server that maintains in-memory state for CRUD operations.
3.  **`mock-server/seed-data.json`**: Initial dataset for the mock server.
4.  **`httpie-mock-collection.json`**: HTTPie collection configured for the mock server.

## 🛠 Setup & Execution

### 1. Install Dependencies
Navigate to the `mock-server` directory and install the required Node.js packages:

```bash
cd mock-server
npm install
```

### 2. Start the Mock Server
Run the server using Node.js:

```bash
npm start
```
The server will be available at `http://localhost:4010`.

## 📖 Mock Behavior

- **Standardized Responses**: All responses are wrapped in `{ data, pagination, messagesList }`.
- **Authentication**: Use `/api/token/` with username `admin` and password `password` to get a mock JWT.
- **State Persistence**: Created posts, users, or comments are saved in memory for the duration of the server session.
- **Filtering**: Post listing supports `category`, `is_hot`, and `search` query parameters.

## 🧪 Testing with HTTPie

Import `httpie-mock-collection.json` into HTTPie Desktop. The `BASE_URL` is pre-configured to `http://localhost:4010`.
