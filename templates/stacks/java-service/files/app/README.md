# @@name@@ service: local setup

## Prerequisites

| Tool | Version | Source |
| --- | --- | --- |
| Java (JDK) | 25 | `java.version` in `pom.xml` |
| Maven | 3.9 | `Dockerfile` build image |
| Docker (optional, to build the image) | any recent | `Dockerfile` |

## Quick start

```sh
mvn -B verify
```

## Run and try it

```sh
mvn spring-boot:run
curl http://localhost:8080/api/hello
curl http://localhost:8080/actuator/health
```

Build and run the container:

```sh
docker build -t @@slug@@:dev .
docker run --rm -p 8080:8080 --memory 512m @@slug@@:dev
```

## Troubleshooting

- `release version 25 not supported`: your JDK is older than 25; check `java -version`.
- Port 8080 busy: stop the other process or set `SERVER_PORT`.
- TODO: commands under "Run and try it" have not been run by the developer for this project yet (SETUP-003).
