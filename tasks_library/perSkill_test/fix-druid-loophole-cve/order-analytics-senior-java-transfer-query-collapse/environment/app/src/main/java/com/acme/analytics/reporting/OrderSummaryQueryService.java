package com.acme.analytics.reporting;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Collection;
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
        List<OrderSummaryRow> rows = new ArrayList<>();
        long grossRevenueCents = 0L;
        long refundedCents = 0L;
        int shippedOrderCount = 0;

        for (OrderRecord order : orders) {
            String customerTier = customerRepository.findCustomerTier(order.customerId());
            ShipmentSnapshot shipment = shipmentRepository.findLatestShipment(order.orderId());
            int lineItemCount = orderRepository.countLineItems(order.orderId());
            long discountCents = orderRepository.sumDiscountCents(order.orderId());
            long orderRefundedCents = orderRepository.sumRefundedCents(order.orderId());

            rows.add(new OrderSummaryRow(
                order.orderId(),
                order.orderNumber(),
                order.placedAt(),
                customerTier,
                lineItemCount,
                order.grossRevenueCents(),
                discountCents,
                orderRefundedCents,
                shipment.status()
            ));

            grossRevenueCents += order.grossRevenueCents();
            refundedCents += orderRefundedCents;
            if (isShipped(shipment.status())) {
                shippedOrderCount++;
            }
        }

        return new OrderSummaryResponse(
            rows,
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
