# For Lina — Streamlit App

A small romantic Streamlit page created for Lina. It uses a red/pink theme, displays an available image from the project directory, shows a short poem, and includes a "Show balloons" surprise.

Requirements

- Python 3.8+
- See `requirements.txt`

Run (PowerShell)

```powershell
python -m pip install -r requirements.txt
streamlit run app.py
```

If you want to package or customize, edit `app.py`. Images placed in the project root will automatically be shown on the page (it prefers filenames with `lina`, `cutie`, `good`, or `rose`).

## Deployment (Heroku via GitHub Actions)

This repository can be deployed automatically to Heroku using the included GitHub Actions workflow.

Steps:

- Create a Heroku app (dashboard.heroku.com) and note the app name.
- In the GitHub repository, go to Settings → Secrets and variables → Actions and add these secrets:
  - `HEROKU_API_KEY` — your Heroku API key
  - `HEROKU_APP_NAME` — the Heroku app name
  - `HEROKU_EMAIL` — your Heroku account email
- Push to `main`. The workflow `.github/workflows/deploy-heroku.yml` will run and deploy to Heroku.

Notes:

- The workflow uses Python 3.12. Adjust if needed.
- The `Procfile` instructs Heroku to run Streamlit.
