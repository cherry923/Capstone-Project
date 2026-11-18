package com.ev.multiev_charging_management_system.auth.repository;

import com.ev.multiev_charging_management_system.auth.entity.AdminAccount;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface AdminAccountRepository extends JpaRepository<AdminAccount, Long> {

    Optional<AdminAccount> findByUsername(String username);

    boolean existsByUsername(String username);
}
