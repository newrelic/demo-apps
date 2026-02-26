import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.util.Random;
import java.util.logging.Logger;
import java.util.logging.Level;

public class HelloWorld {
    private static final Logger logger = Logger.getLogger(HelloWorld.class.getName());
    private static final Random random = new Random();

    private static final String[] ERROR_MESSAGES = {
        "Database connection timeout - unable to retrieve user data",
        "External API rate limit exceeded - request throttled",
        "Cache miss - failed to retrieve cached session data",
        "Authentication service unavailable - token validation failed",
        "Downstream service timeout - payment gateway not responding"
    };

    public static void main(String[] args) throws IOException {
        String serviceName = System.getenv().getOrDefault("SERVICE_NAME", "app");
        int port = 8080;

        // Get error rate from environment variable (default 10%)
        double errorRate = Double.parseDouble(
            System.getenv().getOrDefault("ERROR_RATE", "0.10")
        );

        HttpServer server = HttpServer.create(new InetSocketAddress(port), 0);

        server.createContext("/hello", exchange -> {
            try {
                // Randomly trigger errors based on error rate
                if (random.nextDouble() < errorRate) {
                    String errorMessage = ERROR_MESSAGES[random.nextInt(ERROR_MESSAGES.length)];

                    // Log error with structured information
                    logger.log(Level.SEVERE, String.format(
                        "Request failed: service=%s, error=%s, path=%s, method=%s",
                        serviceName, errorMessage, exchange.getRequestURI(), exchange.getRequestMethod()
                    ));

                    // Send 500 error response
                    String errorResponse = String.format(
                        "{\"error\": \"%s\", \"service\": \"%s\", \"status\": 500}",
                        errorMessage, serviceName
                    );
                    exchange.sendResponseHeaders(500, errorResponse.length());
                    OutputStream os = exchange.getResponseBody();
                    os.write(errorResponse.getBytes());
                    os.close();
                } else {
                    // Successful response
                    String response = "Hello from " + serviceName + "!";
                    exchange.sendResponseHeaders(200, response.length());
                    OutputStream os = exchange.getResponseBody();
                    os.write(response.getBytes());
                    os.close();

                    // Log successful request at INFO level
                    logger.log(Level.INFO, String.format(
                        "Request successful: service=%s, path=%s",
                        serviceName, exchange.getRequestURI()
                    ));
                }
            } catch (Exception e) {
                logger.log(Level.SEVERE, "Unexpected error processing request", e);
                throw e;
            }
        });

        server.start();
        System.out.println(serviceName + " started on port " + port + " (error rate: " + (errorRate * 100) + "%)");
    }
}
