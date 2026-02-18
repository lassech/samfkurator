FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

WORKDIR /app

COPY . .

RUN pip install -e .

# Install Playwright's Chromium browser
RUN playwright install chromium

EXPOSE 5001

CMD ["gunicorn", "samfkurator.web.app:app", "--bind", "0.0.0.0:5001", "--workers", "2"]
