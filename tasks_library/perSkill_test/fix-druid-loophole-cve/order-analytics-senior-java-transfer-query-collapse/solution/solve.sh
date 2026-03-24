#!/bin/bash

set -euo pipefail

APP_HOME="${APP_HOME:-/workspace/order-analytics}"
TARGET_FILE="${APP_HOME}/src/main/java/com/acme/analytics/reporting/OrderSummaryQueryService.java"

cat > "${TARGET_FILE}" <<'EOF'
package com.acme.analytics.reporting;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;

public class OrderSummaryQueryService {
    private final OrderRepository orderRepository;
    private final CustomerRepository customerRepository;
    private final ShipmentRepository shipmentRepository;

    public OrderSummaryQueryService(
        OrderRepository orderRepository,
        CustomerRepository customerRepository,
        ShipmentRepository shipmentRepository
    ) {
        this.orderRepository = orderRepository;
        this.customerRepository = customerRepository;
        this.shipmentRepository = shipmentRepository;
    }

    public OrderSummaryResponse fetchOrderSummaries(LocalDate startDate, LocalDate endDate, int limit) {
        List<OrderRecord> orders = orderRepository.findRecentOrders(startDate, endDate, limit);
        if (orders.isEmpty()) {
            return new OrderSummaryResponse(List.of(), new SummaryTotals(0, 0L, 0L, 0));
        }

        List<Long> orderIds = orders.stream()
            .map(OrderRecord::orderId)
            .toList();
        List<Long> customerIds = new ArrayList<>(new LinkedHashSet<>(
            orders.stream().map(OrderRecord::customerId).toList()
        ));

        Map<Long, OrderMetrics> metricsByOrderId = orderRepository.findOrderMetrics(orderIds);
        Map<Long, String> customerTierById = customerRepository.findCustomerTiers(customerIds);
        Map<Long, ShipmentSnapshot> shipmentByOrderId = shipmentRepository.findLatestShipments(orderIds);

        List<OrderSummaryRow> rows = new ArrayList<>(orders.size());
        long grossRevenueCents = 0L;
        long refundedCents = 0L;
        int shippedOrderCount = 0;

        for (OrderRecord order : orders) {
            OrderMetrics metrics = metricsByOrderId.getOrDefault(order.orderId(), OrderMetrics.EMPTY);
            ShipmentSnapshot shipment = shipmentByOrderId.getOrDefault(order.orderId(), ShipmentSnapshot.PENDING);
            String customerTier = customerTierById.getOrDefault(order.customerId(), "STANDARD");

            rows.add(new OrderSummaryRow(
                order.orderId(),
                order.orderNumber(),
                order.placedAt(),
                customerTier,
                metrics.lineItemCount(),
                order.grossRevenueCents(),
                metrics.discountCents(),
                metrics.refundedCents(),
                shipment.status()
            ));

            grossRevenueCents += order.grossRevenueCents();
            refundedCents += metrics.refundedCents();
            if (isShipped(shipment.status())) {
                shippedOrderCount++;
            }
        }

        return new OrderSummaryResponse(
            List.copyOf(rows),
            new SummaryTotals(rows.size(), grossRevenueCents, refundedCents, shippedOrderCount)
        );
    }

    private boolean isShipped(String status) {
        return "SHIPPED".equals(status) || "DELIVERED".equals(status);
    }

    public interface OrderRepository {
        List<OrderRecord> findRecentOrders(LocalDate startDate, LocalDate endDate, int limit);

        int countLineItems(long orderId);

        long sumDiscountCents(long orderId);

        long sumRefundedCents(long orderId);

        Map<Long, OrderMetrics> findOrderMetrics(Collection<Long> orderIds);
    }

    public interface CustomerRepository {
        String findCustomerTier(long customerId);

        Map<Long, String> findCustomerTiers(Collection<Long> customerIds);
    }

    public interface ShipmentRepository {
        ShipmentSnapshot findLatestShipment(long orderId);

        Map<Long, ShipmentSnapshot> findLatestShipments(Collection<Long> orderIds);
    }

    public record OrderRecord(
        long orderId,
        long customerId,
        String orderNumber,
        LocalDate placedAt,
        long grossRevenueCents
    ) {
    }

    public record OrderMetrics(
        int lineItemCount,
        long discountCents,
        long refundedCents
    ) {
        public static final OrderMetrics EMPTY = new OrderMetrics(0, 0L, 0L);
    }

    public record ShipmentSnapshot(String status) {
        public static final ShipmentSnapshot PENDING = new ShipmentSnapshot("PENDING");
    }

    public record OrderSummaryRow(
        long orderId,
        String orderNumber,
        LocalDate placedAt,
        String customerTier,
        int lineItemCount,
        long grossRevenueCents,
        long discountCents,
        long refundedCents,
        String shipmentStatus
    ) {
    }

    public record SummaryTotals(
        int orderCount,
        long grossRevenueCents,
        long refundedCents,
        int shippedOrderCount
    ) {
    }

    public record OrderSummaryResponse(List<OrderSummaryRow> rows, SummaryTotals totals) {
    }
}
EOF

cd "${APP_HOME}"
mvn -q -DskipTests package
