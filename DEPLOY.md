# Deploy Womba API (Free Tier)

## Option 1: Render.com (Recommended - $0/month)

### Quick Deploy

1. **Sign up**: Go to [render.com](https://render.com) (no credit card required)

2. **New Web Service**: Click "New +" → "Web Service"

3. **Connect Repository**: 
   - Connect your GitHub account
   - Select `womba-api` repository

4. **Configure**:
   - **Name**: womba-api
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

5. **Environment Variables** (click "Advanced" → "Add Environment Variable"):
   ```
   WOMBA_API_KEY=<click "Generate" button>
   SECRET_KEY=<click "Generate" button>
   JIRA_BASE_URL=https://your-company.atlassian.net
   JIRA_EMAIL=your-email@company.com
   JIRA_API_TOKEN=your-jira-token
   OPENAI_API_KEY=sk-...
   ZEPHYR_API_TOKEN=eyJ0eXAi...
   ZEPHYR_BASE_URL=https://api.zephyrscale.smartbear.com/v2
   ```

6. **Deploy**: Click "Create Web Service"
   - Takes ~5 minutes
   - You'll get a URL like: `https://womba-api.onrender.com`

7. **Test**:
   ```bash
   curl https://your-app.onrender.com/health
   ```

### Features

- ✅ **Free forever** (750 hours/month)
- ✅ No credit card required
- ✅ Auto-sleeps after 15 min (wakes on request)
- ✅ HTTPS by default
- ⚠️  Cold starts (~30s) - fine for testing

### Using render.yaml (Alternative)

If `render.yaml` is in the repo, Render will auto-detect it:

```bash
git push origin main
# Go to Render dashboard → New Blueprint → Select womba-api
# Add environment variables in dashboard
# Deploy
```

---

## Option 2: Local Testing with ngrok (Instant - $0)

### Setup

1. **Install ngrok**:
   ```bash
   # macOS
   brew install ngrok
   
   # Or download from ngrok.com
   ```

2. **Start API locally**:
   ```bash
   cd womba-api
   # Make sure .env has all required variables
   uvicorn main:app --port 8000
   ```

3. **Expose with ngrok** (in another terminal):
   ```bash
   ngrok http 8000
   ```

4. **Copy URL** from ngrok output:
   ```
   Forwarding    https://abc123.ngrok-free.app -> http://localhost:8000
   ```

5. **Use with CLIs**:
   ```bash
   export WOMBA_API_URL="https://abc123.ngrok-free.app"
   export WOMBA_API_KEY="test-key"
   
   # Test
   womba generate -story PLAT-12991
   ```

### Features

- ✅ **Free** (40 requests/min)
- ✅ **Instant** setup
- ✅ No cold starts
- ⚠️  Must keep terminal open
- ⚠️  URL changes each restart (free tier)

---

## Testing the Deployment

Once deployed, test with:

```bash
# Set environment
export WOMBA_API_URL="https://your-app.onrender.com"
export WOMBA_API_KEY="your-key-from-render"

# Health check
curl $WOMBA_API_URL/health

# Generate tests (Go CLI)
womba generate -story PLAT-14095

# Generate tests (Java CLI)
java -jar target/womba.jar generate -story PLAT-14095

# Generate tests (Node.js CLI)
womba generate -s PLAT-14095
```

---

## Cost Comparison

| Platform | Cost | Setup Time | Best For |
|----------|------|------------|----------|
| **Render.com** | $0/month | 10 min | Persistent testing |
| **ngrok** | $0/month | 1 min | Quick local testing |
| Fly.io | $0-5/month | 15 min | Small apps (needs card) |
| Railway | $5+/month | 10 min | Production (not free) |

## Troubleshooting

### Render.com

**Issue**: Build failed
- Check requirements.txt is valid
- Ensure Python 3.11+ compatible

**Issue**: Service crashes
- Check logs in Render dashboard
- Verify all environment variables are set

**Issue**: 404 errors
- Ensure start command is: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Check PORT env var is used (auto-set by Render)

### ngrok

**Issue**: Connection refused
- Make sure API is running on port 8000
- Check firewall settings

**Issue**: Rate limit exceeded
- Free tier: 40 requests/min
- Upgrade to paid ($8/month) for unlimited

---

## Next Steps

After deployment:

1. **Update CLIs**: Set `WOMBA_API_URL` to your Render URL
2. **Test all languages**: Go, Java, Node.js
3. **Monitor**: Check Render dashboard for logs
4. **Scale**: Upgrade to paid tier if needed ($7/month for more resources)
