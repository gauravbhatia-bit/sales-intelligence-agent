# Deployment

The public demo uses two services:

- FastAPI backend on Render
- Streamlit frontend on Streamlit Community Cloud

No Gemini key is required. The deployed application uses the local NLP classifier.

## 1. Push the repository to GitHub

Commit all project files except ignored local state such as `.venv`, `.logs`, `.env`, and `.local-services.json`.

## 2. Deploy FastAPI on Render

1. In Render, choose **New > Blueprint**.
2. Connect this GitHub repository.
3. Render reads `render.yaml` and creates `sales-intelligence-api`.
4. Wait for the health check to pass.
5. Copy the resulting URL, for example `https://sales-intelligence-api.onrender.com`.

The API documentation will be available at `<render-url>/docs`.

## 3. Deploy Streamlit

1. In Streamlit Community Cloud, choose **Create app**.
2. Select this repository and branch.
3. Set the entrypoint to `frontend/app.py`.
4. Select Python 3.11.
5. In Advanced settings, add this secret using the actual Render URL:

```toml
BACKEND_URL = "https://sales-intelligence-api.onrender.com"
```

6. Deploy and test the example questions.

## 4. Add it to a portfolio

Use the Streamlit URL for a **Live demo** button. For an iframe, append `/?embed=true` to the public Streamlit URL.

Also link to the GitHub repository and describe the measurable NLP work: TF-IDF bigrams, logistic-regression intent classification, entity extraction, confidence-based routing, and holdout evaluation.
