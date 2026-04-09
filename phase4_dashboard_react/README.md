# Banking BI Copilot — Phase 4: Executive Dashboard

## Stack
- React 18 + Recharts
- Dark financial theme (DM Serif Display + DM Mono + Instrument Sans)
- Three sections: KPI Dashboard, Investigation History, PDF Reports
- Live chat panel connected to Bedrock supervisor agent

## Run locally

```powershell
cd C:\Users\anita\banking-bi-copilot\phase4_dashboard_react
npm install
npm start
```

Opens at http://localhost:3000

## Build for production

```powershell
npm run build
```

Output goes to `build/` folder — ready to deploy to S3.

## Deploy to S3 + CloudFront (Phase 5)

```powershell
# After npm run build:
aws s3 sync build/ s3://YOUR-BUCKET-NAME --delete
aws cloudfront create-invalidation --distribution-id YOUR-DIST-ID --paths "/*"
```

## API Configuration

The dashboard is pre-configured to use:
- Chat: POST https://9yxcjs8frj.execute-api.us-east-1.amazonaws.com/prod/chat
- Investigate: POST https://9yxcjs8frj.execute-api.us-east-1.amazonaws.com/prod/investigate

To change, edit the `API` constant at the top of `src/App.js`.
