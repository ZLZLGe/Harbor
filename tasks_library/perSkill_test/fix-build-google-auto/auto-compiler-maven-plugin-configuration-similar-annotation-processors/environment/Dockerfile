FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y \
    openjdk-17-jdk \
    maven \
    python3 \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp/descriptor-build

COPY processor-src/descriptor-processor/src ./descriptor-processor/src
COPY processor-src/descriptor-runtime/src ./descriptor-runtime/src

RUN mkdir -p descriptor-processor/classes \
    && javac -d descriptor-processor/classes $(find descriptor-processor/src -name '*.java') \
    && mkdir -p descriptor-processor/classes/META-INF/services \
    && cp descriptor-processor/src/META-INF/services/javax.annotation.processing.Processor descriptor-processor/classes/META-INF/services/javax.annotation.processing.Processor \
    && jar --create --file descriptor-processor-1.0.0.jar -C descriptor-processor/classes . \
    && mkdir -p descriptor-runtime/classes \
    && javac -d descriptor-runtime/classes $(find descriptor-runtime/src -name '*.java') \
    && jar --create --file descriptor-runtime-1.0.0.jar -C descriptor-runtime/classes . \
    && mkdir -p /root/.m2/repository/com/acme/build/descriptor-processor/1.0.0 \
    && mkdir -p /root/.m2/repository/com/acme/build/descriptor-runtime/1.0.0 \
    && cp descriptor-processor-1.0.0.jar /root/.m2/repository/com/acme/build/descriptor-processor/1.0.0/descriptor-processor-1.0.0.jar \
    && cp descriptor-runtime-1.0.0.jar /root/.m2/repository/com/acme/build/descriptor-runtime/1.0.0/descriptor-runtime-1.0.0.jar

RUN cat <<'EOF' > /root/.m2/repository/com/acme/build/descriptor-processor/1.0.0/descriptor-processor-1.0.0.pom
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.acme.build</groupId>
  <artifactId>descriptor-processor</artifactId>
  <version>1.0.0</version>
  <packaging>jar</packaging>
</project>
EOF

RUN cat <<'EOF' > /root/.m2/repository/com/acme/build/descriptor-runtime/1.0.0/descriptor-runtime-1.0.0.pom
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.acme.build</groupId>
  <artifactId>descriptor-runtime</artifactId>
  <version>1.0.0</version>
  <packaging>jar</packaging>
</project>
EOF

WORKDIR /workspace/project

COPY project/ /workspace/project/
COPY skills /root/.codex/skills
