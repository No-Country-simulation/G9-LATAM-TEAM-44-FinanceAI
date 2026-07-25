# Build multi-etapa: compilamos con Maven y publicamos solo el JRE + el jar.
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /build

# Copiamos primero el pom para aprovechar la cache de capas de Docker:
# si no cambian las dependencias, no se vuelven a descargar.
COPY pom.xml .
RUN mvn -B dependency:go-offline

COPY src ./src
RUN mvn -B clean package -DskipTests

FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=build /build/target/*.jar app.jar

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
