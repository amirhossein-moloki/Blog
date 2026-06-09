# Postman API Testing Guide - Blog Platform

This guide explains how to set up and use the provided Postman Collection for automated testing of the Blog Platform APIs.

## 1. Postman Environment Setup

To use this collection, you should create a Postman Environment and define the following variables:

| Variable | Description | Example Value |
| :--- | :--- | :--- |
| `baseUrl` | The root URL of the API | `http://localhost:8000` |
| `username` | Test user's username | `admin` |
| `password` | Test user's password | `your_secure_password` |
| `accessToken` | JWT Access Token | *(Set automatically by Login request)* |
| `refreshToken`| JWT Refresh Token | *(Set automatically by Login request)* |
| `postSlug` | Slug of a blog post | *(Set automatically by List Posts)* |
| `postId` | ID of a blog post | *(Set automatically by List Posts)* |
| `mediaId` | ID of a media object | *(Set automatically by List Media)* |

## 2. Execution Order

For the automated tests to pass correctly, the requests should be executed in the following order:

1.  **Authentication > Login**: This obtains the JWT tokens and stores them in the environment for subsequent authenticated requests.
2.  **Posts > List Posts**: This fetches the latest posts and extracts a `postSlug` and `postId` to be used in detail and interaction requests.
3.  **Other Requests**: Once `accessToken` and `postSlug` are set, you can run all other requests (Users, Media, Interactions, etc.) in any order.

## 3. Running Automated Tests

### Using Postman App
1.  Import the `postman_collection.json` file.
2.  Select your Environment.
3.  Click on the collection name and select **Run**.
4.  Ensure the execution order is correct and click **Run Blog Platform API**.

### Using Newman (CLI)
If you have Newman installed, you can run the collection from your terminal:

```bash
newman run postman_collection.json -e your_environment.json
```

## 4. Test Coverage
The collection includes automated JavaScript tests at both the collection and request levels:
*   **Collection Level**: Global response time validation (less than 500ms).
*   **Request Level**:
    *   HTTP Status Code validation (200, 201, etc.).
    *   Standard Response Wrapper validation (`data`, `pagination`, `messagesList`).
    *   Required field presence and data type checking.
    *   Dynamic environment variable assignment for chained requests.
