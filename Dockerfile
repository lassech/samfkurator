FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

WORKDIR /app

COPY . .

RUN pip install -e .

# Install Playwright's Chromium browser
RUN playwright install chromium

# Download og udpak nyeste bypass-paywalls extension
RUN curl -fsSL \
    "https://gitflic.ru/project/magnolia1234/bpc_uploads/blob/raw?file=bypass-paywalls-chrome-clean-latest.crx" \
    -o /tmp/bypass-paywalls.crx \
  && mkdir -p extensions/bypass-paywalls \
  && python3 scripts/unpack_crx.py /tmp/bypass-paywalls.crx extensions/bypass-paywalls \
  && rm /tmp/bypass-paywalls.crx

EXPOSE 5001

CMD ["gunicorn", "samfkurator.web.app:app", "--bind", "0.0.0.0:5001", "--workers", "2"]
