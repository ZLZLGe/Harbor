package com.acme.logistics.repository;

import com.acme.logistics.model.ShipmentEvent;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ShipmentEventRepository extends JpaRepository<ShipmentEvent, Long> {

    List<ShipmentEvent> findByShipmentIdOrderByOccurredAtAsc(String shipmentId);
}
