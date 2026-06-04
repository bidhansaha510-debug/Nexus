# 🚀 Deploy NEXUS AI — 24/7 Cloud Hosting (FREE)

This guide deploys NEXUS to **Render.com** so it runs forever, even when your PC is off.

---

## Prerequisites

1. A **GitHub account** (free)
2. A **Render.com account** (free — sign up with GitHub)
3. Your NEXUS code **pushed to a GitHub repository**

---

## Step 1: Push Code to GitHub

If you haven't already, create a GitHub repo and push your code:

```powershell
cd D:\NEXUS
git init
git add .
git commit -m "NEXUS AI — ready for cloud deployment"
git remote add origin https://github.com/YOUR_USERNAME/NEXUS.git
git push -u origin main
```

> ⚠️ **Important**: Your `config.py` has API keys hardcoded as fallbacks.
> For public repos, consider using a `.env` file and adding it to `.gitignore`.
> On Render, keys are set as secure environment variables (see Step 3).

---

## Step 2: Deploy on Render

### Option A: One-Click Blueprint (Recommended)

1. Go to [https://render.com](https://render.com) and sign in with GitHub
2. Click **"New +"** → **"Blueprint"**
3. Connect your NEXUS GitHub repository
4. Render will detect `render.yaml` and auto-configure everything
5. Click **"Apply"**

### Option B: Manual Setup

1. Go to [https://render.com](https://render.com) and sign in
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repo
4. Configure:
   - **Name**: `nexus-ai`
   - **Runtime**: `Docker`
   - **Plan**: `Free`
5. Click **"Create Web Service"**

---

## Step 3: Set Environment Variables

In the Render dashboard for your service:

1. Go to **"Environment"** tab
2. Add these variables:

| Key            | Value                          |
|----------------|--------------------------------|
| `GROQ_API_KEY` | Your Groq API key              |
| `RENDER`       | `true`                         |

> Render automatically sets the `PORT` variable — you don't need to add it.

---

## Step 4: Verify

1. Wait for the build to complete (first build takes ~5-10 minutes)
2. Click the URL shown at the top of your service page (e.g., `https://nexus-ai.onrender.com`)
3. You should see the NEXUS web login page
4. **Shut down your PC** — NEXUS keeps running on Render! 🎉

---

## Auto-Deploy

Every time you push to GitHub, Render automatically rebuilds and redeploys:

```powershell
git add .
git commit -m "Update NEXUS"
git push
```

Render picks up the changes within ~1 minute.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Build fails | Check Render logs → "Events" tab |
| Out of memory | Free tier has 512MB; disable heavy modules |
| App sleeps | Free tier may sleep after 15min inactivity; first request wakes it |
| Port error | Don't set PORT manually; Render sets it automatically |

---

## 💡 Tips

- **Custom domain**: In Render settings, add your own domain for free
- **Upgrade later**: If you need more RAM/speed, upgrade to $7/mo Starter plan
- **Monitor logs**: Render dashboard → "Logs" tab shows live output
