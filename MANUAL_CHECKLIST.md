# Manual Verification Checklist

## Setup
- Start services (includes Redis):
  - docker compose up -d --build

## 1) Conversation ownership (IDOR)
- Create two users (A and B) and log in to get tokens.
- Start a conversation with user A:
  - curl -X POST http://localhost:8000/api/conversation/start -H "Authorization: Bearer <TOKEN_A>" -H "Content-Type: application/json" -d "{}"
- Use the returned conversation_id and try to send a message with user B:
  - curl -X POST http://localhost:8000/api/conversation/<CONVERSATION_ID>/message -H "Authorization: Bearer <TOKEN_B>" -H "Content-Type: application/json" -d "{"message":"hi"}"
- Expected: 404 "Conversa nao encontrada" (should not leak other user's conversation).

## 2) JWT bad sub handling
- Call any auth-protected endpoint with a clearly invalid token:
  - curl -H "Authorization: Bearer invalid.token.here" http://localhost:8000/api/auth/me
- Expected: 401 (not 500).

## 3) daily_goal can be zero
- Update profile:
  - curl -X PUT http://localhost:8000/api/auth/me -H "Authorization: Bearer <TOKEN_A>" -H "Content-Type: application/json" -d "{"daily_goal":0}"
- Fetch stats:
  - curl -H "Authorization: Bearer <TOKEN_A>" http://localhost:8000/api/study/stats
- Expected: daily_goal = 0, daily_goal_progress = 0.

## 4) Admin cleanup endpoint
- Call the cleanup endpoint with an admin token:
  - curl -X DELETE http://localhost:8000/api/admin/cleanup/old-reviews?days=1 -H "Authorization: Bearer <ADMIN_TOKEN>"
- Expected: 200 with a message, not 500.

## 5) Redis session storage
- Start a game (quiz):
  - curl -X POST http://localhost:8000/api/games/quiz/start -H "Authorization: Bearer <TOKEN_A>"
- Check Redis for active keys and TTL:
  - redis-cli KEYS "games:*"
  - redis-cli TTL "games:<SESSION_ID>"
- Expected: key exists and TTL > 0.
