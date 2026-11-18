package com.ev.multiev_charging_management_system.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.Customizer;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.servlet.util.matcher.PathPatternRequestMatcher;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

import java.util.Arrays;
import java.util.List;

@Configuration
public class SecurityConfig {

    private static final PathPatternRequestMatcher AI_DISPATCH_24H =
            PathPatternRequestMatcher.pathPattern(HttpMethod.POST, "/api/v1/ai/dispatch-24h");
    private static final PathPatternRequestMatcher AI_DISPATCH_RUNS =
            PathPatternRequestMatcher.pathPattern("/api/v1/ai/dispatch-runs");
    private static final PathPatternRequestMatcher AI_DISPATCH_RUN_LATEST =
            PathPatternRequestMatcher.pathPattern("/api/v1/ai/dispatch-runs/latest");
    private static final PathPatternRequestMatcher AI_DISPATCH_RUN_DETAILS =
            PathPatternRequestMatcher.pathPattern("/api/v1/ai/dispatch-runs/**");
    private static final PathPatternRequestMatcher AI_TIMELAPSE_PERIODS =
            PathPatternRequestMatcher.pathPattern("/api/v1/ai/timelapse-periods");
    private static final PathPatternRequestMatcher AI_TIMELAPSE_PERIOD_DETAILS =
            PathPatternRequestMatcher.pathPattern("/api/v1/ai/timelapse-periods/**");
    private static final PathPatternRequestMatcher AI_TIMELAPSE_PERIODS_WRITE =
            PathPatternRequestMatcher.pathPattern(HttpMethod.POST, "/api/v1/ai/timelapse-periods");
    private static final PathPatternRequestMatcher AI_TIMELAPSE_PERIOD_MQTT_PUBLISH =
            PathPatternRequestMatcher.pathPattern(
                    HttpMethod.POST,
                    "/api/v1/ai/timelapse-periods/{periodKey}/frames/{frameIndex}/mqtt-publish"
            );
    private static final PathPatternRequestMatcher CHARGER_MEASUREMENTS_LATEST =
            PathPatternRequestMatcher.pathPattern("/api/chargers/measurements/latest-snapshot");
    private static final PathPatternRequestMatcher V1_CHARGER_MEASUREMENTS_LATEST =
            PathPatternRequestMatcher.pathPattern("/api/v1/chargers/measurements/latest-snapshot");
    private static final PathPatternRequestMatcher CHARGER_MEASUREMENTS =
            PathPatternRequestMatcher.pathPattern("/api/chargers/measurements/**");
    private static final PathPatternRequestMatcher V1_CHARGER_MEASUREMENTS =
            PathPatternRequestMatcher.pathPattern("/api/v1/chargers/measurements/**");
    private static final PathPatternRequestMatcher AUTH_LOGIN =
            PathPatternRequestMatcher.pathPattern(HttpMethod.POST, "/api/auth/login");
    private static final PathPatternRequestMatcher AUTH_SIGNUP =
            PathPatternRequestMatcher.pathPattern(HttpMethod.POST, "/api/auth/signup");
    private static final PathPatternRequestMatcher AUTH_CHECK_USERNAME =
            PathPatternRequestMatcher.pathPattern(HttpMethod.GET, "/api/auth/check-username");
    private static final PathPatternRequestMatcher ADMIN_STATIONS =
            PathPatternRequestMatcher.pathPattern(HttpMethod.GET, "/api/admin/stations");
    private static final PathPatternRequestMatcher V1_ADMIN_STATIONS =
            PathPatternRequestMatcher.pathPattern(HttpMethod.GET, "/api/v1/admin/stations");
    private static final PathPatternRequestMatcher ADMIN_STATIONS_ROOT =
            PathPatternRequestMatcher.pathPattern("/api/admin/stations");
    private static final PathPatternRequestMatcher V1_ADMIN_STATIONS_ROOT =
            PathPatternRequestMatcher.pathPattern("/api/v1/admin/stations");
    private static final PathPatternRequestMatcher ADMIN_STATIONS_WRITE =
            PathPatternRequestMatcher.pathPattern("/api/admin/stations/**");
    private static final PathPatternRequestMatcher V1_ADMIN_STATIONS_WRITE =
            PathPatternRequestMatcher.pathPattern("/api/v1/admin/stations/**");
    private static final PathPatternRequestMatcher FRONTEND_ROOT =
            PathPatternRequestMatcher.pathPattern(HttpMethod.GET, "/");
    private static final PathPatternRequestMatcher FRONTEND_HTML =
            PathPatternRequestMatcher.pathPattern(HttpMethod.GET, "/*.html");
    private static final PathPatternRequestMatcher FRONTEND_JS =
            PathPatternRequestMatcher.pathPattern(HttpMethod.GET, "/*.js");
    private static final PathPatternRequestMatcher FRONTEND_CSS =
            PathPatternRequestMatcher.pathPattern(HttpMethod.GET, "/*.css");
    private static final PathPatternRequestMatcher FRONTEND_ASSETS =
            PathPatternRequestMatcher.pathPattern(HttpMethod.GET, "/assets/**");
    private static final PathPatternRequestMatcher FAVICON =
            PathPatternRequestMatcher.pathPattern(HttpMethod.GET, "/favicon.ico");
    private static final PathPatternRequestMatcher ERROR =
            PathPatternRequestMatcher.pathPattern("/error");

    @Bean
    public SecurityFilterChain securityFilterChain(
            HttpSecurity http,
            @Value("${external.ai.dispatch.demo-open-enabled:false}") boolean demoOpenEnabled
    ) throws Exception {
        http.cors(Customizer.withDefaults());

        if (demoOpenEnabled) {
            http.csrf(csrf -> csrf.ignoringRequestMatchers(
                    AI_DISPATCH_24H,
                    AUTH_LOGIN,
                    AUTH_SIGNUP,
                    AI_TIMELAPSE_PERIODS_WRITE,
                    AI_TIMELAPSE_PERIOD_MQTT_PUBLISH,
                    ADMIN_STATIONS_ROOT,
                    V1_ADMIN_STATIONS_ROOT,
                    ADMIN_STATIONS_WRITE,
                    V1_ADMIN_STATIONS_WRITE
            ));
        } else {
            http.csrf(csrf -> csrf.ignoringRequestMatchers(
                    AUTH_LOGIN,
                    AUTH_SIGNUP,
                    ADMIN_STATIONS_ROOT,
                    V1_ADMIN_STATIONS_ROOT,
                    ADMIN_STATIONS_WRITE,
                    V1_ADMIN_STATIONS_WRITE
            ));
        }

        http.authorizeHttpRequests(authorize -> {
            if (demoOpenEnabled) {
                authorize.requestMatchers(AI_DISPATCH_24H).permitAll();
                authorize.requestMatchers(AI_DISPATCH_RUNS, AI_DISPATCH_RUN_LATEST, AI_DISPATCH_RUN_DETAILS).permitAll();
                authorize.requestMatchers(AI_TIMELAPSE_PERIODS_WRITE).permitAll();
                authorize.requestMatchers(AI_TIMELAPSE_PERIOD_MQTT_PUBLISH).permitAll();
            } else {
                authorize.requestMatchers(AI_DISPATCH_24H).authenticated();
                authorize.requestMatchers(AI_DISPATCH_RUNS, AI_DISPATCH_RUN_LATEST, AI_DISPATCH_RUN_DETAILS).authenticated();
                authorize.requestMatchers(AI_TIMELAPSE_PERIODS_WRITE).authenticated();
                authorize.requestMatchers(AI_TIMELAPSE_PERIOD_MQTT_PUBLISH).authenticated();
            }
            authorize.requestMatchers(AI_TIMELAPSE_PERIODS, AI_TIMELAPSE_PERIOD_DETAILS).permitAll();
            authorize.requestMatchers(AUTH_LOGIN, AUTH_SIGNUP, AUTH_CHECK_USERNAME).permitAll();
            authorize.requestMatchers(ADMIN_STATIONS, V1_ADMIN_STATIONS).permitAll();
            authorize.requestMatchers(
                    ADMIN_STATIONS_ROOT,
                    V1_ADMIN_STATIONS_ROOT,
                    ADMIN_STATIONS_WRITE,
                    V1_ADMIN_STATIONS_WRITE
            ).permitAll();
            authorize.requestMatchers(
                    CHARGER_MEASUREMENTS_LATEST,
                    V1_CHARGER_MEASUREMENTS_LATEST,
                    CHARGER_MEASUREMENTS,
                    V1_CHARGER_MEASUREMENTS
            ).permitAll();
            authorize.requestMatchers(
                    FRONTEND_ROOT,
                    FRONTEND_HTML,
                    FRONTEND_JS,
                    FRONTEND_CSS,
                    FRONTEND_ASSETS,
                    FAVICON,
                    ERROR
            ).permitAll();
            authorize.anyRequest().authenticated();
        });
        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource(
            @Value("${app.cors.allowed-origins:}") String allowedOrigins
    ) {
        CorsConfiguration configuration = new CorsConfiguration();
        configuration.setAllowedOrigins(splitCsv(allowedOrigins));
        configuration.setAllowedMethods(List.of("GET", "POST", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(List.of("Content-Type", "Authorization"));
        configuration.setAllowCredentials(false);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/v1/ai/**", configuration);
        source.registerCorsConfiguration("/api/auth/**", configuration);
        source.registerCorsConfiguration("/api/admin/**", configuration);
        source.registerCorsConfiguration("/api/v1/admin/**", configuration);
        source.registerCorsConfiguration("/api/chargers/**", configuration);
        source.registerCorsConfiguration("/api/v1/chargers/**", configuration);
        return source;
    }

    private List<String> splitCsv(String value) {
        return Arrays.stream(value.split(","))
                .map(String::trim)
                .filter(origin -> !origin.isBlank())
                .toList();
    }
}
