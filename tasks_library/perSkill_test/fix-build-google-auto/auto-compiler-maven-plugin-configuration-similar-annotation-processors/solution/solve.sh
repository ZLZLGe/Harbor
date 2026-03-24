#!/bin/bash
set -euo pipefail

cat <<'EOF' > pom.xml
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>

  <groupId>com.acme</groupId>
  <artifactId>descriptor-catalog</artifactId>
  <version>1.0.0-SNAPSHOT</version>

  <properties>
    <maven.compiler.release>17</maven.compiler.release>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
  </properties>

  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-compiler-plugin</artifactId>
        <version>3.12.1</version>
        <configuration>
          <annotationProcessorPaths>
            <path>
              <groupId>com.acme.build</groupId>
              <artifactId>descriptor-processor</artifactId>
              <version>1.0.0</version>
            </path>
          </annotationProcessorPaths>
          <compilerArgs>
            <arg>-Adescriptor.package=com.acme.catalog.generated</arg>
            <arg>-Adescriptor.className=OrderFieldsDescriptor</arg>
          </compilerArgs>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
EOF
