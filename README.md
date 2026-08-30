# 🎯 Advanced Telegram Quiz Bot

> **Developed by ABHISHEK PRAJAPAT with all love ❤️**

Welcome to the most advanced, feature-rich Telegram Quiz Bot! This bot allows you to create, manage, and play interactive quizzes seamlessly within Telegram. It comes packed with a Dual-Bot architecture, Mini Web App support, AI capabilities, and much more!

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

## 📋 Final Environment Variables Master Checklist

Yahan ek-ek Environment Variable (Secret Key) ka ultra-detailed checklist hai. Deployment ke waqt Render me aapko yahi values exact isi format me daalni hain.

### 1️⃣ Telegram Core Credentials (Bot Identity)

#### 🔹 `API_ID`
- **Value Format:** Numbers (Jaise: `12345678`)
- **Detail:** Telegram application ka unique ID hai jo `my.telegram.org` se milta hai. Iske bina bot Telegram servers se communicate nahi kar sakta.
- **Kaise Le Kar Aayein:**
  1. Jao [my.telegram.org](https://my.telegram.org) par aur login karo.
  2. "API development tools" par click karo.
  3. App Name aur Short Name dalo aur "Create application" dabao.
  4. Yahan aapko apna `api_id` mil jayega.

#### 🔹 `API_HASH`
- **Value Format:** Text string (Jaise: `a1b2c3d4e5f6g7h8i9j0...`)
- **Detail:** Telegram application ki security key hai jo `my.telegram.org` se milti hai.
- **Kaise Le Kar Aayein:** Upar wale same process se `api_id` ke theek niche `api_hash` milta hai.

#### 🔹 `CREATOR_BOT_TOKEN`
- **Value Format:** `1234567890:ABCdefgh...`
- **Detail:** `@BotFather` se mila aapka **Single Bot Token**. Ye Pyrogram engine ko Quiz Create karne, edit karne aur manage karne me help karta hai.
- **Kaise Le Kar Aayein:**
  1. Telegram me **@BotFather** search karo aur `/newbot` likho.
  2. Bot ka naam aur username dalo.
  3. BotFather aapko ek "HTTP API Token" dega. Yahi aapka Token hai.

#### 🔹 `RUNNER_BOT_TOKEN`
- **Value Format:** `1234567890:ABCdefgh...`
- **Detail:** Isme bhi **wahi same Single Bot Token** daalna hai. Ye Python-Telegram-Bot engine ko Groups me quiz chalane aur leaderboards dikhane me help karta hai.

---

### 2️⃣ Database & Ownership (Data Storage & Admin)

#### 🔹 `MONGODB_URI`
- **Value Format:** `mongodb+srv://username:password@cluster0.xxxx.mongodb.net/`
- **Detail:** MongoDB Atlas database ka connection link hai. Isme aapke real username aur password bhare hone chahiye.
- **Kaise Le Kar Aayein:**
  1. [mongodb.com](https://www.mongodb.com/) par free account banao.
  2. "Build a Database" -> FREE (M0) select karke Create karo.
  3. Username aur Password banao (Password yaad rakhna).
  4. Network Access me jao aur IP `0.0.0.0/0` (Allow Anywhere) add karo.
  5. Connect -> Drivers (Python) me jao aur Connection String copy karo.
  6. String me `<password>` ki jagah apna asli password dal do.

#### 🔹 `MONGODB_DB_NAME`
- **Value Format:** `quizbot`
- **Detail:** Aapke database ka naam. Isko bilkul `quizbot` hi likhna hai.

#### 🔹 `OWNER_ID`
- **Value Format:** Numbers (Jaise: `12345678`)
- **Detail:** Aapka personal numeric Telegram ID. Bot sirf aapko Owner manega aur admin commands (/stats, /broadcast) chalane dega.
- **Kaise Le Kar Aayein:** Telegram par **@MissRose_bot** ko `/id` bhejo. Jo numbers reply me aayenge wo aapki Owner ID hai.

---

### 3️⃣ Channel & Log Group (Management & Force Subscribe)

#### 🔹 `LOG_GROUP`
- **Value Format:** Negative Number (Jaise: `-100123456789`)
- **Detail:** Aapke us 1 Private Log Group ka ID. Jab bhi bot me koi activity ya error aayega, bot isme silently alerts bhejega.
- **Kaise Le Kar Aayein:** Ek private group banao, apne bot aur Rose bot ko add karo, aur `/id` bhejo. Group ID humesha minus `-` se shuru hoti hai.

#### 🔹 `CHANNEL_ID`
- **Value Format:** Negative Number (Jaise: `-100987654321`)
- **Detail:** Aapke 1 Official Channel ka numeric ID. Broadcast aur system posts ke liye.
- **Kaise Le Kar Aayein:** Apne channel me koi message karein aur use Rose bot wale group me forward karke `/id` check karein (ya channel me Rose bot add karke `/id` bhej dein).

#### 🔹 `REQUIRED_SUB_CHANNEL`
- **Value Format:** Username with `@` (Jaise: `@myquizchannel`)
- **Detail:** Aapke 1 Official Channel ka `@username`. Jab tak koi user is channel ko join nahi karega, bot use start/quiz-create nahi karne dega. Dhyan rahe bot channel me Admin hona chahiye!

---

### 4️⃣ Feature Flags & AI (Free Bot & AI Quiz Generator)

#### 🔹 `FREE_BOT`
- **Value Format:** `True`
- **Detail:** Isko bilkul `True` likhna hai (T is capital). Isse aapka bot poori tarah sabhi users ke liye 100% Free chalega aur koi payment ki maang nahi karega.

#### 🔹 `OPENROUTER_DEFAULT_KEYS`
- **Value Format:** `sk-or-v1-xxxxxxxxxxxxxxxx`
- **Detail:** OpenRouter.ai se mila aapka AI API Key. Isse bot me AI dwara automatic questions generate honge.
- **Kaise Le Kar Aayein:** [openrouter.ai](https://openrouter.ai/) par account banao, Settings -> Keys me jao aur ek nayi key generate karke copy kar lo.

---

### 5️⃣ Mini App WebApp (Visual In-Telegram Quiz Player)

#### 🔹 `MINI_APP_DOMAIN`
- **Value Format:** `https://quizbot-app.onrender.com` *(Aapke Render app ka exact URL)*
- **Detail:** Render par aapki service ka public URL. Isse Telegram me Play Quiz button work karega.
- **Kaise Le Kar Aayein:** Jab aap Render par bot deploy karenge, to top left par aapko aapka URL dikhega, usko copy kar lein.

#### 🔹 `MINI_APP_HOST`
- **Value Format:** `0.0.0.0`
- **Detail:** Render server ke internal network binding ke liye. Isko exact `0.0.0.0` hi likhna hai.

#### 🔹 `MINI_APP_PORT`
- **Value Format:** `8080`
- **Detail:** Port number. Isko exact `8080` hi likhna hai.

---

### 🚫 KHALLI / BLANK Chhodne Wale Variables (Inko NAHI bharna):
- **`BOT_GROUP`** -> Khali chhod dein (Hata diya hai)
- **`RAZORPAY_KEY_ID`** -> Khali chhod dein (Bot free hai)
- **`RAZORPAY_KEY_SECRET`** -> Khali chhod dein (Bot free hai)
- **`ADMIN_IDS`** -> Khali chhod dein

---

## 🚀 Step 2: How to Deploy on Render (Step-by-Step)

1. **Create Account:** Go to [render.com](https://render.com/) and sign up.
2. **Connect Repo:** Click **"New +"** -> **"Web Service"** -> **"Build and deploy from a Git repository"** -> Connect your GitHub and select this repository.
3. **Configure Settings:**
   - **Name:** Your bot's name.
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python run.py`
   - **Instance Type:** **Free** (512 MB).
4. **Environment Variables:** Scroll to **"Advanced"** -> **"Add Environment Variable"** and add all the variables from the checklist above.
5. **Deploy:** Click **"Create Web Service"**.

---

## ⏰ Step 3: Keep the Bot Awake 24/7 (Cron-job.org)

1. Copy your Render app URL (e.g., `https://quizbot-app.onrender.com`).
2. Go to [cron-job.org](https://cron-job.org/) and create an account.
3. Click **"Cronjobs"** -> **"CREATE CRONJOB"**.
4. **URL:** Paste your Render URL and add `/healthz` at the end (`https://quizbot-app.onrender.com/healthz`).
5. **Execution Schedule:** Select **Every 5 minutes**.
6. **Notifications:** Turn **ON** only `"the cronjob will be disabled because of too many failures"`. Leave all others **OFF**.
7. Click **"CREATE"**.

---
*Created with ❤️ by ABHISHEK PRAJAPAT.*
