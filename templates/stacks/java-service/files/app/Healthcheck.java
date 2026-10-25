// Used by the Dockerfile HEALTHCHECK: the runtime image has no curl or wget.
// Compiled in the Dockerfile build stage; run with `java -cp /app/healthcheck Healthcheck [url]`; exits 0 when the URL answers 200, else 1.
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

public class Healthcheck {
    public static void main(String[] args) throws Exception {
        String url = args.length > 0 ? args[0] : "http://localhost:8080/actuator/health/liveness";
        try {
            HttpRequest request = HttpRequest.newBuilder(URI.create(url)).timeout(Duration.ofSeconds(3)).build();
            int status = HttpClient.newHttpClient().send(request, HttpResponse.BodyHandlers.discarding()).statusCode();
            System.exit(status == 200 ? 0 : 1);
        } catch (Exception e) {
            System.exit(1);
        }
    }
}
