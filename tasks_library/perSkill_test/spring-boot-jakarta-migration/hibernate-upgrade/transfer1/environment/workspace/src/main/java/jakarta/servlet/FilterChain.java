package jakarta.servlet;

import java.io.IOException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

public interface FilterChain {
    void doFilter(HttpServletRequest request, HttpServletResponse response) throws IOException, ServletException;
}
