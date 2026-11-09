# 공격자·정상 시민 컨테이너. wan 망은 인터넷이 막혀 있으므로 도구는 빌드 때 넣는다.
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends iputils-ping curl iproute2 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /lab
CMD ["sleep", "infinity"]
