package com.ev.multiev_charging_management_system;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@EnableScheduling
@SpringBootApplication
public class MultiEvChargingManagementSystemApplication {

    public static void main(String[] args) {
        SpringApplication.run(MultiEvChargingManagementSystemApplication.class, args);
    }

}
