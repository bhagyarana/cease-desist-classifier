# Vercel Cloud Deployment Guide

This guide details the step-by-step instructions to deploy the CeaseGuard platform (Next.js frontend + FastAPI backend) on **Vercel** connected to a persistent **PostgreSQL** cloud database.

---

## Prerequisites
1. A **Vercel** account linked to your GitHub.
2. A **Google Gemini API Key** (from Google AI Studio).
3. A **PostgreSQL database connection string** (e.g., from Neon, Supabase, or Vercel Postgres).

---

## Step 1: Provision Cloud PostgreSQL Database
Since Vercel runs serverless functions on ephemeral containers, local files (like SQLite DB files or JSONL logs) will not persist. We must use a cloud database:

1. Create a free PostgreSQL instance on **Neon** (https://neon.tech) or **Supabase** (https://supabase.com).
2. Copy the connection string. It should look like this:
   `postgresql://username:password@ephemeral-hostname.neon.tech/neondb?sslmode=require`

---

## Step 2: Push Project to GitHub
Initialize git and push your cleaned repository structure to your GitHub account:
```bash
git init
git add .
git commit -m "feat: CeaseGuard Next.js + FastAPI Gemini platform upgrade"
git remote add origin https://github.com/your-username/your-repo.git
git branch -M main
git push -u origin main
```

---

## Step 3: Deploy to Vercel

1. Open your **Vercel Dashboard** and click **Add New** → **Project**.
2. Import your GitHub repository.
3. Configure the Project Settings:
   * **Framework Preset**: Select **Next.js** (detected automatically).
   * **Root Directory**: `./` (leave default).
   * **Build Command**: `next build` (leave default).
   * **Output Directory**: `.next` (leave default).
4. Add the following **Environment Variables**:
   * `GEMINI_API_KEY`: Your Google Gemini API Key.
   * `DATABASE_URL` (or `POSTGRES_URL`): Your cloud PostgreSQL connection string.
5. Click **Deploy**.

---

## Step 4: Automatic Schema Migration
You do **not** need to manually run any SQL table migration scripts! 

When the serverless FastAPI app spins up on Vercel, `api/index.py` detects that the database type is `"postgres"`, connects via your connection string, and automatically runs `initialize_postgres()` to create the necessary tables (`cease_requests`, `audit_logs`, `archive_logs`, `deferred_requests`, `document_embeddings`) if they do not already exist.

---

## Step 5: Verification & Testing
1. Wait for Vercel to complete the build and generate your deployment domain (e.g., `https://cease-guard-classifier.vercel.app`).
2. Navigate to your custom domain.
3. Go to the **Ingest Console**, upload a legal C&D document, and verify that the progress tracker runs and completes successfully.
4. Open the **History & Logs** dashboard to confirm that transaction audits are being read and rendered directly from your cloud PostgreSQL database tables.
