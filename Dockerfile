FROM --platform=$BUILDPLATFORM python:3.12-alpine AS builder
EXPOSE 8000
WORKDIR /app
COPY requirements.txt /app
RUN pip3 install -r requirements.txt --no-cache-dir
COPY . /app
RUN chmod +x ./runWebServer.sh
RUN sed -i 's/\r$//' runWebServer.sh
# ENTRYPOINT ["./runWebServer.sh"] 
ENTRYPOINT ["/bin/sh","runWebServer.sh"]