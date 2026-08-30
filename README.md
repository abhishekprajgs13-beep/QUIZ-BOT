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

## 🛠️ Step 1: Getting Your Environment Variables

Before deploying the bot, you need to gather specific secret keys (Environment Variables). Save these somewhere safe (like a Notepad file) as you will need them during deployment.

### 1. `API_ID` & `API_HASH`
These are your core Telegram App credentials.
- **Step 1:** Go to [my.telegram.org](https://my.telegram.org) and log in with your Telegram phone number.
- **Step 2:** Click on **"API development tools"**.
- **Step 3:** Fill in a random App Name and Short Name (e.g., "MyQuizBot").
- **Step 4:** Click **"Create application"**.
- **Step 5:** You will now see your **App api_id** (This is your `API_ID`) and **App api_hash** (This is your `API_HASH`). Copy both!

### 2. `CREATOR_BOT_TOKEN` & `RUNNER_BOT_TOKEN`
You need to create two separate bots on Telegram to avoid conflicts.
- **Step 1:** Open Telegram and search for **@BotFather**.
- **Step 2:** Send the command `/newbot`.
- **Step 3:** Give it a name (e.g., "Quiz Creator") and a username ending in bot (e.g., `MyQuizCreator_bot`).
- **Step 4:** BotFather will give you a **HTTP API Token**. Copy this! This is your `CREATOR_BOT_TOKEN`.
- **Step 5:** Repeat Steps 2 to 4 to create a second bot (e.g., "Quiz Runner"). The token for this second bot is your `RUNNER_BOT_TOKEN`.
*(Note: Using the same token for both will cause the bot to crash and conflict constantly!)*

### 3. `MONGODB_URI`
This is your database where all quizzes and scores are saved permanently.
- **Step 1:** Go to [mongodb.com](https://www.mongodb.com/) and create a free account.
- **Step 2:** Click **"Build a Database"** and select the **FREE (M0)** tier.
- **Step 3:** Choose a cloud provider (AWS/Google) and region near you. Click **"Create"**.
- **Step 4:** Set up a Database User by typing a Username and a Password. **Save this password!**
- **Step 5:** Under "Network Access", allow access from anywhere (IP Address: `0.0.0.0/0`).
- **Step 6:** Go to your Database dashboard, click **"Connect"** -> **"Drivers"** (Python).
- **Step 7:** Copy the connection string provided. It will look like this:
  `mongodb+srv://<username>:<password>@cluster0.mongodb.net/?retryWrites=true&w=majority`
- **Step 8:** Replace `<password>` in the string with the password you created in Step 4. This complete string is your `MONGODB_URI`.

### 4. `OWNER_ID` & `LOG_GROUP`
- **Step 1:** Open Telegram and search for the bot **@MissRose_bot** (or any ID bot).
- **Step 2:** Send `/id` to the bot. It will reply with your User ID (a long number). This is your `OWNER_ID`.
- **Step 3:** Create a new Private Telegram Group for logs. Add your Creator bot and Runner bot to this group.
- **Step 4:** Send `/id` in this group. Copy the Group ID (it usually starts with a minus sign `-`). This is your `LOG_GROUP`.

---

## 🚀 Step 2: How to Deploy on Render (Step-by-Step)

Render provides a completely free platform to host your bot 24/7.

1. **Create a Render Account:** Go to [render.com](https://render.com/) and sign up using your GitHub account.
2. **Connect Repository:** 
   - Click the **"New +"** button at the top right and select **"Web Service"**.
   - Click **"Build and deploy from a Git repository"**.
   - Connect your GitHub account and select your Quiz Bot repository from the list.
3. **Configure the Web Service:**
   - **Name:** Type a name for your app (e.g., `my-super-quiz-bot`).
   - **Region:** Select any region (e.g., Frankfurt or Oregon).
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** Delete whatever is there and type exactly: `pip install -r requirements.txt`
   - **Start Command:** Delete whatever is there and type exactly: `python run.py`
   - **Instance Type:** Select the **Free** option (512 MB RAM).
4. **Add Environment Variables:**
   - Scroll down and click on **"Advanced"**, then click **"Add Environment Variable"**.
   - You need to add all the secret keys you gathered in Step 1. Click "Add Environment Variable" for each one:
     - Key: `API_ID` | Value: *(Your API ID)*
     - Key: `API_HASH` | Value: *(Your API Hash)*
     - Key: `CREATOR_BOT_TOKEN` | Value: *(Your Creator Bot Token)*
     - Key: `RUNNER_BOT_TOKEN` | Value: *(Your Runner Bot Token)*
     - Key: `MONGODB_URI` | Value: *(Your MongoDB String)*
     - Key: `OWNER_ID` | Value: *(Your User ID)*
     - Key: `LOG_GROUP` | Value: *(Your Log Group ID)*
5. **Deploy!**
   - Scroll to the very bottom and click the big green **"Create Web Service"** button.
   - Wait for 3 to 5 minutes. You will see logs scrolling. Once you see "Your service is live 🎉", your bot is successfully running!

---

## ⏰ Step 3: Keep the Bot Awake 24/7 using Cron-job.org

Render's free tier automatically puts your bot to "sleep" if it doesn't receive any web traffic for 15 minutes. This means if you close Telegram, the bot shuts down. To fix this, we will use a free service to "ping" the bot every 5 minutes.

### Finding Your Web URL
1. Go to your Render dashboard where your bot is deployed.
2. Look at the very top, right under your bot's name. You will see a link that looks like `https://my-super-quiz-bot.onrender.com`.
3. Copy this link.

### Setting up Cron-job.org
1. **Sign Up:** Go to [cron-job.org](https://cron-job.org/) and create a free account.
2. **Create a Job:** Once logged in, click on **"Cronjobs"** in the left menu, then click the **"CREATE CRONJOB"** button.
3. **Fill in the Details:**
   - **Title:** Type `Quiz Bot Keep-Alive` (or anything you like).
   - **URL:** Paste the link you copied from Render, and add `/healthz` at the very end of it.
     - *Example:* `https://my-super-quiz-bot.onrender.com/healthz`
   - **Enable job:** Make sure this toggle is **ON** (Orange).
   - **Save responses in job history:** Leave this **OFF** (Grey).
4. **Execution Schedule:**
   - Select **"Every 5 minutes"** from the drop-down menu. (Do not set it lower than 5 minutes to avoid spamming the free server).
5. **Schedule Expires:** 
   - Leave the toggle **OFF** (Grey). You want this job to run forever.
6. **Notify me when... (Notification Settings):**
   - To avoid getting spammed with useless emails whenever the server restarts, configure these toggles:
   - *execution of the cronjob fails* -> **OFF** (Grey)
   - *execution of the cronjob succeeds after it failed before* -> **OFF** (Grey)
   - *the cronjob will be disabled because of too many failures* -> **ON** (Orange)
   - *the server TLS certificate is about to expire* -> **OFF** (Grey)
7. **Finalize:**
   - Click the orange **"CREATE"** button at the bottom right of the page.

🎉 **Congratulations!** Your Quiz Bot is now fully deployed, configured, and will stay online 24/7 completely for free! 

---
*Created with ❤️ by ABHISHEK PRAJAPAT.*
