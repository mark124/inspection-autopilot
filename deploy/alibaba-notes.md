# Deploying to Alibaba Cloud (30-minute plan, once the account exists)

Goal: backend running on Alibaba Cloud + a code file proving use of Alibaba Cloud services (`app/qwen.py` calls Model Studio/DashScope; the compute itself also runs on Alibaba Cloud).

## Prerequisites (Mark, manual)
1. Account at alibabacloud.com (email + phone verification).
2. Activate Model Studio, create an API key. Free tier tokens are on the Singapore endpoint, which matches the default `QWEN_BASE_URL` in `.env.example`.
3. Apply for the hackathon voucher: https://www.qwencloud.com/challenge/hackathon/voucher-application

## Option A (recommended): Simple Application Server / ECS
1. Create the smallest Ubuntu instance (Singapore region keeps model latency low and matches the free-tier endpoint).
2. Open port 8080 in the security group (or put nginx/Caddy in front on 443 later; not required for judging).
3. On the instance:
   ```bash
   sudo apt update && sudo apt install -y docker.io
   git clone <public repo url> && cd inspection-autopilot
   sudo docker build -t autopilot .
   sudo docker run -d --name autopilot -p 8080:8080 \
     -e DASHSCOPE_API_KEY=sk-... autopilot
   curl localhost:8080/api/health   # expect mode: "live"
   ```
4. Screenshot the console + `/api/health` for the submission evidence.

Known gotcha from previous deploys: `docker restart` does not re-read env vars. To rotate the key: `docker rm -f autopilot` then `docker run` again.

## Option B: Function Compute (custom container)
Works with the same Dockerfile (listens on 8080, stateless enough for demo purposes; SQLite resets on cold start, acceptable for judging but say so honestly in the demo). Prefer Option A because the append-only log surviving across requests is part of the story.

## Submission evidence checklist
- Public URL of the running app
- `app/qwen.py` permalink as the "code file demonstrating use of Alibaba Cloud services and APIs"
- Console screenshot showing the ECS instance + Model Studio key page (key redacted)
