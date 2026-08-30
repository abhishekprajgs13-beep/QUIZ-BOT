# 🎯 Advanced Telegram Quiz Bot

> **Developed by ABHISHEK PRAJAPAT with all love ❤️**

Welcome to the most advanced, feature-rich Telegram Quiz Bot! This bot allows you to create, manage, and play interactive quizzes seamlessly within Telegram. It comes packed with a Dual-Bot architecture (Creator & Runner), Mini Web App support, AI capabilities, and much more!

---

## 🌟 Features of the Bot

- **Dual-Bot Architecture:** Segregated processes for creating quizzes and playing quizzes to ensure maximum stability.
- **Interactive Quizzes:** Play quizzes in groups, channels, or private messages.
- **Mini Web App Support:** Play quizzes directly inside Telegram's modern Web App interface.
- **AI Quiz Generation:** Generate quizzes automatically using AI integration.
- **Polls & Leaderboards:** Real-time polling and dynamic leaderboards for competitive group quizzes.
- **Broadcast & Admin Tools:** Global broadcast capabilities, user banning, and deep statistics for bot admins.
- **Multiple Supported Formats:** Import quizzes from files or create them manually using the step-by-step wizard.
- **Payment & Subscription Gates:** Monetize your quizzes or gate them behind channel subscriptions.

---

## 🛠️ Step 1: Getting ALL Your Environment Variables (Step-by-Step)

When deploying this bot, there are around 15 environment variables you can use. Some are mandatory (Required), and some are optional features. Save these somewhere safe before deploying!

### 🔴 REQUIRED VARIABLES (Must Have)

**1. `API_ID` & `API_HASH`**
These are your core Telegram App credentials.
- Go to [my.telegram.org](https://my.telegram.org) and log in.
- Click on **"API development tools"**.
- Fill in a random App Name and Short Name (e.g., "MyQuizBot").
- Click **"Create application"**.
- You will now see your **App api_id** (`API_ID`) and **App api_hash** (`API_HASH`). Copy both!

**2. `CREATOR_BOT_TOKEN` & `RUNNER_BOT_TOKEN`**
You need TWO bots from BotFather to avoid engine conflicts.
- Search for **@BotFather** on Telegram and send `/newbot`.
- Give it a name (e.g., "Quiz Creator") and get the HTTP API Token. This is your `CREATOR_BOT_TOKEN`.
- Send `/newbot` again, create a second bot (e.g., "Quiz Runner"), and get its token. This is your `RUNNER_BOT_TOKEN`.

**3. `MONGODB_URI`**
The database where all quizzes and scores are saved.
- Go to [mongodb.com](https://www.mongodb.com/) and create a free account.
- Click **"Build a Database"** -> select **FREE (M0)** tier -> Click **Create**.
- Set up a Database User (Username & Password). **Save this password!**
- Go to **Network Access** -> Add IP Address -> "Allow Access from Anywhere" (`0.0.0.0/0`).
- Go to Database -> Connect -> Drivers (Python) -> Copy the connection string.
- Replace `<password>` in the string with your password. The final string is your `MONGODB_URI`.

**4. `OWNER_ID`**
Your personal Telegram account ID to give you Admin rights.
- Search for **@MissRose_bot** (or any ID bot) on Telegram.
- Send `/id` to the bot. It will reply with a long number. This is your `OWNER_ID`.

---

### 🟢 OPTIONAL & ADVANCED VARIABLES (Add these if you want extra features)

**5. `ADMIN_IDS`**
- If you have partners/admins who also need access, get their Telegram IDs (using `@MissRose_bot`) and put them here separated by commas. (e.g., `1234567,9876543`).

**6. `LOG_GROUP`**
- Create a private Telegram group for bot logs (alerts when quizzes finish, errors, etc.). Add your bots to this group. Send `/id` inside the group. Copy the group ID (starts with a `-`). Put this in `LOG_GROUP`.

**7. `BOT_GROUP` & `CHANNEL_ID`**
- If you have an official Support Group or Updates Channel for your bot, put their IDs here (again, get them by forwarding a message to an ID bot or using `@MissRose_bot` in the group/channel).

**8. `REQUIRED_SUB_CHANNEL`**
- To force users to join your channel before they can play quizzes (Force Sub/Subscribe Gate).
- Put your channel's public username here WITH the `@` symbol (e.g., `@MyAwesomeChannel`). Ensure your bot is an Admin in this channel!

**9. `FREE_BOT`**
- If you want EVERY user to have premium features automatically for free.
- Set this to `True` (or `False` if you want to restrict features).

**10. `RAZORPAY_KEY_ID` & `RAZORPAY_KEY_SECRET`**
- If you want to sell Premium subscriptions inside the bot via Razorpay.
- Go to the [Razorpay Dashboard](https://dashboard.razorpay.com/), go to Settings -> API Keys -> Generate Key.
- You will get a Key ID (`RAZORPAY_KEY_ID`) and a Key Secret (`RAZORPAY_KEY_SECRET`).

**11. `PDF_API_BASE`**
- If you purchased or host an external PDF generation API to prevent RAM crashes when users generate heavy PDFs. Paste the API URL here.

**12. `MONGODB_DB_NAME`**
- The name of your database collection. If you leave this blank, it defaults to `quizbot`. You can put `quizbot` here.

---

## 🚀 Step 2: How to Deploy on Render (Step-by-Step)

1. Go to [render.com](https://render.com/) and sign up.
2. Click **"New +"** -> **"Web Service"** -> **"Build and deploy from a Git repository"**.
3. Connect your GitHub account and select your Quiz Bot repository.
4. **Configure the Service:**
   - **Name:** Type a name (e.g., `abhishek-quiz-bot`).
   - **Region:** Select any region.
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** Delete whatever is there and type: `pip install -r requirements.txt`
   - **Start Command:** Delete whatever is there and type: `python run.py`
   - **Instance Type:** Select the **Free** option (512 MB).
5. **Add Environment Variables:**
   - Scroll down to **"Advanced"** -> **"Add Environment Variable"**.
   - Now, click "Add Environment Variable" multiple times and type out ALL the keys and values you gathered from **Step 1** (Required ones are mandatory, Optional ones are up to you).
6. **Deploy!**
   - Click the green **"Create Web Service"** button. Wait 3-5 minutes until you see "Your service is live 🎉".

---

## ⏰ Step 3: Keep the Bot Awake 24/7 (Cron-job.org)

Render's free tier automatically puts your bot to "sleep" after 15 minutes of inactivity. To fix this:

1. **Copy your Render URL:** On your Render dashboard, copy the link at the top (e.g., `https://abhishek-quiz-bot.onrender.com`).
2. Go to [cron-job.org](https://cron-job.org/) and sign up for free.
3. Click **"Cronjobs"** -> **"CREATE CRONJOB"**.
4. **Fill Settings:**
   - **Title:** `Quiz Bot Ping`
   - **URL:** Paste your Render link and add `/healthz` at the end (e.g., `https://abhishek-quiz-bot.onrender.com/healthz`).
   - **Execution Schedule:** Select **Every 5 minutes**.
   - **Schedule Expires:** Leave **OFF** (Grey).
5. **Notify me when (Notifications):**
   - *execution of the cronjob fails* -> **OFF** (Grey)
   - *execution of the cronjob succeeds after it failed before* -> **OFF** (Grey)
   - *the cronjob will be disabled because of too many failures* -> **ON** (Orange)
   - *the server TLS certificate is about to expire* -> **OFF** (Grey)
6. Click **"CREATE"**. Your bot is now 24/7 online for free!

---
*Created with ❤️ by ABHISHEK PRAJAPAT.*
