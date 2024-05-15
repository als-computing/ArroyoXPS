FROM python:3.12

WORKDIR /app

COPY . /app
RUN pip install --no-cache-dir --upgrade .

CMD ["python", "-m", "tr_ap_xps.listener]
