# VERA-IN

**Verification Engine for Results & Accountability - Indiana**

Year Zero infrastructure for Indiana's GPS (Graduate Prepared to Succeed) accountability system.

## Features

- **Year Zero Dashboard** - GPS grade distribution during the consequence-free baseline year
- **GPS Grade Distribution** - Analyze A-F calculations before they count
- **Portrait of a Graduate** - Track implementation of Indiana's five characteristics
- **Milestone Tracker** - Monitor progress toward GPS implementation goals

## Background

Indiana's HEA 1498 (2025) established the GPS framework. The 2025-26 school year is "Year Zero" - grades are calculated and published, but carry no consequences. This is the window for verification.

In 2026-27, grades will carry legal consequences for schools.

## Data

Currently using demo data for verification testing. Planned integrations:
- Indiana GPS Portal (indianagps.doe.in.gov)
- IDOE EdData (eddata.doe.in.gov)
- Ed-Fi Data Exchange

## Local Development

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deployment

Configured for Render.com auto-deployment via GitHub.

## Part of H-EDU.Solutions

An initiative of [Hallucinations.cloud](https://hallucinations.cloud)
