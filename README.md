# owo-script (retired)

This repo used to host `owo.py`, a Discord OwO-bot farming script with a
small Flask dashboard, deployed on Render. It's been retired and its code
removed.

**Replacement:** [status-sim](https://github.com/hatim69/status-sim) — a
"Status - Sims But Social" style social media simulator. That's now the
active project; see its README for setup and deployment.

## If the old Render service is still running

Removing the code here does **not** stop a Render service that's already
deployed from this repo — Render keeps running whatever it last
successfully deployed until you act on it. To actually turn it off:

1. Log into [Render](https://dashboard.render.com) (works fine from a
   phone browser).
2. Open the Web Service that was deploying `owo.py` from this repo.
3. **Settings → Suspend Web Service** (or delete it if you don't want to
   keep it around at all).

Then follow the [status-sim README](https://github.com/hatim69/status-sim#deploy-it-so-you-can-open-it-from-your-phone)
to deploy that app as a new Render Web Service in its place.
