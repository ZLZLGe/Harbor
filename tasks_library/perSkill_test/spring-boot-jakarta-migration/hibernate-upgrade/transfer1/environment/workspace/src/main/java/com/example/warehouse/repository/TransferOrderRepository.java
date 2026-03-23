package com.example.warehouse.repository;

import com.example.warehouse.model.TransferOrder;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface TransferOrderRepository extends JpaRepository<TransferOrder, Long> {

    @Query("select t from TransferOrder t where dock.code = :dockCode and t.closed = false order by t.priority desc")
    List<TransferOrder> findOpenOrdersForDock(@Param("dockCode") String dockCode);
}
