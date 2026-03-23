#!/bin/bash

set -euo pipefail

cd /workspace

cat > src/main/java/com/example/warehouse/model/TransferOrder.java <<'EOF'
package com.example.warehouse.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

@Entity
@Table(name = "transfer_orders")
public class TransferOrder {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "dock_id", nullable = false)
    private WarehouseDock dock;

    @Column(nullable = false)
    private int priority;

    @Column(nullable = false)
    private boolean closed;
}
EOF

cat > src/main/java/com/example/warehouse/repository/TransferOrderRepository.java <<'EOF'
package com.example.warehouse.repository;

import com.example.warehouse.model.TransferOrder;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface TransferOrderRepository extends JpaRepository<TransferOrder, Long> {

    @Query("select t from TransferOrder t where t.dock.code = :dockCode and t.closed = false order by t.priority desc")
    List<TransferOrder> findOpenOrdersForDock(@Param("dockCode") String dockCode);
}
EOF

cat > /root/transfer1_query_fix.json <<'EOF'
{
  "service": "warehouse-transfer",
  "updated_query": "select t from TransferOrder t where t.dock.code = :dockCode and t.closed = false order by t.priority desc",
  "touched_files": [
    "src/main/java/com/example/warehouse/model/TransferOrder.java",
    "src/main/java/com/example/warehouse/repository/TransferOrderRepository.java"
  ]
}
EOF
